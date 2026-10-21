# SPDX-License-Identifier: 0BSD
# Read-only server metadata enumeration. Never opens a cable or selects an IR.
if {![info exists ::env(GAMEBUB_JTAG_SERIAL)] || ![regexp {^[A-Za-z0-9_-]+$} $::env(GAMEBUB_JTAG_SERIAL)]} {
    error "Set GAMEBUB_JTAG_SERIAL before enumerating the selected cable"
}
connect -url tcp:localhost:3121
try {
    set filter [format {jtag_cable_serial == "%s"} $::env(GAMEBUB_JTAG_SERIAL)]
    puts "GAMEBUB_XSDB_TARGET_METADATA=[jtag targets -filter $filter -target-properties]"
} finally {
    disconnect
}
