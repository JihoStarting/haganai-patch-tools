#!/usr/bin/env python3
"""Buat varian uji envpsp.dat untuk mencari skala font kotak dialog (Fase A, R-A2/R-A3).

Pakai:  python envpsp_variants.py envpsp.dat [folder_keluaran]

Semua varian hanya menimpa 4 byte float32 di tempat (ukuran file tidak berubah,
struktur stream tidak bergeser). Sebelum menimpa, skrip memeriksa bahwa nilai
asli di offset memang sama dengan yang diharapkan; kalau tidak, berhenti.

Cara tes: salin varian ke folder game PPSSPP sebagai envpsp.dat (cadangkan yang
asli), mulai game BARU (bukan save state), buka sebuah dialog, lalu catat apa
yang berubah: ukuran huruf dialog? teks menu? daftar? atau tidak ada?
"""
import hashlib, os, struct, sys

ORIG_MD5 = "3962d0e9b9534f9590eb8d7e7360b569"

# (offset, nilai asli yang diharapkan)
GROUPS = {
    # A: rekaman di sekitar 0x935..0xa31: warna putih/hitam + skala 0,75 + 0,38.
    #    Kandidat terkuat untuk gaya teks kotak pesan.
    "A_0935_0a31": [(0x935, 0.75), (0x99D, 0.75), (0xA1D, 0.75), (0xA31, 0.75),
                    (0x9A9, 0.38)],
    # B: daftar 16 baris 0,38 (0x585..0x765) + 0,7 di 0x349.
    "B_0349_0585": [(0x349, 0.7)] + [(o, 0.38) for o in
                    (0x585, 0x589, 0x5C9, 0x5CD, 0x609, 0x60D, 0x64D, 0x651,
                     0x691, 0x695, 0x6D5, 0x6D9, 0x719, 0x71D, 0x761, 0x765)],
    # C: 0,75 dan 0,7 di blok 0x1a0f..0x1a53 (blok sebelum layar flowchart)
    "C_1a0f_1a53": [(0x1A0F, 0.75), (0x1A53, 0.7)],
}
FACTOR = 0.6   # kecilkan jadi 60% supaya perubahan jelas terlihat


def f32(v):
    return struct.pack("<f", v)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    data = open(src, "rb").read()
    md5 = hashlib.md5(data).hexdigest()
    if md5 != ORIG_MD5 or len(data) != 45711:
        sys.exit(f"envpsp.dat bukan versi asli (md5 {md5}, {len(data)} byte)")
    os.makedirs(outdir, exist_ok=True)
    log = []
    for name, items in GROUPS.items():
        buf = bytearray(data)
        for off, expect in items:
            cur = struct.unpack_from("<f", buf, off)[0]
            if buf[off:off + 4] != f32(expect):
                sys.exit(f"{name}: offset {off:#x} berisi {cur}, bukan {expect}")
            new = round(expect * FACTOR, 4)
            buf[off:off + 4] = f32(new)
            log.append(f"{name}  {off:#06x}  {expect} -> {new}")
        assert len(buf) == len(data)
        path = os.path.join(outdir, f"envpsp_{name}.dat")
        open(path, "wb").write(buf)
        print("tulis", path)
    open(os.path.join(outdir, "envpsp_variants_log.txt"), "w").write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
