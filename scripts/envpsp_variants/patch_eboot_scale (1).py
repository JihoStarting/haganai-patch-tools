#!/usr/bin/env python3
"""
patch_eboot_scale.py : kecilkan teks dialog (blok teks di bagian bawah layar)
dan kembalikan teks choice ke posisi aslinya. Menggantikan patch_eboot.py (geser Y).

Pakai:
  python patch_eboot_scale.py MASUKAN.BIN KELUARAN.BIN [--k 0.72] [--top 207] [--thr 200] [--x0 45] [--y0 218] [--kx 0.72]

MASUKAN boleh dump asli (ULJS00459_EBOOT.BIN, MD5 2056ae23...) atau varian
patch_eboot.py lama (Y8/Y13/Y18/Y34); geser Y lama otomatis dibatalkan.

Cara kerja (semua teks lewat penggambar glyph 0x1ad77c):
  1. instruksi 0x1ad7b8 dikembalikan ke asli (tanpa geser Y).
  2. 'jal 0x1ad430' di 0x1ad7c8 diarahkan ke kode kecil di 0x1a9980
     (badan fungsi std::vector yang tidak dipanggil siapa pun).
  3. kode itu: bila y glyph >= thr, glyph diciutkan terhadap titik (x0,y0)
     dengan faktor k lalu ditaruh mulai y=top; skala glyph juga dikali k.
     Lalu lompat ke 0x1ad430 (alamat dihitung dari $ra, tanpa relokasi baru).
  Teks dengan y < thr (choice, judul, dll.) tidak tersentuh.
"""
import struct, sys, hashlib, argparse

BASE = 0xc0
HOOK_Y   = 0x1ad7b8   # instruksi geser Y lama
HOOK_JAL = 0x1ad7c8   # jal 0x1ad430
CAVE     = 0x1a9980
CAVE_MAX = 0xac       # 172 byte
ORIG_Y   = 0x00e09025 # or $s2,$a3,$zero
CAVE_ORIG_MD5 = "a89867841b97344c3f52ae5762f59222"

def enc_i(op, rs, rt, imm): return (op<<26)|(rs<<21)|(rt<<16)|(imm&0xffff)
def enc_r(rs, rt, rd, sa, fn): return (rs<<21)|(rt<<16)|(rd<<11)|(sa<<6)|fn
Z,AT,V0,S2,S3,RA = 0,1,2,18,19,31

def build_cave(k, kx, top, thr, x0, y0):
    def f16(v):            # float32 dengan 16 bit bawah nol, dibulatkan
        b = struct.unpack('<I', struct.pack('<f', v))[0]
        b = (b + 0x8000) & 0xffff0000
        return b
    fk, fkx = f16(k), f16(kx)
    vk  = struct.unpack('<f', struct.pack('<I', fk ))[0]
    vkx = struct.unpack('<f', struct.pack('<I', fkx))[0]
    K, KX = round(vk*256), round(vkx*256)
    assert abs(K/256 - vk) < 1e-9 and abs(KX/256 - vkx) < 1e-9, "k tidak pas 8-bit"
    code = []
    def add(w): code.append(w & 0xffffffff)
    add(enc_i(10, S2, V0, thr))                  # slti  v0,s2,thr
    skip_index = len(code)
    add(0)                                       # bne   v0,zero,skip  (diisi nanti)
    add(0)                                       # nop
    add(enc_i(9, S3, V0, -x0))                   # addiu v0,s3,-x0
    add(enc_i(13, Z, AT, KX))                    # ori   at,zero,KX
    add(enc_r(V0, AT, 0, 0, 0x18))               # mult  v0,at
    add(enc_r(0, 0, V0, 0, 0x12))                # mflo  v0
    add(enc_r(0, V0, V0, 8, 0x03))               # sra   v0,v0,8
    add(enc_i(9, V0, S3, x0))                    # addiu s3,v0,x0
    add(enc_i(9, S2, V0, -y0))                   # addiu v0,s2,-y0
    add(enc_i(13, Z, AT, K))                     # ori   at,zero,K
    add(enc_r(V0, AT, 0, 0, 0x18))               # mult  v0,at
    add(enc_r(0, 0, V0, 0, 0x12))                # mflo  v0
    add(enc_r(0, V0, V0, 8, 0x03))               # sra   v0,v0,8
    add(enc_i(9, V0, S2, top))                   # addiu s2,v0,top
    add(enc_i(15, 0, AT, fk >> 16))              # lui   at,hi(k)
    add((0x11<<26)|(4<<21)|(AT<<16)|(4<<11))     # mtc1  at,f4
    add((0x11<<26)|(16<<21)|(4<<16)|(20<<11)|(20<<6)|2)   # mul.s f20,f20,f4  (skala vertikal)
    add(enc_i(15, 0, AT, fkx >> 16))             # lui   at,hi(kx)
    add((0x11<<26)|(4<<21)|(AT<<16)|(5<<11))     # mtc1  at,f5
    add((0x11<<26)|(16<<21)|(5<<16)|(22<<11)|(22<<6)|2)   # mul.s f22,f22,f5  (skala horizontal)
    skip_target = len(code)
    add(enc_i(9, RA, AT, -0x3a0))                # addiu at,ra,-0x3a0   (= alamat 0x1ad430)
    add(enc_r(AT, 0, 0, 0, 0x08))                # jr    at
    add(0)                                       # nop
    off = skip_target - (skip_index + 1)
    code[skip_index] = enc_i(5, V0, Z, off)      # bne v0,zero,skip
    return code, K, KX, vk, vkx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--k', type=float, default=0.72, help='skala vertikal/umum')
    ap.add_argument('--kx', type=float, default=None, help='skala horizontal (default = k)')
    ap.add_argument('--top', type=int, default=207, help='y baris pertama setelah diciutkan')
    ap.add_argument('--thr', type=int, default=200, help='y >= thr dianggap kotak dialog')
    ap.add_argument('--x0', type=int, default=45)
    ap.add_argument('--y0', type=int, default=218)
    a = ap.parse_args()
    kx = a.kx if a.kx is not None else a.k
    d = bytearray(open(a.inp, 'rb').read())
    if len(d) != 4953616 or d[:4] != b'\x7fELF':
        sys.exit('bukan dump EBOOT terdekripsi PPSSPP (4.953.616 byte, ELF)')
    w = struct.unpack('<I', d[HOOK_Y+BASE:HOOK_Y+BASE+4])[0]
    if w != ORIG_Y and (w >> 16) != 0x24f2:
        sys.exit('instruksi di 0x1ad7b8 tidak dikenal: %08x' % w)
    jal = struct.unpack('<I', d[HOOK_JAL+BASE:HOOK_JAL+BASE+4])[0]
    if jal != 0x0c06b50c:
        sys.exit('jal di 0x1ad7c8 tidak cocok (sudah dipatch?): %08x' % jal)
    cave_old = bytes(d[CAVE+BASE:CAVE+BASE+CAVE_MAX])
    if hashlib.md5(cave_old).hexdigest() != CAVE_ORIG_MD5:
        sys.exit('isi fungsi di 0x1a9980 beda dari yang diharapkan')
    code, K, KX, vk, vkx = build_cave(a.k, kx, a.top, a.thr, a.x0, a.y0)
    assert len(code)*4 <= CAVE_MAX
    d[HOOK_Y+BASE:HOOK_Y+BASE+4] = struct.pack('<I', ORIG_Y)
    d[HOOK_JAL+BASE:HOOK_JAL+BASE+4] = struct.pack('<I', 0x0c000000 | (CAVE >> 2))
    for i, c in enumerate(code):
        d[CAVE+BASE+4*i:CAVE+BASE+4*i+4] = struct.pack('<I', c)
    open(a.out, 'wb').write(d)
    print('OK -> %s | k=%.5f (K=%d) kx=%.5f (KX=%d) top=%d thr=%d anchor=(%d,%d) | kode %d instruksi'
          % (a.out, vk, K, vkx, KX, a.top, a.thr, a.x0, a.y0, len(code)))
if __name__ == '__main__':
    main()
