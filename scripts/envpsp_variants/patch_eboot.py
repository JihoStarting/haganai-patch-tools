#!/usr/bin/env python3
"""Patch uji EBOOT terdekripsi: geser posisi Y semua teks yang digambar lewat
penggambar glyph 0x1ad77c (Fase A, R-A3).

Pakai:  python patch_eboot.py ULJS00459_EBOOT.BIN KELUARAN.bin [geser_px]
        geser_px default 13 (positif = teks naik)

Yang diubah: SATU instruksi di vaddr 0x1ad7b8 (file 0x1ad878):
    move  $s2,$a3            (0x00e09025)
  -> addiu $s2,$a3,-geser    ($a3 = posisi Y glyph; instruksi ini tidak direlokasi)
Ukuran file tetap 4.953.616 byte. Skrip memeriksa MD5 asli dan kata asli dulu.
"""
import hashlib, struct, sys
ORIG_MD5 = "2056ae231e9bf9e07649092e408974fb"
VA = 0x1AD7B8
ORIG_WORD = 0x00E09025

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    shift = int(sys.argv[3]) if len(sys.argv) > 3 else 13
    d = bytearray(open(src, "rb").read())
    if hashlib.md5(d).hexdigest() != ORIG_MD5 or len(d) != 4953616:
        sys.exit("EBOOT bukan dump terdekripsi yang diharapkan (MD5/ukuran beda)")
    fo = VA + 0xC0
    cur = struct.unpack_from("<I", d, fo)[0]
    if cur != ORIG_WORD:
        sys.exit(f"kata di {fo:#x} = {cur:#010x}, bukan {ORIG_WORD:#010x}")
    new = (9 << 26) | (7 << 21) | (18 << 16) | (0xFFFF & -shift)   # addiu s2,a3,-shift
    struct.pack_into("<I", d, fo, new)
    open(dst, "wb").write(d)
    print(f"ok: file {fo:#x}: {cur:#010x} -> {new:#010x} (Y -{shift} px) -> {dst}")

if __name__ == "__main__":
    main()
