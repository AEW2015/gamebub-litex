# SPDX-License-Identifier: 0BSD
"""Generate successive architecture artwork revisions, not hardware netlists."""
from pathlib import Path
from html import escape
import argparse
import json
import cairosvg

ROOT = Path(__file__).resolve().parent


def render(version):
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1580" height="960" viewBox="0 0 1580 960">',
           '<title>GameBub LiteX Tester</title>',
           '<desc>Simplified tester architecture. Independent peripheral lanes avoid wire crossings. ESP32 overlay and CPU UI feed the native LCD compositor. Memory controllers serve CPU accesses, not an external framebuffer.</desc>',
           '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#606060"/></marker></defs>',
           '<rect width="1580" height="960" fill="white"/>']
    blocks, segments = [], []

    def text(x, y, value, size=18, bold=False, anchor='middle'):
        svg.append(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(value)}</text>')

    def shape(x, y, w, h, fill='#bbb', cut=12):
        d = f'M{x} {y}H{x+w-cut}L{x+w} {y+cut}V{y+h}H{x+cut}L{x} {y+h-cut}Z'
        for shift, alpha in [(5, .035), (3, .065), (1.5, .10)]:
            svg.append(f'<path d="{d}" transform="translate({shift},{shift})" fill="black" opacity="{alpha}"/>')
        svg.append(f'<path d="{d}" fill="{fill}" stroke="#555" stroke-width="1"/>')

    def block(name, x, y, w, h, lines, fill='#bbb'):
        blocks.append((name, x, y, x+w, y+h))
        shape(x, y, w, h, fill)
        for i, line in enumerate(lines):
            text(x+w/2, y+h/2-(len(lines)-1)*12+6+i*24, line, 18 if i == 0 else 16, i == 0)

    def wire(name, points, both=False, arrow=True):
        # Orthogonal paths are retained as geometry for a separate routing audit.
        for a, b in zip(points, points[1:]):
            assert a[0] == b[0] or a[1] == b[1], name
            segments.append((name, a, b))
        path = 'M' + 'L'.join(f'{x} {y}' for x, y in points)
        start = 'marker-start="url(#a)"' if both else ''
        end = 'marker-end="url(#a)"' if arrow else ''
        svg.append(f'<path d="{path}" fill="none" stroke="#606060" stroke-width="1.8" {start} {end}/>')

    shape(250, 70, 1030, 770, '#fff', 28)
    shape(275, 100, 980, 710, '#f3f3f3', 22)

    wire('rom', [(440, 175), (600, 175)], both=True)
    wire('ram', [(440, 285), (520, 285), (520, 220), (600, 220)], both=True)
    wire('cpu-bus', [(715, 250), (715, 420)], arrow=False)
    wire('jtag-bus', [(370, 400), (370, 420)], arrow=False)
    sram_bus_y = 180 if version == 4 else 205
    sram_bus_points = [(1000, 180), (970, 180), (970, 420)] if version >= 6 else [(1200, sram_bus_y), (1220, sram_bus_y), (1220, 420)]
    wire('sram-bus', sram_bus_points, arrow=False)
    wire('sdram-bus', [(1100, 360), (1100, 420)], arrow=False)
    wire('sram-pins', [(1200, 180), (1330, 180)], both=True)
    wire('sdram-pins', [(1200, 320), (1330, 320)], both=True)
    wire('jtag-pins', [(210, 375), (300, 375)], both=True)
    wire('buttons-bus', [(365, 455), (365, 500)], arrow=False)
    wire('outputs-bus', [(470, 455), (470, 755)], arrow=False)
    wire('audio-csr', [(470, 645), (430, 645)], arrow=False)
    wire('motor-csr', [(470, 755), (430, 755)], arrow=False)
    wire('ui-bus', [(665, 455), (665, 500)], arrow=False)
    wire('esp-bus', [(1100, 455), (1100, 500)], arrow=False)
    wire('buttons-pins', [(210, 535), (300, 535)])
    wire('audio-pins', [(300, 645), (210, 645)])
    wire('motor-pins', [(300, 755), (210, 755)])
    wire('cpu-ui-pixels', [(665, 570), (665, 700)])
    wire('esp-overlay-pixels', [(1100, 570), (1100, 650), (900, 650), (900, 700)])
    wire('qspi-pins', [(1200, 520), (1330, 520)], both=True)
    wire('irq-pins', [(1200, 550), (1330, 550)])
    wire('lcd-pins', [(930, 735), (1330, 735)])

    block('cpu', 600, 140, 230, 110, ['VexRiscv CPU', 'RV32I · 50 MHz'], '#f3f3f3')
    block('rom', 300, 140, 140, 70, ['ROM', '16 KiB'], '#f3f3f3')
    block('ram', 300, 250, 140, 70, ['RAM', '16 KiB'], '#f3f3f3')
    block('jtag', 300, 350, 140, 50, ['JTAG UART'])
    block('sram', 1000, 140, 200, 80, ['SRAM controller'])
    block('sdram', 1000, 280, 200, 80, ['LiteDRAM', 'SDR SDRAM'])
    text(715 if version == 4 else 865, 355, 'LiteX SoC', 26)
    svg.append('<rect x="300" y="420" width="920" height="35" fill="#bbb" stroke="#555"/>')
    text(760, 444, 'Wishbone / CSR', 18)

    block('buttons', 300, 500, 130, 70, ['Buttons'])
    block('audio', 300, 610, 130, 70, ['Audio'])
    block('motor', 300, 720, 130, 70, ['Motor PWM'])
    block('ui', 600, 500, 130, 70, ['UI BRAM'])
    block('esp', 1000, 500, 200, 70, ['ESP32 QSPI', 'Overlay BRAM'])
    block('video', 600, 700, 330, 70, ['LCD video', 'Pattern + UI + overlay'])

    block('host', 20, 340, 190, 70, ['USB / JTAG'], '#eee')
    block('keys', 20, 500, 190, 70, ['12 buttons'], '#eee')
    block('dac', 20, 610, 190, 70, ['Audio DAC'], '#eee')
    block('motor-driver', 20, 720, 190, 70, ['Motor'], '#eee')
    block('external-sram', 1330, 140, 220, 80, ['512 KiB SRAM'], '#eee')
    block('external-sdram', 1330, 280, 220, 80, ['32 MiB SDRAM'], '#eee')
    block('esp32', 1330, 500, 220, 70, ['ESP32'], '#eee')
    block('lcd', 1330, 700, 220, 70, ['LCD', '480 × 800'], '#eee')

    text(1265, 509, 'QSPI', 14)
    text(1265, 542, 'IRQ', 14)
    if version == 4:
        text(665, 625, 'UI pixels', 15)
        text(990, 640, 'ESP32 pixels', 15)
        text(1120, 723, 'RGB888 / sync / clock', 15)
    elif version == 5:
        text(995, 640, 'Overlay', 15)
        text(1130, 723, 'RGB888', 15)

    if version >= 5:
        # Dot denotes a real shared CSR branch, never a crossing.
        svg.append('<circle cx="470" cy="645" r="2.5" fill="#606060"/>')

    text(280, 91, 'GameBub', 15, True, 'start')
    text(1260, 827, 'FPGA', 15, True, 'end')
    text(790, 905, 'GameBub LiteX Tester', 36)
    text(790, 940, 'Built with LiteX', 17)
    svg.append('</svg>')
    target = ROOT / f'gamebub-litex-clean-v{version}.svg'
    target.write_text('\n'.join(svg), encoding='utf-8')
    cairosvg.svg2png(url=str(target), write_to=str(target.with_suffix('.png')))

    # Check proper wire crossings and any segment running through a block.
    # Touching endpoints and intended T branches are not counted as crossings.
    crossings, through_blocks = [], []
    for i, (name, a, b) in enumerate(segments):
        for other, c, d in segments[i+1:]:
            if name == other:
                continue
            first_h, second_h = a[1] == b[1], c[1] == d[1]
            if first_h == second_h:
                continue
            h1, h2, v1, v2 = (a, b, c, d) if first_h else (c, d, a, b)
            if min(h1[0], h2[0]) < v1[0] < max(h1[0], h2[0]) and min(v1[1], v2[1]) < h1[1] < max(v1[1], v2[1]):
                crossings.append([name, other, [v1[0], h1[1]]])
        for block_name, left, top, right, bottom in blocks:
            if a[1] == b[1]:
                intersects = top < a[1] < bottom and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right)
            else:
                intersects = left < a[0] < right and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), bottom)
            if intersects:
                through_blocks.append([name, block_name])
    audit = {'version': version, 'proper_wire_crossings': crossings, 'wires_through_blocks': through_blocks,
             'note': 'Geometric diagram checks, not hardware/RTL verification. Endpoints and intended T junctions excluded.'}
    target.with_suffix('.routing.json').write_text(json.dumps(audit, indent=2)+'\n', encoding='utf-8')
    assert not crossings and not through_blocks, audit
    print(f'v{version}: no proper wire crossings or wires through blocks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('version', type=int, choices=(4, 5, 6))
    render(parser.parse_args().version)
