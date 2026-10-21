# SPDX-License-Identifier: 0BSD
import argparse
import json
from pathlib import Path
from migen import Signal
from migen.fhdl import verilog
from migen.build.xilinx.common import xilinx_special_overrides
from clocking import PhysicalCRG


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    a=p.parse_args()
    if a.output.exists():p.error("choose a new directory")
    a.output.mkdir(parents=True)
    class Platform:
        clk=Signal(name="clk50")
        def request(self,name):
            assert name=="clk50"
            return self.clk
    platform=Platform()
    c=PhysicalCRG(platform,por_cycles=16)
    por_done_monitor=Signal(name="por_done_monitor")
    c.comb += por_done_monitor.eq(c.por_done)
    ios={platform.clk,c.locked,por_done_monitor,c.reset_request}
    for cd in (c.cd_sys,c.cd_service,c.cd_video):ios.update((cd.clk,cd.rst))
    verilog.convert(c,ios=ios,name="clocking_dut",special_overrides=xilinx_special_overrides).write(str(a.output/"clocking_dut.v"))
    (a.output/"frequencies.json").write_text(json.dumps(c.frequencies(),indent=2)+"\n")


if __name__=="__main__":main()
