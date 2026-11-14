#!/usr/bin/env python3
"""Varian D: kecilkan SEMUA float skala kandidat di envpsp.dat sekaligus.

Pakai:  python envpsp_variant_D.py envpsp.dat [envpsp_D_all.dat]

Tujuan uji ya/tidak: kalau dialog TIDAK berubah dengan varian ini, skala dialog
hampir pasti bukan di envpsp.dat (jalur envpsp ditutup). Kalau berubah, varian
dipecah dua (separuh offset) berulang sampai ketemu offsetnya.
Hanya menimpa 4 byte float di tempat; ukuran file tetap 45.711 byte.
"""
import hashlib, struct, sys

ORIG_MD5 = "3962d0e9b9534f9590eb8d7e7360b569"
VALUES = [0.38, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9]   # semua < 1,0
FACTOR = 0.6


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "envpsp_D_all.dat"
    data = open(src, "rb").read()
    if hashlib.md5(data).hexdigest() != ORIG_MD5:
        sys.exit("envpsp.dat bukan versi asli")
    buf = bytearray(data)
    offs = []
    for v in VALUES:
        pat = struct.pack("<f", v)
        i = data.find(pat)
        while i != -1:
            offs.append((i, v))
            i = data.find(pat, i + 1)
    offs.sort()
    # lewati tumpang tindih (dua kecocokan yang saling menimpa)
    used_end = -1
    kept = []
    for o, v in offs:
        if o >= used_end:
            kept.append((o, v))
            used_end = o + 4
    for o, v in kept:
        buf[o:o + 4] = struct.pack("<f", v * FACTOR)
    open(dst, "wb").write(buf)
    open(dst + ".log.txt", "w").write(
        "\n".join(f"{o:#06x} {v} -> {round(v*FACTOR,4)}" for o, v in kept) + "\n")
    print(f"{len(kept)} float diubah -> {dst}")


if __name__ == "__main__":
    main()
