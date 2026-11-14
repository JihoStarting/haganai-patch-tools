"""
patch_eboot_scale.py  --  by: KangJiho
Tes kecilkan font (skala 0,7) di penggambar string 0x1ad8d4 + geser Y (penggambar glyph 0x1ad77c).
Pakai: python patch_eboot_scale.py ULJS00459_EBOOT.BIN KELUARAN.BIN [geser_px=13] [--no-scale]
Hanya menulis ulang kata yang sudah dicek (ukuran file tetap, MD5 asli diperiksa).
Skala 0,7 = konstanta f24 yang sudah dimuat fungsi itu (tidak ada ruang kosong untuk konstanta lain).
"""
import hashlib, struct, sys
MD5 = "2056ae231e9bf9e07649092e408974fb"
DELTA = 0xC0                       # file offset = vaddr + 0xC0
def w(d, va, old, new):
    o = va + DELTA
    cur = struct.unpack_from("<I", d, o)[0]
    assert cur == old, f"{va:#x}: {cur:08x} != {old:08x}"
    struct.pack_into("<I", d, o, new)
a = sys.argv[1:]
no_scale = "--no-scale" in a; a = [x for x in a if x != "--no-scale"]
src, dst = a[0], a[1]; shift = int(a[2]) if len(a) > 2 else 13
d = bytearray(open(src, "rb").read())
assert hashlib.md5(d).hexdigest() == MD5, "EBOOT bukan dump terdekripsi yang dikenal"
w(d, 0x1ad7b8, 0x00e09025, 0x24e00000 | (18 << 16) | ((-shift) & 0xFFFF))      # addiu s2,a3,-shift
if not no_scale:
    # 0x1ad914..0x1ad920: [mov.s f20,f12][mov.s f22,f13][ori s1,0][mtc1 a0,f24]
    #   -> [mtc1 a0,f24][mul.s f20,f12,f24][mul.s f22,f13,f24][ori s1,0]
    w(d, 0x1ad914, 0x46006506, 0x4484C000)
    w(d, 0x1ad918, 0x46006D86, 0x46186502)
    w(d, 0x1ad91c, 0x34110000, 0x46186D82)
    w(d, 0x1ad920, 0x4484C000, 0x34110000)
open(dst, "wb").write(d)
print("OK ->", dst, "| geser Y =", shift, "| skala 0,7 =", not no_scale)
