# SPDX-License-Identifier: 0BSD
import argparse
import sys
from pathlib import Path
from migen import Module, ClockDomain
from migen.fhdl import verilog
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gamebub.video import Video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=int, choices=(0, 1), default=1)
    args = parser.parse_args()
    m = Module()
    m.clock_domains.cd_video = ClockDomain("video")
    m.submodules.video = v = Video(timing_profile=args.profile)
    ios = {m.cd_video.clk, m.cd_video.rst}
    ios.update(getattr(v, n) for n in ("dotclk", "de", "hsync", "vsync", "r", "g", "b", "x", "y",
               "overlay_valid", "overlay_rgb", "overlay_x", "overlay_y", "overlay_de", "frame_start"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    verilog.convert(m, ios=ios, name="gamebub_video").write(str(args.output))


if __name__ == "__main__":
    main()
