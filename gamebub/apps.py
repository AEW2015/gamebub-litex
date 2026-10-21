# SPDX-License-Identifier: 0BSD
"""Software UI layer and bounded, initially-off audio/motor outputs."""
from migen import Signal, Memory, If, Mux, Cat, ClockSignal, Instance
from migen.genlib.cdc import MultiReg

from litex.gen import LiteXModule

from litex.soc.interconnect import wishbone
from litex.soc.interconnect.csr import CSRStorage, CSRStatus


# CPU Overlay -------------------------------------------------------------------------------------

class AppOverlay(LiteXModule):
    """384x240 packed 2-bit alpha/luma; visible area is the stock 360x240."""
    def __init__(self):
        self.bus = b = wishbone.Interface(data_width=32, address_width=32, addressing="word")
        self.x, self.y, self.de = Signal(10), Signal(10), Signal()
        self.valid, self.rgb = Signal(), Signal(24)
        # # #

        mem  = Memory(32, 24*240, init=[0]*(24*240))
        cpu  = mem.get_port(write_capable=True, we_granularity=8)
        scan = mem.get_port(clock_domain="video")
        self.specials += mem, cpu, scan
        pending = Signal()
        # CPU port. Only valid pixel words accept byte-enabled writes.
        self.comb += [
            cpu.adr.eq(b.adr[:13]),
            cpu.dat_w.eq(b.dat_w),
            cpu.we.eq(0),
            b.dat_r.eq(cpu.dat_r),
            b.ack.eq(pending),
            b.err.eq(0),
            If(b.cyc & b.stb & ~pending & b.we & (b.adr[:13] < 5760),
                cpu.we.eq(b.sel)
            ),
        ]
        self.sync += pending.eq(b.cyc & b.stb & ~pending)
        col, row = Signal(9), Signal(8)
        lane = Signal(4)
        requested = Signal()
        pixel = Signal(2)
        # Scan port. The five-bit shift count must not wrap at pixel eight.
        self.comb += [
            col.eq((self.y - 12) >> 1),
            row.eq(self.x >> 1),
            scan.adr.eq(row*24 + col[4:]),
            pixel.eq(scan.dat_r >> Cat(0, lane)),
            self.valid.eq(requested & pixel[1]),
            self.rgb.eq(Mux(pixel[0], 0xffffff, 0)),
        ]
        self.sync.video += [
            lane.eq(col[:4]),
            requested.eq(self.de & (self.x < 480) & (self.y >= 12) & (self.y < 732)),
        ]


# Bounded Test Outputs ----------------------------------------------------------------------------

class AppOutputs(LiteXModule):
    """A write starts a bounded one-shot; B and writing zero stop both outputs."""
    def __init__(self, platform, buttons):
        # Keep the tested register widths, names and bit positions unchanged.
        self.command  = CSRStorage(2, name="command",   description="Start outputs: bit 0 audio, bit 1 motor; zero stops both.")
        self.audio_ms = CSRStatus(11, name="audio_ms",  description="Remaining audio activation time in milliseconds.")
        self.motor_ms = CSRStatus(9, name="motor_ms",   description="Remaining motor activation time in milliseconds.")
        self.page     = CSRStorage(3, name="page",      description="Software-selected tester page.")
        self.state    = CSRStorage(3, name="state",     description="Software test state; not physical output feedback.")
        self.progress = CSRStorage(8, name="progress",  description="Software memory-test progress.")
        self.color    = CSRStorage(3, name="color",     description="LCD background pattern selector.")

        # # #

        # Independent output leases still expire if firmware stops servicing UI.
        ms = Signal(16)
        tick = Signal()
        audio, motor = Signal(11), Signal(9)
        stop = Signal()
        self.specials += MultiReg(buttons[1], stop)
        self.comb += [
            tick.eq(ms == 49999),
            self.audio_ms.status.eq(audio),
            self.motor_ms.status.eq(motor),
        ]
        self.sync += [
            ms.eq(ms + 1),
            If(tick,
                ms.eq(0),
                If(audio != 0, audio.eq(audio - 1)),
                If(motor != 0, motor.eq(motor - 1)),
            ),
            If(self.command.re,
                audio.eq(Mux(self.command.storage[0], 1000, 0)),
                motor.eq(Mux(self.command.storage[1], 200, 0)),
            ),
            If(stop,
                audio.eq(0),
                motor.eq(0),
            ),
        ]

        # Forward/coast PWM. IN2 never asserts reverse drive or active braking.
        pwm = Signal(12)
        self.sync += If(pwm == 2499, pwm.eq(0)).Else(pwm.eq(pwm + 1))
        self.comb += [
            platform.request("vibrate_in1").eq((motor != 0) & (pwm < 1250)),
            platform.request("vibrate_in2").eq(0),
        ]
        # Match the known-good DAC DSP framing: 608 MCLK/frame, inverted
        # divide-by-8 BCLK, 16-bit signed left then right, offset zero.
        enabled_sys, enabled = Signal(), Signal()
        self.sync += enabled_sys.eq(audio != 0)
        self.specials += MultiReg(enabled_sys, enabled, odomain="video")
        counter, phase, serial, word_clock = Signal(10), Signal(32), Signal(32), Signal()
        sample = Signal(16)
        step = round((2**32)*440/(800_000_000/27.25/608))
        self.comb += [
            sample.eq(Mux(enabled, Mux(phase[31], 65536 - 2048, 2048), 0)),
            platform.request("dac_bclk").eq(~counter[2]),
            platform.request("dac_wclk").eq(word_clock),
            platform.request("dac_din").eq(serial[31]),
        ]
        self.specials += Instance("ODDR", p_DDR_CLK_EDGE="SAME_EDGE", p_INIT=0, p_SRTYPE="SYNC",
            i_C=ClockSignal("video"), i_CE=1, i_D1=1, i_D2=0, i_R=0, i_S=0,
            o_Q=platform.request("dac_mclk"))
        self.sync.video += [
            counter.eq(counter + 1),
            If(counter[:3] == 7,
                serial.eq(serial << 1),
                word_clock.eq(0),
            ),
            If(counter == 607,
                counter.eq(0),
                serial.eq(Cat(sample, sample)),
                word_clock.eq(1),
                phase.eq(phase + step),
            ),
        ]
