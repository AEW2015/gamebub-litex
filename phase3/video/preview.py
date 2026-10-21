# SPDX-License-Identifier: 0BSD
"""Losslessly wrap a simulator RGB P6 capture in PNG, using only stdlib."""
import argparse
from pathlib import Path
import struct
import zlib


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ppm", type=Path)
    p.add_argument("png", type=Path)
    a = p.parse_args()
    if a.png.exists(): p.error("refusing to replace an existing preview")
    magic, geometry, maximum, pixels = a.ppm.read_bytes().split(b"\n", 3)
    width, height = map(int, geometry.split())
    if magic != b"P6" or maximum != b"255" or len(pixels) != width*height*3:
        p.error("expected complete RGB888 P6 capture")
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    scanlines=b"".join(b"\0"+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    png=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))
    png+=chunk(b"IDAT",zlib.compress(scanlines))+chunk(b"IEND",b"")
    a.png.write_bytes(png)


if __name__=="__main__":main()
