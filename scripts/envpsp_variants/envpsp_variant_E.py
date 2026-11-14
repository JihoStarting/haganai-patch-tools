#!/usr/bin/env python3
"""Varian E: kecilkan hanya float skala yang tepat didahului warna ARGB (170 offset).

Pakai:  python envpsp_variant_E.py envpsp.dat [envpsp_E_color.dat]
Filter ini membuang kecocokan palsu yang membuat varian D hang. Hanya menimpa
4 byte float di tempat; ukuran file tetap 45.711 byte.
"""
import hashlib, struct, sys
ORIG_MD5 = "3962d0e9b9534f9590eb8d7e7360b569"
FACTOR = 0.6

def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "envpsp_E_color.dat"
    d = open(src, "rb").read()
    if hashlib.md5(d).hexdigest() != ORIG_MD5:
        sys.exit("envpsp.dat bukan versi asli")
    buf = bytearray(d)
    kept = []
    for o in range(4, len(d) - 4):
        if d[o - 1] == 0xFF:
            v = struct.unpack_from("<f", d, o)[0]
            if v == v and 0.2 <= v <= 3.0 and abs(v * 100 - round(v * 100)) < 1e-3 \
               and d[o:o + 4] != b"\0\0\0\0":
                kept.append((o, round(v, 3)))
    for o, v in kept:
        buf[o:o + 4] = struct.pack("<f", v * FACTOR)
    open(dst, "wb").write(buf)
    open(dst + ".log.txt", "w").write(
        "\n".join(f"{o:#06x} {v} -> {round(v*FACTOR,4)}" for o, v in kept) + "\n")
    print(f"{len(kept)} float diubah -> {dst}")

if __name__ == "__main__":
    main()
