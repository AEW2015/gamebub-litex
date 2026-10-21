# SPDX-License-Identifier: BSD-2-Clause
"""Conservative Rev4 external-memory Wishbone controllers, 50 MHz system clock."""
import os
import sys
from types import SimpleNamespace
sys.path.insert(0, os.environ.get("GAMEBUB_LITEDRAM_PATH", "/opt/gamebub-litex-20261021/memory-python"))
from migen import *
from migen.fhdl.specials import Tristate

from litex.soc.interconnect import wishbone

from litedram.phy.gensdrphy import GENSDRPHY
from litedram.modules import MT48LC16M16
from litedram.core.controller import LiteDRAMController, ControllerSettings
from litedram.core.crossbar import LiteDRAMCrossbar
from litedram.frontend.wishbone import LiteDRAMWishbone2Native


# Pad Records -------------------------------------------------------------------------------------

def sram_pads():
    return Record([
        ("a", 18), ("dq", 16), ("ce_n", 1), ("we_n", 1),
        ("oe_n", 1), ("lb_n", 1), ("ub_n", 1),
    ], name="sram")


def sdram_pads():
    return Record([
        ("a", 13), ("ba", 2), ("dq", 16), ("dm", 2), ("cs_n", 2), ("cke", 2),
        ("ras_n", 1), ("cas_n", 1), ("we_n", 1), ("clk", 1),
    ], name="sdram")


# Asynchronous SRAM -------------------------------------------------------------------------------

class GameBubSRAM(Module):
    """32-bit Wishbone to 256K x16 asynchronous SRAM; conservative 80ns access."""
    def __init__(self, pads):
        self.bus = bus = wishbone.Interface(data_width=32, address_width=32, addressing='word')
        self.initialized = Signal(reset=1)

        # # #

        address, data, select, write = Signal(17), Signal(32), Signal(4), Signal()
        half, sample, drive = Signal(), Signal(16), Signal()
        read_data = Signal(32)
        count = Signal(3)
        lane = Signal(2)
        self.comb += [
            pads.a.eq(Cat(half, address)),
            lane.eq(Mux(half, select[2:4], select[:2])),
            pads.lb_n.eq(~lane[0]),
            pads.ub_n.eq(~lane[1]),
            bus.dat_r.eq(read_data),
        ]
        self.specials += Tristate(pads.dq, Mux(half, data[16:32], data[:16]), drive, sample)
        self.submodules.fsm = fsm = FSM(reset_state='IDLE')
        # Controls default inactive; drive only while write address/data are stable.
        self.comb += [pads.ce_n.eq(1), pads.we_n.eq(1), pads.oe_n.eq(1)]
        fsm.act("IDLE",
            If(bus.cyc & bus.stb,
                NextValue(address, bus.adr[:17]),
                NextValue(data, bus.dat_w),
                NextValue(select, bus.sel),
                NextValue(write, bus.we),
                NextValue(half, 0),
                NextValue(count, 1),
                NextState("SETUP"),
            )
        )
        fsm.act("SETUP",
            pads.ce_n.eq(0),
            drive.eq(write),
            If(count == 0,
                NextValue(count, 3),
                NextState("ACCESS"),
            ).Else(
                NextValue(count, count - 1)
            )
        )
        fsm.act("ACCESS",
            pads.ce_n.eq(0),
            drive.eq(write),
            pads.we_n.eq(~write),
            pads.oe_n.eq(write),
            If(count == 0,
                If(~write,
                    If(half,
                        NextValue(read_data[16:32], sample)
                    ).Else(
                        NextValue(read_data[:16], sample)
                    )
                ),
                NextValue(count, 1),
                NextState("HOLD"),
            ).Else(
                NextValue(count, count - 1)
            )
        )
        fsm.act("HOLD",
            pads.ce_n.eq(0),
            drive.eq(write),
            If(count == 0,
                NextState("TURN")
            ).Else(
                NextValue(count, count - 1)
            )
        )
        fsm.act("TURN",
            If(half,
                NextState("ACK")
            ).Else(
                NextValue(half, 1),
                NextValue(count, 1),
                NextState("SETUP"),
            )
        )
        fsm.act("ACK",
            bus.ack.eq(bus.cyc & bus.stb),
            NextState("IDLE"),
        )


# SDR SDRAM ---------------------------------------------------------------------------------------

class GameBubSDRAM(Module):
    """Upstream LiteDRAM controller+GENSDRPHY with autonomous JEDEC SDR init.

    One populated/selected x16 rank, 13 row/9 column/2 bank bits = 32MiB.
    The second physical CS stays inactive, matching the known-good Rev4 stack.
    """
    def __init__(self, pads, sys_clk_freq=50e6):
        if sys_clk_freq != 50e6:
            raise ValueError('This conservative profile is validated only at 50MHz')
        self.bus = bus = wishbone.Interface(data_width=32,address_width=32,addressing='word')
        self.initialized = initialized = Signal()

        # # #

        one = SimpleNamespace(a=pads.a,ba=pads.ba,dq=pads.dq,dm=pads.dm,
                              cs_n=pads.cs_n[:1],cke=pads.cke[:1],
                              ras_n=pads.ras_n,cas_n=pads.cas_n,we_n=pads.we_n)
        self.comb += [pads.cs_n[1].eq(1), pads.cke[1].eq(1), pads.clk.eq(~ClockSignal())]
        self.submodules.phy = phy = GENSDRPHY(one,sys_clk_freq=sys_clk_freq,cl=2)
        module = MT48LC16M16(sys_clk_freq,'1:1')
        self.submodules.controller = controller = LiteDRAMController(
            phy.settings,module.geom_settings,module.timing_settings,sys_clk_freq,
            controller_settings=ControllerSettings(with_refresh=True,with_auto_precharge=True))
        self.submodules.crossbar = crossbar = LiteDRAMCrossbar(controller.interface)
        port = crossbar.get_port(mode='both',data_width=32)
        local = wishbone.Interface(data_width=32,address_width=32,addressing='word')
        self.comb += [bus.connect(local),local.cyc.eq(bus.cyc & initialized),local.stb.eq(bus.stb & initialized)]
        self.submodules.frontend = LiteDRAMWishbone2Native(local,port)
        self.comb += controller.dfi.connect(phy.dfi)
        # Override only master-to-PHY signals during initialization; read return
        # path and upstream timing logic are unchanged after the handoff.
        p = phy.dfi.p0
        counter = Signal(max=10100)
        self.sync += If(~initialized,
            counter.eq(counter + 1),
            If(counter == 10082, initialized.eq(1)),
        )
        self.comb += If(~initialized,
            p.address.eq(0),p.bank.eq(0),p.cs_n.eq(0),p.cke.eq(1),
            p.ras_n.eq(1),p.cas_n.eq(1),p.we_n.eq(1),p.wrdata_en.eq(0),p.rddata_en.eq(0),
            p.wrdata.eq(0),p.wrdata_mask.eq(0),
            If(counter == 10002,
                p.ras_n.eq(0), p.we_n.eq(0), p.address.eq(1 << 10),
            ),
            If((counter >= 10006) & (counter <= 10062) & (counter[:3] == 6),
                p.ras_n.eq(0), p.cas_n.eq(0),
            ),
            If(counter == 10074,
                p.ras_n.eq(0), p.cas_n.eq(0), p.we_n.eq(0), p.address.eq(2 << 4),
            ),
        )
