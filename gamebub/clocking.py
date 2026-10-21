# SPDX-License-Identifier: 0BSD
"""Physical 7-series clocks for the open-source GameBub hardware candidate.

One 800 MHz VCO: video CLKOUT0 /27.25, sys CLKOUT1 /16, service CLKOUT2 /4.
The fractional video divide belongs on CLKOUT0. All reset release is local
clock synchronized after autonomous input-clock POR and MMCM lock.
"""
from migen import ClockDomain, Signal, If, Instance
from migen.genlib.resetsync import AsyncResetSynchronizer
from litex.gen import LiteXModule
from litex.soc.cores.clock import S7MMCM

INPUT_HZ = 50_000_000
SYS_HZ = 50_000_000
SERVICE_HZ = 200_000_000
VIDEO_HZ = 800_000_000 / 27.25
VIDEO_FRAME_HZ = VIDEO_HZ / (605 * 809)
LEGACY_VIDEO_HZ = 29_361_979.166666668
VIDEO_ERROR_PPM = (VIDEO_HZ / LEGACY_VIDEO_HZ - 1) * 1e6


class PhysicalCRG(LiteXModule):
    def __init__(self, platform, por_cycles=1024):
        if por_cycles < 4:
            raise ValueError("POR must span at least four input-clock cycles")
        self.cd_por = ClockDomain("por", reset_less=True)
        self.cd_sys = ClockDomain("sys")
        self.cd_service = ClockDomain("service")
        self.cd_video = ClockDomain("video")
        for cd in (self.cd_por, self.cd_sys, self.cd_service, self.cd_video):
            cd.clk.attr.add("keep")
        clk50 = platform.request("clk50")
        # The independent input-clock domain guarantees MMCM reset can release
        # before any output clock exists. The tool inserts the input IBUF.
        self.specials += Instance("BUFG", i_I=clk50, o_O=self.cd_por.clk)
        count = Signal(max=por_cycles, reset=0, reset_less=True, name="por_count")
        self.por_done = Signal(reset=0, reset_less=True, name="por_done")
        self.sync.por += If(~self.por_done,
            If(count == por_cycles-1, self.por_done.eq(1)).Else(count.eq(count+1)))

        self.mmcm = mmcm = S7MMCM(speedgrade=-1)
        # Constrain the standard LiteX search, rather than relying on the first
        # approximate solution selected by its default broad search ranges.
        mmcm.divclk_divide_range = (1, 2)
        mmcm.clkfbout_mult_frange = (16, 17)
        mmcm.register_clkin(self.cd_por.clk, INPUT_HZ)
        mmcm.create_clkout(self.cd_video, VIDEO_HZ, margin=1e-9, with_reset=False)
        mmcm.create_clkout(self.cd_sys, SYS_HZ, margin=1e-9, with_reset=False)
        mmcm.create_clkout(self.cd_service, SERVICE_HZ, margin=1e-9, with_reset=False)
        self.comb += mmcm.reset.eq(~self.por_done)
        self.locked = mmcm.locked
        self.reset_request = Signal(name="reset_request")
        self.comb += self.reset_request.eq(~self.por_done | ~mmcm.locked)
        for cd in (self.cd_sys, self.cd_service, self.cd_video):
            self.specials += AsyncResetSynchronizer(cd, self.reset_request)

    @staticmethod
    def frequencies():
        return dict(input_hz=INPUT_HZ, sys_hz=SYS_HZ, service_hz=SERVICE_HZ,
                    video_hz=VIDEO_HZ, profile1_frame_hz=VIDEO_FRAME_HZ,
                    legacy_video_hz=LEGACY_VIDEO_HZ, video_error_ppm=VIDEO_ERROR_PPM,
                    vco_hz=800_000_000, divclk_divide=1, clkfbout_mult=16,
                    clkout0_divide=27.25, clkout1_divide=16, clkout2_divide=4)


# Convenient local alias for target CRG replacement.
CRG = PhysicalCRG
