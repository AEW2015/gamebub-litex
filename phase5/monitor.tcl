# SPDX-License-Identifier: 0BSD
# Read-only LiteX JTAGPHY/JTAG UART drain for the GameBub XC7A100T.
# Run from XSDB only after the programmer has released the target.

set server_url "tcp:localhost:3121"
if {![info exists ::env(GAMEBUB_JTAG_SERIAL)] || ![regexp {^[A-Za-z0-9_-]+$} $::env(GAMEBUB_JTAG_SERIAL)]} {
    error "Set GAMEBUB_JTAG_SERIAL to the exact cable serial before opening JTAG"
}
set wanted_serial $::env(GAMEBUB_JTAG_SERIAL)
set wanted_idcode "13631093"
set user1_ir 0x02
set user1_irlen 6
set jtag_hz 1000000
set frame_bits 10
set max_frames 512
set idle_tail 4
set expected_payload {71 66 53 95 79 75 10}

set connected 0
set chain_locked 0
set cable_opened 0
set cable_node ""
set sequence ""
set old_frequency ""

proc matching_targets {serial idcode} {
    set cables {}
    set fpgas {}
    # The cable serial filter is applied before any target is selected/opened.
    set filter [format {jtag_cable_serial == "%s"} $serial]
    set props [jtag targets -filter $filter -target-properties]
    foreach p $props {
        if {![dict exists $p jtag_cable_serial] ||
            [dict get $p jtag_cable_serial] ne $serial} {
            continue
        }
        set level [dict get $p level]
        if {$level == 0} {
            lappend cables $p
        } elseif {[dict exists $p is_fpga] && [dict get $p is_fpga] &&
                  [dict exists $p idcode] &&
                  [string tolower [dict get $p idcode]] eq [string tolower $idcode]} {
            lappend fpgas $p
        }
    }
    if {[llength $cables] != 1} {
        error "expected one active cable with serial $serial; found [llength $cables]"
    }
    if {[llength $fpgas] != 1} {
        error "expected one XC7A100T IDCODE $idcode under $serial; found [llength $fpgas]"
    }
    return [list [lindex $cables 0] [lindex $fpgas 0]]
}

set status [catch {
    connect -url $server_url
    set connected 1

    foreach {cable fpga} [matching_targets $wanted_serial $wanted_idcode] break
    set cable_node [dict get $cable node_id]
    # hw_server can auto-open a cable even with no programming client.
    # is_open is not an ownership test. Preserve pre-existing open state,
    # and use the documented chain lock to prevent concurrent scan sequences.
    if {![dict get $cable is_open]} {
        jtag targets -open $cable_node
        set cable_opened 1
    }

    # Re-resolve node IDs after opening, and require the same exact serial/IDCODE.
    foreach {cable fpga} [matching_targets $wanted_serial $wanted_idcode] break
    if {[dict get $cable node_id] ne $cable_node} {
        error "HS2 cable node changed while opening; refusing to continue"
    }
    set fpga_node [dict get $fpga node_id]
    if {[dict exists $fpga irlen] && [dict get $fpga irlen] != $user1_irlen} {
        error "expected FPGA IR length $user1_irlen, got [dict get $fpga irlen]"
    }
    jtag targets -set $fpga_node
    jtag lock 1000
    set chain_locked 1

    set old_frequency [jtag frequency]
    jtag frequency $jtag_hz
    puts "TARGET serial=$wanted_serial idcode=$wanted_idcode user1_ir=$user1_irlen-bit/$user1_ir frequency=[jtag frequency]Hz"

    # Select USER1 and leave the TAP in IDLE (not RESET, which would replace
    # USER1 with the FPGA's default instruction).
    set sequence [jtag sequence]
    $sequence irshift -integer -state IDLE $user1_irlen $user1_ir
    $sequence run

    set received {}
    set idle_count 0
    for {set n 0} {$n < $max_frames} {incr n} {
        $sequence clear
        # TDI bit 0 accepts one target-to-host byte; bit 9 is host-to-target
        # valid and remains 0. The 8 data bits are don't-care zeroes.
        $sequence drshift -capture -integer -state IDLE $frame_bits 1
        set raw [$sequence run -integer -single]
        set raw [expr {$raw & ((1 << $frame_bits) - 1)}]
        set valid [expr {($raw >> 9) & 1}]
        set byte [expr {($raw >> 1) & 0xff}]
        if {$valid} {
            lappend received $byte
            set idle_count 0
            puts [format {UART[%03d] valid=1 data=0x%02X} $n $byte]
        } else {
            incr idle_count
            if {[llength $received] > 0 && $idle_count >= $idle_tail} {
                break
            }
            # Allow the periodic firmware smoke message to arrive if the
            # programmer's USER1 discovery scans already drained the FIFO.
            after 5
        }
    }

    set hex {}
    set ascii ""
    foreach byte $received {
        append hex [format "%02X" $byte]
        switch -- $byte {
            9  {append ascii "\\t"}
            10 {append ascii "\\n"}
            13 {append ascii "\\r"}
            default {
                if {$byte >= 0x20 && $byte <= 0x7e} {
                    append ascii [format "%c" $byte]
                } else {
                    append ascii "."
                }
            }
        }
    }
    puts "JTAGUART_COUNT=[llength $received]"
    puts "JTAGUART_HEX=$hex"
    puts "JTAGUART_ASCII=$ascii"

    set expected_index -1
    set expected_len [llength $expected_payload]
    for {set i 0} {$i + $expected_len <= [llength $received]} {incr i} {
        if {[lrange $received $i [expr {$i + $expected_len - 1}]] eq $expected_payload} {
            set expected_index $i
            break
        }
    }
    if {$expected_index < 0} {
        error "did not receive expected 7-byte GB5_OK newline UI-startup payload"
    }
    puts "JTAGUART_SMOKE_PASS=GB5_OK\\n offset=$expected_index"
} message options]

if {$sequence ne ""} {
    if {[catch {$sequence delete} cleanup_message]} {
        puts stderr "JTAGUART_CLEANUP_WARNING=sequence delete failed: $cleanup_message"
    }
}
if {$old_frequency ne ""} {
    if {[catch {jtag frequency $old_frequency} cleanup_message]} {
        puts stderr "JTAGUART_CLEANUP_WARNING=frequency restore failed: $cleanup_message"
    }
}
if {$chain_locked} {
    if {[catch {jtag unlock} cleanup_message]} {
        puts stderr "JTAGUART_CLEANUP_WARNING=chain unlock failed: $cleanup_message"
    }
}
if {$cable_opened} {
    if {[catch {jtag targets -close $cable_node} cleanup_message]} {
        puts stderr "JTAGUART_CLEANUP_WARNING=cable close failed: $cleanup_message"
    }
}
if {$connected} {
    if {[catch {disconnect} cleanup_message]} {
        puts stderr "JTAGUART_CLEANUP_WARNING=XSDB disconnect failed: $cleanup_message"
    }
}

if {$status} {
    puts stderr "JTAGUART_ERROR=$message"
    return -options $options $message
}
