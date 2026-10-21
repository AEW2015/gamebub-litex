# SPDX-License-Identifier: 0BSD
"""Run the frozen button/IRQ/overlay BFM against this phase's endpoint."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"phase3"))
from esp32 import run
run.SOURCES=(HERE/"rtl/esp32_v102_endpoint.sv",
             HERE.parent/"phase3/esp32/qspi_host_bfm.sv",
             HERE.parent/"phase3/esp32/tb_endpoint_protocol.sv")
if __name__=="__main__": raise SystemExit(run.main())
