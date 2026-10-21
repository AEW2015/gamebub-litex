# SPDX-License-Identifier: 0BSD
"""GameBub v1.0.2-compatible QSPI service subset and LiteX diagnostics.

The phase4 endpoint timing variant lives in ``rtl/``. This wrapper
provides explicit pins, a CPU-visible read-only diagnostic Wishbone window
with a bundled-data request/ack CDC, and the native overlay BRAM reader.
"""

from pathlib import Path

from migen import Cat, ClockSignal, If, Instance, Memory, Replicate, ResetSignal, Signal
from migen.genlib.cdc import MultiReg
from litex.gen import LiteXModule
from litex.soc.interconnect import wishbone


class ESP32OverlayReader(LiteXModule):
    """360x240 ARGB1555 framebuffer with the stock rotated panel mapping.

    ``connect_video(video)`` connects the synchronous reader to the request
    interface used by phase3/video. Requests are sampled in ``video`` domain;
    the corresponding opaque/monochrome pixel is available one cycle later.
    """

    WIDTH = 360
    HEIGHT = 240
    PIXELS = WIDTH * HEIGHT

    def __init__(self, ov_wr, ov_addr, ov_data, *, service_domain="service"):
        self.valid = Signal()
        self.rgb = Signal(24)
        self.x = Signal(9)
        self.y = Signal(10)
        self.de = Signal()

        memory = Memory(width=2, depth=self.PIXELS, init=[0] * self.PIXELS)
        wr = memory.get_port(write_capable=True, clock_domain=service_domain)
        rd = memory.get_port(async_read=False, clock_domain="video")
        self.specials += memory, wr, rd

        # Two full-throughput pipeline stages isolate luma arithmetic from
        # the 200MHz BRAM write input. Address, alpha and valid travel together.
        # Every input pulse is accepted, including one on every service cycle.
        wr_addr = ov_addr[1:]
        sum_rb_s1 = Signal(7, name="overlay_sum_rb_s1")  # 2R+B <=93
        sum_g_s1 = Signal(8, name="overlay_sum_g_s1")    # 5G <=155
        alpha_s1 = Signal(name="overlay_alpha_s1")
        addr_s1 = Signal(17, name="overlay_addr_s1")
        valid_s1 = Signal(name="overlay_valid_s1")
        sum_s1 = Signal(8, name="overlay_sum_s1")       # total <=248
        addr_s2 = Signal(17, name="overlay_addr_s2")
        valid_s2 = Signal(name="overlay_valid_s2")
        pixel_s2 = Signal(2, name="overlay_pixel_s2")
        self.comb += [
            sum_s1.eq(sum_rb_s1 + sum_g_s1),
            wr.adr.eq(addr_s2),
            wr.we.eq(valid_s2),
            wr.dat_w.eq(pixel_s2),
        ]
        getattr(self.sync, service_domain).__iadd__([
            sum_rb_s1.eq((ov_data[10:15] << 1) + ov_data[0:5]),
            sum_g_s1.eq((ov_data[5:10] << 2) + ov_data[5:10]),
            alpha_s1.eq(ov_data[15]),
            addr_s1.eq(wr_addr),
            valid_s1.eq(ov_wr & ~ov_addr[0] & (wr_addr < self.PIXELS)),
            addr_s2.eq(addr_s1),
            valid_s2.eq(valid_s1),
            pixel_s2.eq(Cat(sum_s1 >= 128, alpha_s1)),
        ])

        inside = (self.de & (self.x < 480) & (self.y >= 12) & (self.y < 732))
        # Stock native scanner rotates 360x240 into x=0..479, y=12..731.
        # Its RTL address is (x >> 1) * 360 + ((y - 12) >> 1).
        row = self.x[1:]
        col = (self.y - 12) >> 1
        address = Signal(17)
        requested = Signal()
        pixel = rd.dat_r
        self.comb += [
            address.eq(row * 360 + col),
            rd.adr.eq(address),
        ]
        self.sync.video += requested.eq(inside)
        # The Memory read port and requested flag update on the same edge.
        # This exactly supplies the video block's one-cycle look-ahead input.
        white = pixel[0]
        self.comb += [
            self.valid.eq(requested & pixel[1]),
            self.rgb.eq(Cat(Replicate(white, 8), Replicate(white, 8),
                            Replicate(white, 8))),
        ]

    def connect_video(self, video):
        self.comb += [
            self.x.eq(video.overlay_x),
            self.y.eq(video.overlay_y),
            self.de.eq(video.overlay_de),
            video.overlay_valid.eq(self.valid),
            video.overlay_rgb.eq(self.rgb),
        ]


class ESP32Service(LiteXModule):
    """Portable endpoint wrapper.

    ``pads`` is a resource with ``sck``, ``cs_n``, ``dq_i``, ``dq_o`` and
    ``dq_oe`` subsignals. If omitted, ``platform.request('qspi')`` is used.
    The CPU Wishbone aperture is read-only and exposes endpoint diagnostics at
    word offsets 0x00..0x3c. QSPI control/register and overlay accesses remain
    in the native ESP32 protocol engine.
    """

    def __init__(self, platform, pads=None, *, service_domain="service",
                 sys_domain="sys", with_overlay=True):
        self.pads = pads if pads is not None else platform.request("qspi")
        self.buttons_native = Signal(12, name="buttons_native")
        self.irq_gate = Signal(name="esp32_irq_gate")
        self.cpu_irq = Signal(name="esp32_cpu_irq")
        self.vblank = Signal(name="esp32_vblank")
        self.bus = wishbone.Interface(data_width=32, address_width=32,
                                      addressing="word")

        rtl = Path(__file__).resolve().parent / "rtl" / "esp32_v102_endpoint.sv"
        platform.add_source(str(rtl))

        dq_o = Signal(4)
        dq_oe = Signal(4)
        irq_request = Signal()
        diag_select = Signal(5)
        diag_data = Signal(32)
        ov_wr = Signal()
        ov_addr = Signal(18)
        ov_data = Signal(16)
        control = Signal(4)
        forced = Signal(12)
        display_external = Signal()
        color_correct_enable = Signal()
        overlay_xctrl = Signal(24)
        overlay_yctrl = Signal(24)
        mailbox_wr = Signal()
        mailbox_addr = Signal(14)
        mailbox_wdata = Signal(32)

        self.specials += Instance(
            "esp32_v102_endpoint",
            i_clk200=ClockSignal(service_domain),
            i_rst_n=~ResetSignal(service_domain),
            i_qspi_sck=self.pads.sck,
            i_qspi_cs_n=self.pads.cs_n,
            i_qspi_dq_i=self.pads.dq_i,
            o_dq_o=dq_o,
            o_dq_oe=dq_oe,
            i_buttons_native=self.buttons_native,
            i_vblank=self.vblank,
            o_irq_request=irq_request,
            o_control=control,
            o_force_buttons_native=forced,
            o_display_external=display_external,
            o_color_correct_enable=color_correct_enable,
            o_overlay_xctrl=overlay_xctrl,
            o_overlay_yctrl=overlay_yctrl,
            o_ov_wr=ov_wr,
            o_ov_addr=ov_addr,
            o_ov_data=ov_data,
            o_mailbox_wr=mailbox_wr,
            o_mailbox_addr=mailbox_addr,
            o_mailbox_wdata=mailbox_wdata,
            i_mailbox_rdata=0,
            i_diag_select=diag_select,
            i_inject_toggle=0,
            o_diag_data=diag_data,
        )

        self.comb += [
            self.pads.dq_o.eq(dq_o),
            self.pads.dq_oe.eq(dq_oe),
            self.irq_gate.eq(irq_request),
        ]
        self.specials += MultiReg(irq_request, self.cpu_irq, odomain=sys_domain)

        self.overlay = None
        if with_overlay:
            self.overlay = ESP32OverlayReader(ov_wr, ov_addr, ov_data,
                                              service_domain=service_domain)

        self._add_diagnostic_cdc(service_domain, sys_domain, diag_select, diag_data)

    def _add_diagnostic_cdc(self, service_domain, sys_domain, diag_select,
                            diag_data):
        """Single-outstanding bundled-data Wishbone request/response CDC."""
        bus = self.bus
        request_toggle = Signal()
        request_sync = Signal()
        acknowledge_toggle = Signal()
        acknowledge_sync = Signal()
        pending = Signal()
        ack_seen = Signal()
        req_addr = Signal(32)
        req_we = Signal()
        req_wdata = Signal(32)
        req_sel = Signal(4)
        response_data = Signal(32)
        response_sync = Signal(32)
        service_addr = Signal(32)
        service_we = Signal()
        state = Signal(2, reset=0)
        service_data = Signal(32)

        self.specials += [
            MultiReg(acknowledge_toggle, acknowledge_sync, odomain=sys_domain),
            MultiReg(request_toggle, request_sync, odomain=service_domain),
            MultiReg(response_data, response_sync, odomain=sys_domain),
        ]

        self.comb += [
            bus.dat_r.eq(response_sync),
            bus.ack.eq(pending & ack_seen),
            bus.err.eq(0),
        ]
        getattr(self.sync, sys_domain).__iadd__(If(
            bus.cyc & bus.stb & ~pending,
            req_addr.eq(bus.adr),
            req_we.eq(bus.we),
            req_wdata.eq(bus.dat_w),
            req_sel.eq(bus.sel),
            request_toggle.eq(~request_toggle),
            pending.eq(1),
            ack_seen.eq(0),
        ).Elif(pending & (acknowledge_sync == request_toggle),
            If(ack_seen, pending.eq(0), ack_seen.eq(0)).Else(ack_seen.eq(1))
        ))

        getattr(self.sync, service_domain).__iadd__([
            If(state == 0,
                If(request_sync != acknowledge_toggle,
                    service_addr.eq(req_addr),
                    service_we.eq(req_we),
                    state.eq(1),
                )
            ).Elif(state == 1,
                diag_select.eq(service_addr[0:5]),
                state.eq(2),
            ).Else(
                service_data.eq(diag_data),
                # Address decoding by the parent selects a 4KiB aperture.
                # Only its first16 words are defined: reject aliasing, and
                # ignore CPU writes rather than exposing endpoint controls.
                response_data.eq(0),
                If(~service_we & (service_addr[:10] < 16),
                   response_data.eq(diag_data)),
                acknowledge_toggle.eq(request_sync),
                state.eq(0),
            )
        ])
