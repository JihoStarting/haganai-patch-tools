#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_tabel.py - HANYA MEMBACA. Membedah irisan RES.DAT yang berisi tabel Flowchart.

Format yang dicari: [u32 jumlah_karakter][string UTF-16LE] (alamat tidak harus genap).
Hasil:
  1. irisan_<start>.bin   -> salinan mentah irisan (untuk dikirim)
  2. hasil_tabel.txt      -> daftar string + byte biner di antaranya + hexdump awal

Pakai:
  python dump_tabel.py "..\\data ekstrak\\RES.DAT"
  python dump_tabel.py "..\\data ekstrak\\RES.DAT" --start 0x0d5e7000 --size 0x6000
"""
import sys
import struct
import argparse


def int0(x):
    return int(x, 0)


def ok_char(c):
    """Karakter yang wajar untuk teks game (Jepang / ASCII / tanda baca)."""
    return (
        0x20 <= c <= 0x7E
        or 0x00A0 <= c <= 0x00FF
        or 0x2000 <= c <= 0x206F
        or 0x2190 <= c <= 0x25FF
        or 0x2600 <= c <= 0x26FF
        or 0x3000 <= c <= 0x30FF
        or 0x3400 <= c <= 0x4DBF
        or 0x4E00 <= c <= 0x9FFF
        or 0xFF00 <= c <= 0xFFEF
    )


def find_strings(buf):
    """Kembalikan list (offset_u32, n, teks) tanpa tumpang tindih."""
    res, p, end = [], 0, len(buf)
    while p + 6 <= end:
        n = struct.unpack_from("<I", buf, p)[0]
        if 1 <= n <= 400 and p + 4 + 2 * n <= end:
            chars = struct.unpack_from("<%dH" % n, buf, p + 4)
            if all(ok_char(c) for c in chars):
                # saring false positive: n=1 dan bukan CJK/kana/tanda baca
                if n == 1 and chars[0] < 0x3000:
                    p += 1
                    continue
                res.append((p, n, "".join(map(chr, chars))))
                p += 4 + 2 * n
                continue
        p += 1
    return res


def hexline(b, base, width=16):
    out = []
    for i in range(0, len(b), width):
        ch = b[i:i + width]
        hx = " ".join("%02x" % x for x in ch)
        out.append("%08x  %-*s" % (base + i, width * 3, hx))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--start", type=int0, default=0x0D5E7000)
    ap.add_argument("--size", type=int0, default=0x6000)
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    with open(a.file, "rb") as f:
        f.seek(a.start)
        buf = f.read(a.size)

    binname = "irisan_%08x.bin" % a.start
    with open(binname, "wb") as f:
        f.write(buf)

    strs = find_strings(buf)
    L = []
    L.append("File  : %s" % a.file)
    L.append("Irisan: 0x%08x .. 0x%08x (%d byte), disimpan ke %s"
             % (a.start, a.start + len(buf), len(buf), binname))
    L.append("Ditemukan %d string berawalan u32 jumlah-karakter" % len(strs))
    L.append("=" * 70)
    L.append("Awal irisan (hexdump 256 byte pertama dari string pertama - 64):")
    if strs:
        s0 = max(0, strs[0][0] - 64)
        L.append(hexline(buf[s0:s0 + 320], a.start + s0))
    L.append("=" * 70)
    L.append("DAFTAR STRING (offset_absolut | n | jarak_dari_string_sebelumnya | teks)")
    L.append("Di antara string: byte biner ditampilkan (dipotong 40 byte).")
    L.append("-" * 70)

    prev_end = None
    for off, n, txt in strs:
        absoff = a.start + off
        if prev_end is not None:
            gap = buf[prev_end:off]
            L.append("   gap %3d byte: %s%s" % (
                len(gap), gap[:40].hex(" "), " ..." if len(gap) > 40 else ""))
        shown = txt.replace("\n", "\\n")
        L.append("0x%08x | n=%3d | %s" % (absoff, n, shown))
        prev_end = off + 4 + 2 * n

    L.append("=" * 70)
    L.append("Selesai.")

    text = "\n".join(L)
    with open("hasil_tabel.txt", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text[:3000])
    if len(text) > 3000:
        print("\n... (lengkapnya di hasil_tabel.txt)")


if __name__ == "__main__":
    main()
