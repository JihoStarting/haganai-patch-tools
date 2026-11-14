#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cari_string.py - pencari string Jepang (HANYA MEMBACA, tidak mengubah file).

Mencari teks dalam 3 encoding: UTF-16LE, Shift-JIS (cp932), UTF-8.
Juga membongkar aliran gzip yang tertanam (magic 1f 8b 08) lalu mencari di dalamnya.

Pakai:
  python cari_string.py <file> [teks ...] [--max N] [--out hasil.txt] [--nogzip]

Contoh:
  python cari_string.py envpsp.dat
  python cari_string.py RES.DAT プロローグ 共通ルート --out hasil_res.txt

Tanpa [teks], dipakai 3 teks bawaan: プロローグ, 共通ルート, 南の島で
"""
import sys
import zlib
import struct
import argparse

DEFAULT = ["プロローグ", "共通ルート", "南の島で"]
ENCODINGS = [("utf-16le", "UTF-16LE"), ("cp932", "Shift-JIS"), ("utf-8", "UTF-8")]


def find_all(data, needle, limit):
    pos, hits = 0, []
    while len(hits) < limit:
        i = data.find(needle, pos)
        if i < 0:
            break
        hits.append(i)
        pos = i + 1
    return hits


def context(data, off, nlen, enc):
    """Ambil teks di sekitar hit (decode seaman mungkin)."""
    a = max(0, off - 16)
    b = min(len(data), off + nlen + 40)
    chunk = data[a:b]
    if enc == "utf-16le" and (off - a) % 2:
        chunk = chunk[1:]
    try:
        s = chunk.decode(enc, errors="replace")
    except Exception:
        s = repr(chunk)
    return s.replace("\n", "\\n").replace("\r", "\\r").replace("\x00", "")


def search_buffer(data, texts, limit, label, out):
    total = 0
    for t in texts:
        for enc, name in ENCODINGS:
            try:
                needle = t.encode(enc)
            except Exception:
                continue
            for off in find_all(data, needle, limit):
                total += 1
                extra = ""
                if enc == "utf-16le" and off >= 4:
                    n = struct.unpack("<I", data[off - 4:off])[0]
                    extra = f"  [u32 sebelum={n}]"
                out(f"{label}0x{off:08x}  {name:9s} '{t}'{extra}")
                out(f"      ...{context(data, off, len(needle), enc)}...")
    return total


def scan_gzip(data, texts, limit, out):
    total, streams, pos = 0, 0, 0
    magic = b"\x1f\x8b\x08"
    while True:
        i = data.find(magic, pos)
        if i < 0:
            break
        pos = i + 3
        try:
            d = zlib.decompressobj(31)
            raw = d.decompress(data[i:i + 8 * 1024 * 1024])
        except Exception:
            continue
        if len(raw) < 8:
            continue
        streams += 1
        total += search_buffer(raw, texts, limit, f"gzip@0x{i:08x} +", out)
    return total, streams


def main():
    ap = argparse.ArgumentParser(description="Pencari string Jepang (read-only)")
    ap.add_argument("file")
    ap.add_argument("teks", nargs="*")
    ap.add_argument("--max", type=int, default=50, help="maks hit per teks per encoding")
    ap.add_argument("--out", help="simpan hasil ke file (UTF-8)")
    ap.add_argument("--nogzip", action="store_true", help="lewati pemindaian gzip")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    fh = open(a.out, "w", encoding="utf-8") if a.out else None

    def out(s):
        print(s)
        if fh:
            fh.write(s + "\n")

    texts = a.teks or DEFAULT
    with open(a.file, "rb") as f:
        data = f.read()

    out(f"File : {a.file} ({len(data):,} byte)")
    out(f"Cari : {', '.join(texts)}")
    out("-" * 60)

    n = search_buffer(data, texts, a.max, "raw   ", out)
    g = streams = 0
    if not a.nogzip:
        g, streams = scan_gzip(data, texts, a.max, out)

    out("-" * 60)
    out(f"Selesai: {n} hit mentah, {g} hit di dalam gzip ({streams} aliran gzip terbaca).")
    if n + g == 0:
        out("Tidak ada hit. Belum tentu berarti tidak ada: teks bisa dikompres/dienkripsi atau memakai encoding lain.")
    if fh:
        fh.close()


if __name__ == "__main__":
    main()
