"""
seekmap_rebuild.py
==================
Bangun ulang seekmap.dat (dan first.dat yang membungkusnya) dari RES.DAT hasil patch.

Format seekmap.dat (teks, CRLF, indentasi tab = kedalaman pohon):
    <tab*depth><nama><spasi> <offset> <size> <checksum>                  <- file biasa
    <tab*depth><nama><spasi> <offset> <size> <checksum> 0 <jumlah_anak>  <- container GPDA
  offset = offset ABSOLUT di RES.DAT, checksum = CRC-32/MPEG-2 atas data[offset:offset+size].

Pohon di seekmap diikuti berurutan bersamaan dengan pohon GPDA di RES.DAT
(urutan TOC = urutan baris). Nama dan jumlah anak dicocokkan; kalau topologi
beda, script berhenti dengan pesan error (tidak menebak).

Pemakaian:
    python seekmap_rebuild.py check RES.DAT first.dat
        Self-check: hitung ulang semua checksum dari RES.DAT dan bandingkan dengan
        seekmap di first.dat. Jalankan ini DULU pada RES.DAT + first.dat ORIGINAL;
        harus 0 mismatch (membuktikan script ini benar sebelum dipakai ke file patched).

    python seekmap_rebuild.py build RES_patched.DAT first.dat first_new.dat
        Hitung ulang, tulis seekmap baru ke first_new.dat, lalu verifikasi ulang
        first_new.dat terhadap RES_patched.DAT.

Butuh RAM sekitar 2x ukuran RES.DAT (~800 MB).
"""
import gzip
import re
import struct
import sys
import time
import zlib
from pathlib import Path

REV = bytes(int(f"{i:08b}"[::-1], 2) for i in range(256))
LINE_RX = re.compile(rb'^(\t*)(.*? +)(\d+) (\d+) (\d+)(?: (\d+) (\d+))? $')


def rev32(x):
    return int(f"{x:032b}"[::-1], 2)


def crc_mpeg2(rev_buf, start, size):
    """CRC-32/MPEG-2 (poly 04C11DB7, init FFFFFFFF, tanpa refleksi/xorout) atas
    data asli. rev_buf = data yang tiap byte-nya sudah di-bit-reverse; memakai
    zlib.crc32 (C, cepat) lewat kesetaraan refleksi."""
    return rev32(zlib.crc32(memoryview(rev_buf)[start:start + size]) ^ 0xFFFFFFFF)


# ----------------------------------------------------------------------------
# seekmap.dat (teks)
# ----------------------------------------------------------------------------

class Rec:
    __slots__ = ("depth", "prefix", "off", "size", "crc", "z", "cc")


def parse_seekmap(raw: bytes):
    lines = raw.split(b"\r\n")
    if lines[-1] != b"":
        raise ValueError("seekmap tidak diakhiri CRLF")
    recs = []
    for n, ln in enumerate(lines[:-1]):
        m = LINE_RX.match(ln)
        if not m:
            raise ValueError(f"baris {n} seekmap tidak dikenali: {ln[:80]!r}")
        r = Rec()
        tabs, name, off, size, crc, z, cc = m.groups()
        r.depth = len(tabs)
        r.prefix = tabs + name
        r.off, r.size, r.crc = int(off), int(size), int(crc)
        r.z, r.cc = z, cc
        recs.append(r)
    return recs


def rec_name(r):
    return r.prefix.strip(b"\t ")


def emit_seekmap(recs, values):
    out = bytearray()
    for r, (off, size, crc) in zip(recs, values):
        out += r.prefix + b"%d %d %d" % (off, size, crc)
        if r.cc is not None:
            out += b" " + r.z + b" " + r.cc
        out += b" \r\n"
    return bytes(out)


def make_gz(raw: bytes) -> bytes:
    # header disamakan dengan seekmap.dat.gz original: mtime=0, XFL=2, OS=0x0B
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    body = co.compress(raw) + co.flush()
    return (bytes([0x1F, 0x8B, 8, 0, 0, 0, 0, 0, 2, 0x0B]) + body
            + struct.pack("<II", zlib.crc32(raw) & 0xFFFFFFFF, len(raw) & 0xFFFFFFFF))


# ----------------------------------------------------------------------------
# GPDA
# ----------------------------------------------------------------------------

def parse_gpda(buf, base):
    magic, f4, z, cnt = struct.unpack_from("<4sIII", buf, base)
    if magic != b"GPDA":
        raise ValueError(f"bukan GPDA di offset {base}")
    ents = []
    for i in range(cnt):
        rel, _zero, size, noff = struct.unpack_from("<IIII", buf, base + 16 + 16 * i)
        nlen = struct.unpack_from("<I", buf, base + noff)[0]
        name = bytes(buf[base + noff + 4: base + noff + 4 + nlen])
        ents.append((rel, size, name))
    return f4, cnt, ents


def walk_tree(buf, rev, recs, progress=True):
    """Ikuti pohon GPDA di buf berpasangan dengan recs. Balikin (values, f4_mismatch)."""
    values = [None] * len(recs)
    f4_mismatch = []
    pos = [0]
    t0 = time.time()

    def visit(abs_off, size, name, depth):
        i = pos[0]
        pos[0] += 1
        if i >= len(recs):
            raise ValueError("pohon RES.DAT punya lebih banyak entri daripada seekmap")
        r = recs[i]
        if r.depth != depth or (name is not None and rec_name(r) != name.strip(b"\t ")):
            raise ValueError(f"topologi beda di baris {i}: seekmap="
                             f"{r.depth}/{rec_name(r)!r}, RES.DAT={depth}/{name!r}")
        values[i] = (abs_off, size, crc_mpeg2(rev, abs_off, size))
        if progress and i % 2000 == 0:
            print(f"      ... {i}/{len(recs)} entri, {time.time()-t0:.1f}s")
        if r.cc is not None:
            f4, cnt, ents = parse_gpda(buf, abs_off)
            if cnt != int(r.cc):
                raise ValueError(f"jumlah anak beda di baris {i} ({rec_name(r)!r}): "
                                 f"seekmap={r.cc!r}, GPDA={cnt}")
            if f4 != size:
                f4_mismatch.append((i, rec_name(r), f4, size))
            for rel, sz, nm in ents:
                visit(abs_off + rel, sz, nm, depth + 1)

    visit(0, len(buf), None, 0)
    if pos[0] != len(recs):
        raise ValueError(f"seekmap punya {len(recs)} baris tapi pohon RES.DAT cuma {pos[0]} entri")
    return values, f4_mismatch


# ----------------------------------------------------------------------------
# first.dat
# ----------------------------------------------------------------------------

def first_dat_toc(first: bytes):
    magic, f4, z, cnt = struct.unpack_from("<4sIII", first, 0)
    if magic != b"GPDA":
        raise ValueError("first.dat bukan GPDA")
    ents = []
    for i in range(cnt):
        rel, _zero, size, noff = struct.unpack_from("<IIII", first, 16 + 16 * i)
        nlen = struct.unpack_from("<I", first, noff)[0]
        name = first[noff + 4: noff + 4 + nlen].decode("ascii", "replace").strip()
        ents.append((i, rel, size, name))
    return f4, ents


def extract_seekmap(first: bytes):
    f4, ents = first_dat_toc(first)
    for i, rel, size, name in ents:
        if name == "seekmap.dat":
            return gzip.decompress(first[rel:rel + size])
    raise ValueError("entri seekmap.dat tidak ada di first.dat")


def write_seekmap_into_first(first: bytes, new_raw: bytes) -> bytes:
    f4, ents = first_dat_toc(first)
    idx, rel, old_size = next((i, r, s) for i, r, s, n in ents if n == "seekmap.dat")
    slot_end = min([r for _, r, _, _ in ents if r > rel] + [f4])
    gz = make_gz(new_raw)
    if len(gz) > slot_end - rel:
        raise ValueError(f"seekmap baru ({len(gz)} byte) tidak muat di slot lama "
                         f"({slot_end - rel} byte); perlu relayout first.dat")
    out = bytearray(first)
    out[rel:slot_end] = gz + b"\x00" * (slot_end - rel - len(gz))
    struct.pack_into("<I", out, 16 + 16 * idx + 8, len(gz))
    print(f"      seekmap.dat.gz: {old_size} -> {len(gz)} byte (slot {slot_end - rel} byte)")
    return bytes(out)


# ----------------------------------------------------------------------------
# perintah
# ----------------------------------------------------------------------------

def load_res(path):
    print(f"Membaca {path} ...")
    buf = Path(path).read_bytes()
    print(f"  {len(buf)} byte; menyiapkan buffer bit-reverse ...")
    return buf, buf.translate(REV)


def compare(recs, values):
    bad = [(i, recs[i], values[i]) for i in range(len(recs))
           if (recs[i].off, recs[i].size, recs[i].crc) != values[i]]
    return bad


def cmd_check(res_path, first_path):
    first = Path(first_path).read_bytes()
    recs = parse_seekmap(extract_seekmap(first))
    print(f"seekmap: {len(recs)} baris, {sum(r.cc is not None for r in recs)} container")
    buf, rev = load_res(res_path)
    values, f4_bad = walk_tree(buf, rev, recs)
    bad = compare(recs, values)
    print(f"\nHASIL: {len(recs)-len(bad)}/{len(recs)} baris cocok, {len(bad)} mismatch")
    for i, r, v in bad[:15]:
        print(f"  baris {i} {rec_name(r)!r}: seekmap=({r.off},{r.size},{r.crc}) hitung={v}")
    print(f"Header GPDA field4 != size pada {len(f4_bad)} container")
    for i, nm, f4, sz in f4_bad[:10]:
        print(f"  baris {i} {nm!r}: field4={f4} size={sz}")
    return len(bad) == 0


def cmd_build(res_path, first_path, out_path):
    first = Path(first_path).read_bytes()
    recs = parse_seekmap(extract_seekmap(first))
    buf, rev = load_res(res_path)
    print("Menghitung ulang offset/size/checksum ...")
    values, f4_bad = walk_tree(buf, rev, recs)
    changed = len(compare(recs, values))
    print(f"  {changed} dari {len(recs)} baris berubah")
    if f4_bad:
        print(f"  PERINGATAN: header GPDA field4 != size pada {len(f4_bad)} container "
              f"(contoh: {f4_bad[:3]})")

    new_raw = emit_seekmap(recs, values)
    print(f"  seekmap teks: {len(new_raw)} byte")
    new_first = write_seekmap_into_first(first, new_raw)
    Path(out_path).write_bytes(new_first)
    print(f"Ditulis: {out_path} ({len(new_first)} byte; first.dat asli {len(first)} byte)")

    print("\nVerifikasi ulang dari file yang baru ditulis ...")
    recs2 = parse_seekmap(extract_seekmap(Path(out_path).read_bytes()))
    values2, _ = walk_tree(buf, rev, recs2, progress=False)
    bad = compare(recs2, values2)
    print(f"HASIL VERIFIKASI: {len(recs2)-len(bad)}/{len(recs2)} baris cocok, {len(bad)} mismatch")
    return len(bad) == 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "check":
        sys.exit(0 if cmd_check(a[1], a[2]) else 1)
    elif len(a) == 4 and a[0] == "build":
        sys.exit(0 if cmd_build(a[1], a[2], a[3]) else 1)
    else:
        print(__doc__)
        sys.exit(1)
