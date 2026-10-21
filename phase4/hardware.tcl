# SPDX-License-Identifier: 0BSD
# Vivado is used ONLY as a read-only probe / volatile bitstream loader.
lassign $argv mode bit expected
if {![info exists ::env(GAMEBUB_JTAG_SERIAL)] || ![regexp {^[A-Za-z0-9_-]+$} $::env(GAMEBUB_JTAG_SERIAL)]} {
    error "Set GAMEBUB_JTAG_SERIAL to the exact cable serial before probing or programming"
}
set wanted_serial $::env(GAMEBUB_JTAG_SERIAL)
if {$mode ni {probe program}} {error "usage: hardware.tcl probe|program BIT SHA256"}
if {$mode eq "program"} {
    if {![file isfile $bit] || ![regexp {^[0-9a-fA-F]{64}$} $expected]} {error "BIT and SHA256 required"}
    set result [exec certutil -hashfile $bit SHA256]
    if {![regexp -nocase {\m[0-9a-f]{64}\M} $result actual] || ![string equal -nocase $actual $expected]} {error "BIT hash mismatch"}
}
open_hw_manager
try {
    connect_hw_server -allow_non_jtag
    set targets [get_hw_targets -quiet */Digilent/$wanted_serial]
    if {[llength $targets] != 1} {error "Unique selected GameBub cable $wanted_serial required"}
    current_hw_target [lindex $targets 0]
    set_property PARAM.FREQUENCY 1000000 [current_hw_target]
    open_hw_target
    set devices [get_hw_devices]
    if {[llength $devices] != 1} {error "Expected one device on the selected cable; not touching an unexpected chain"}
    set device [lindex $devices 0]
    if {[get_property PART $device] ne "xc7a100t"} {error "Selected cable does not contain the expected XC7A100T"}
    refresh_hw_device $device
    puts "GAMEBUB_PROBE CABLE=[current_hw_target] PART=[get_property PART $device] USERCODE=[get_property REGISTER.USERCODE $device] DONE=[get_property REGISTER.IR.BIT5_DONE $device] CRC=[get_property REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR $device]"
    if {$mode eq "program"} {
        # Previous images remain preserved in the earlier release directories.
        set_property PROBES.FILE {} $device
        set_property FULL_PROBES.FILE {} $device
        set_property PROGRAM.FILE $bit $device
        program_hw_devices $device
        refresh_hw_device $device
        set done [get_property REGISTER.IR.BIT5_DONE $device]
        set crc [get_property REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR $device]
        puts "GAMEBUB_PROGRAM BIT=$bit SHA256=$actual DONE=$done CRC=$crc USERCODE=[get_property REGISTER.USERCODE $device]"
        if {$done != 1 || $crc != 0} {error "FPGA configuration did not complete cleanly"}
        puts GAMEBUB_VOLATILE_PROGRAM_PASS
    }
} finally {
    catch {close_hw_target}
    close_hw_manager
}
exit
