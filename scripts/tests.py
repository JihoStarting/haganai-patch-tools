"""
tests.py -- tes keamanan pipeline.
(gabungan test_identity_rebuild.py + test_real.py + fix_inst_sizes.py + test_seekmap.py)
Taruh satu folder dengan pipeline.py dan seekmap_rebuild.py.

  python tests.py identity <RES.DAT>
      Rebuild semua level GPDA TANPA perubahan harus byte-identical dengan aslinya.
      Kalau gagal, jangan lanjut patch teks -- perbaiki GPDAContainer di pipeline.py dulu.

  python tests.py crosscheck <file.obj>
      Bandingkan pipeline.patch_objbin_bytes dengan implementasi referensi
      fix_instruction_sizes (ada di file ini) pada 20 seed acak. Ambil .obj dari:
      python dump.py obj RES.DAT 0011ess0 0011ess0.obj

  python tests.py seekmap [first.dat]
      Tes seekmap_rebuild.py pada RES sintetis (check, build, CRC independen, topologi beda).
      first.dat opsional; kalau tidak diberi, dipakai first.dat sintetis.
"""
import gzip
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))


# =============================================================== identity
def _check_recursive(data: bytes, label: str, depth: int = 0):
    from pipeline import GPDAContainer
    indent = "  " * depth
    try:
        c = GPDAContainer.parse(data)
    except Exception as e:
        print(f"{indent}{label}: bukan GPDA container ({e}) -- skip")
        return True

    rebuilt = c.rebuild({})
    ok = rebuilt == data
    status = "OK" if ok else "MISMATCH!!"
    print(f"{indent}{label}: count={c.count}, size={len(data)} -> {len(rebuilt)}  [{status}]")

    all_ok = ok
    if not ok:
        print(f"{indent}  -> berhenti di level ini, perbaiki GPDAContainer di pipeline.py dulu sebelum lanjut")
        return False

    if depth < 3:  # batasi kedalaman biar ga kelamaan
        for i in range(c.count):
            entry_data = c.entry_bytes(i)
            if entry_data[:4] == b"GPDA":
                sub_ok = _check_recursive(entry_data, f"{label} > entry[{i}] ({c.names[i]})", depth + 1)
                all_ok = all_ok and sub_ok
    return all_ok


def cmd_identity(path):
    data = Path(path).read_bytes()
    print("Testing identity rebuild, semua level GPDA nested...\n")
    ok = _check_recursive(data, "resource.dat")
    print()
    if ok:
        print("✅ SEMUA level rebuild identik 100% ke file asli. GPDAContainer (pipeline.py) aman dipakai.")
    else:
        print("❌ Ada level yang MISMATCH. JANGAN lanjut ke patch teks dulu.")
    return ok


# =============================================================== referensi fix_inst_sizes
# (hanya dipakai crosscheck; pipeline.py memperbaiki ukuran per instruksi sendiri)
OP_DIALOG = 100
ALIGN = 16
MIN_TRAIL = 5   # nol minimal sesudah byte teks terakhir (hasil analisis data asli)


def walk(d: bytes):
    pos = struct.unpack_from("<I", d, 4)[0]
    out = []
    while pos < len(d):
        size = struct.unpack_from("<I", d, pos)[0]
        op = struct.unpack_from("<H", d, pos + 4)[0]
        if size < 8 or pos + size > len(d):
            raise ValueError(f"instruksi rusak di {pos:#x} (size={size})")
        out.append((pos, size, op))
        pos += size
    return out


def fix_instruction_sizes(orig: bytes, patched: bytes) -> bytes:
    """Update prefix ukuran u32 tiap instruksi dialog + pad ke kelipatan 16 (implementasi referensi)."""
    oi = walk(orig)
    first = struct.unpack_from("<I", patched, 4)[0]
    out = bytearray(patched[:first])
    pos = first
    for opos, osz, op in oi:
        if op != OP_DIALOG:
            out += patched[pos:pos + osz]
            pos += osz
            continue
        # length field dialog ada di opcode_pos + 11 (marker 0x64 di +4, field di marker+7)
        lo = struct.unpack_from("<H", orig, opos + 11)[0]
        lp = struct.unpack_from("<H", patched, pos + 11)[0]
        raw_len = osz + 2 * (lp - lo)       # panjang instruksi ini di file patched
        if lp == lo:                        # tidak berubah -> salin apa adanya
            out += patched[pos:pos + raw_len]
            pos += raw_len
            continue
        # c = jumlah byte sampai byte non-nol terakhir (= akhir teks). Di file asli, sesudah
        # teks selalu ada minimal 5 byte nol (terminator + trailer), lalu pad ke kelipatan 16:
        #   ukuran = ceil16(c + 5)   (terverifikasi di semua 62 dialog _0011ess0)
        c_old = osz - (len(orig[opos:opos + osz]) - len(orig[opos:opos + osz].rstrip(b"\x00")))
        c_new = c_old + 2 * (lp - lo)
        assert not any(patched[pos + c_new:pos + raw_len]), "ada data non-nol di ekor instruksi"
        newsz = (c_new + MIN_TRAIL + ALIGN - 1) // ALIGN * ALIGN
        core = bytearray(patched[pos:pos + c_new] + b"\x00" * (newsz - c_new))
        struct.pack_into("<I", core, 0, newsz)
        out += core
        pos += raw_len
    out += patched[pos:]
    return bytes(out)


def verify_fixed(orig: bytes, fixed: bytes):
    oi, fi = walk(orig), walk(fixed)
    assert len(oi) == len(fi), "jumlah instruksi beda"
    assert [x[2] for x in oi] == [x[2] for x in fi], "urutan opcode beda"
    assert all(x[0] % ALIGN == 0 and x[1] % ALIGN == 0 for x in fi), "tidak rata 16"
    assert fi[-1][0] + fi[-1][1] == len(fixed), "walk tidak berakhir di akhir file"
    assert struct.unpack_from("<I", fixed, 0)[0] == len(fi), "header[0] != jumlah instruksi"


# =============================================================== crosscheck
def cmd_crosscheck(obj_path):
    import pipeline as fp
    d = Path(obj_path).read_bytes()
    c, f, insts = fp.parse_instructions(d)
    LB = "「".encode("utf-16-le")

    def locate(inst):
        lf = struct.unpack_from("<H", inst, 11)[0]
        for w in range(0, fp.MAX_SANE_SPEAKER_FIELD + 1, 2):
            t = 15 + w
            if inst[t:t + 2] != LB:
                continue
            try:
                txt, end = fp.decode_utf16le_until_null(inst, t)
            except ValueError:
                continue
            if txt.endswith("」") and len(txt) + w // 2 == lf:
                return t, w, txt, end

    info = {i: locate(d[p:p + s]) for i, (p, s, o) in enumerate(insts) if o == 100}
    info = {i: r for i, r in info.items() if r}
    print("dialog berbracket:", len(info))
    ok = True
    for seed in range(1, 21):
        random.seed(seed)
        rows = []
        naive = bytearray(d[:f])
        for i, (p, s, o) in enumerate(insts):
            inst = d[p:p + s]
            if i in info and random.random() < 0.8:
                t, w, txt, end = info[i]
                eng = ("Lorem ipsum dolor sit amet. " * random.choice([0, 1, 2, 5, 9])) + "x" * random.randint(1, 9)
                rows.append({"offset": hex(p + t), "english_text": eng})
                nt = f"「{eng}」"
                naive += (bytearray(inst[:11]) + struct.pack("<H", len(nt) + w // 2) + b"\0\0"
                          + inst[15:t] + nt.encode("utf-16-le") + b"\0\0" + inst[end:])
            else:
                naive += inst
        theirs = fix_instruction_sizes(d, bytes(naive))
        verify_fixed(d, theirs)
        mine, n, sk = fp.patch_objbin_bytes(d, rows)
        same = (mine == theirs and n == len(rows) and not sk)
        ok &= same
        if not same:
            print("seed", seed, "BEDA", n, len(rows), sk[:2], len(mine), len(theirs))
    print("SEMUA IDENTIK dengan implementasi referensi" if ok else "ADA PERBEDAAN")
    return ok


# =============================================================== seekmap
def _align(n, a=2048):
    return (n + a - 1) // a * a


def _crc_slow(data):
    c = 0xFFFFFFFF
    for b in data:
        c ^= b << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
    return c


def _build(name, node, depth):
    """node = bytes (leaf) atau list[(name,node)] (container). Balikin (bytes, recs).
    recs = [(depth,name,rel_off,size,cc|None)] preorder, rel_off relatif ke awal bytes ini."""
    if isinstance(node, bytes):
        return node, [(depth, name, 0, len(node), None)]
    cnt = len(node)
    pool = b""
    noffs = []
    base = 16 + 16 * cnt
    for nm, _ in node:
        noffs.append(base + len(pool))
        pool += struct.pack("<I", len(nm)) + nm
    cursor = _align(base + len(pool))
    toc = []
    subrecs = []
    parts = []
    for (nm, ch), noff in zip(node, noffs):
        data, rs = _build(nm, ch, depth + 1)
        if not isinstance(ch, bytes):
            data = data + b"\0" * (_align(len(data)) - len(data))
        size = len(data)
        off = cursor
        parts.append((off, data))
        toc.append((off, 0, size, noff))
        subrecs += [(d, n, o + off, s, c) for d, n, o, s, c in rs]
        cursor = _align(off + size)
    total = cursor
    out = bytearray(total)
    out[0:16] = struct.pack("<4sIII", b"GPDA", total, 0, cnt)
    for i, t in enumerate(toc):
        out[16 + 16 * i:32 + 16 * i] = struct.pack("<IIII", *t)
    out[base:base + len(pool)] = pool
    for off, data in parts:
        out[off:off + len(data)] = data
    return bytes(out), [(depth, name, 0, total, cnt)] + subrecs


def _expected_text(buf, recs):
    out = b""
    for d, nm, off, size, cc in recs:
        line = b"\t" * d + nm + b" %d %d %d" % (off, size, _crc_slow(buf[off:off + size]))
        if cc is not None:
            line += b" 0 %d" % cc
        out += line + b" \r\n"
    return out


def _rb(n):
    return bytes(random.getrandbits(8) for _ in range(n))


def _tree(extra=0):
    return [(b"dummy.dat", _rb(3000)),
            (b"image_bg.dat ", [(b"BG01A.gim", _rb(5000)), (b"BG01B.gim", _rb(2100))]),
            (b"script.dat ", [(b"_0001.dat ", [(b"_0001.dat ", [(b"_0001.obj.gz", _rb(1500 + extra)),
                                                               (b"x.bin", _rb(70))]),
                                               (b"b.bin", _rb(3333))]),
                              (b"_0002.dat ", [(b"n.bin", _rb(10))])]),
            (b"tail.dat", _rb(123))]


def cmd_seekmap(first_path=None):
    import seekmap_rebuild as S
    random.seed(3)
    tmp = Path(tempfile.mkdtemp())
    t1 = _tree()
    res1, recs1 = _build(b"resource.dat", t1, 0)
    (tmp / "RES.DAT").write_bytes(res1)
    txt1 = _expected_text(res1, recs1)
    if first_path:
        real_first = Path(first_path).read_bytes()
    else:
        print("first.dat tidak diberikan -> pakai first.dat sintetis")
        real_first = _build(b"first.dat", [(b"seekmap.dat", S.make_gz(b"placeholder\r\n")), (b"other.bin", _rb(300))], 0)[0]
    first_synth = S.write_seekmap_into_first(real_first, txt1)
    (tmp / "first.dat").write_bytes(first_synth)
    print("RES sintetis", len(res1), "byte,", len(recs1), "baris")

    def run(*a):
        p = subprocess.run([sys.executable, str(HERE / "seekmap_rebuild.py"), *a], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    rc, o = run("check", str(tmp / "RES.DAT"), str(tmp / "first.dat"))
    print("[check original] rc", rc, "|", [l for l in o.splitlines() if "HASIL" in l or "field4" in l])
    assert rc == 0

    # RES v2: satu file dalam membesar (menggeser entri sesudahnya)
    t2 = _tree(extra=2500)
    res2, recs2 = _build(b"resource.dat", t2, 0)
    (tmp / "RES2.DAT").write_bytes(res2)
    rc, o = run("build", str(tmp / "RES2.DAT"), str(tmp / "first.dat"), str(tmp / "first_new.dat"))
    print("[build] rc", rc)
    print("\n".join(l for l in o.splitlines() if "berubah" in l or "HASIL" in l or "seekmap" in l))
    assert rc == 0
    new_raw = S.extract_seekmap((tmp / "first_new.dat").read_bytes())
    same = new_raw == _expected_text(res2, recs2)
    print("seekmap baru == perhitungan independen (CRC bitwise):", same)
    assert same

    # first.dat: hanya slot seekmap yang berubah
    a = real_first
    b = (tmp / "first_new.dat").read_bytes()
    f4, ents = S.first_dat_toc(a)
    i, rel, sz, nm = [e for e in ents if e[3] == "seekmap.dat"][0]
    nxt = min([r for _, r, _, _ in ents if r > rel] + [f4])
    diff = [k for k in range(len(a)) if a[k] != b[k]]
    print("len sama:", len(a) == len(b), "| byte beda di luar TOC-size & slot seekmap:",
          sum(1 for k in diff if not (rel <= k < nxt) and not (16 + 16 * i + 8 <= k < 16 + 16 * i + 12)))

    # negatif: topologi beda -> harus gagal dengan pesan jelas
    t3 = _tree()
    t3[2] = (b"script.dat ", t3[2][1][:1])
    res3, _ = _build(b"resource.dat", t3, 0)
    (tmp / "RES3.DAT").write_bytes(res3)
    rc, o = run("build", str(tmp / "RES3.DAT"), str(tmp / "first.dat"), str(tmp / "x.dat"))
    print("[topologi beda] rc", rc, "|", o.strip().splitlines()[-1][:110])
    assert rc != 0
    print("SEMUA TES LOLOS")


def main(a):
    if a[:1] == ["identity"] and len(a) == 2:
        sys.exit(0 if cmd_identity(a[1]) else 1)
    elif a[:1] == ["crosscheck"] and len(a) == 2:
        sys.exit(0 if cmd_crosscheck(a[1]) else 1)
    elif a[:1] == ["seekmap"] and len(a) in (1, 2):
        cmd_seekmap(*a[1:])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
