#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flowchart_tool.py - terjemahan tabel Flowchart (judul scene, deskripsi, nama route, label cabang).

Tabel ini ada di RES.DAT:
  main_resource.dat (GPDA) > flowmap.dat (GPDA) > map.dat (GPDA) > data mentah (~65 KB)
Isi data: record berurutan  [u32 jumlah_karakter][teks UTF-16LE]  dengan byte biner di antaranya.
'＿' (U+FF3F) di deskripsi = pindah baris.

ALAT INI TIDAK MENGUBAH FILE ASLI. Hasil patch ditulis ke file baru.

  python flowchart_tool.py extract RES.DAT flow_strings.csv [--remaining FULL_remaining_wrap_fixed.csv]
  python flowchart_tool.py patch   RES.DAT flow_strings.csv RES_OUT.DAT [--check] [--width 30] [--max-lines 5]

Setelah patch, WAJIB bangun ulang first.dat sebagai pasangan:
  python seekmap_rebuild.py build RES_OUT.DAT ..\\data ekstrak\\first.dat first_new.dat

Kolom CSV: jp, count, kind, english.  Di kolom english boleh pakai '|' sebagai pindah baris
(otomatis jadi '＿'). Apostrof ' otomatis jadi ’, "—" jadi "--", "…" jadi "..." (sama seperti pipeline).
Baris dengan english kosong TIDAK diubah (tetap Jepang).
"""
import sys
import csv
import struct
import argparse

ALIGN = 2048
MARK = "\uFF3F"  # ＿

BUILTIN = {
    "共通ルート": "Common Route",
    "分岐ポイント": "Branch Point",
    "条件分岐": "Conditional Branch",
    "選択肢分岐": "Choice Branch",
    "隣人部会話分岐": "Neighbors Club Chat Branch",
    "マップ終了判定": "Map End Check",
    "成功終了": "Success End",
    "成功終了A": "Success End A",
    "成功終了B": "Success End B",
    "失敗終了": "Failure End",
    "小鳩＆マリアルート": "Kobato & Maria Route",
    "妹バトルロワイヤルルート": "Little Sister Battle Royale Route",
    "夜空＆星奈ルート": "Yozora & Sena Route",
    "夜空ルート": "Yozora Route",
    "星奈ルート": "Sena Route",
    "理科ルート": "Rika Route",
    "小鳩ルート": "Kobato Route",
    "マリアルート": "Maria Route",
    "幸村ルート": "Yukimura Route",
    "天馬ルート": "Tenma Route",
}
BRANCH_SET = {"分岐ポイント", "条件分岐", "選択肢分岐", "隣人部会話分岐", "マップ終了判定"}


def align(x):
    return (x + ALIGN - 1) // ALIGN * ALIGN


# ------------------------------------------------------------------ GPDA
def parse_gpda(b):
    if b[:4] != b"GPDA":
        raise ValueError("bukan GPDA")
    total = struct.unpack_from("<Q", b, 4)[0]
    n = struct.unpack_from("<I", b, 12)[0]
    ents = []
    for i in range(n):
        off, size, noff = struct.unpack_from("<QII", b, 16 + 16 * i)
        ln = struct.unpack_from("<I", b, noff)[0]
        name = b[noff + 4:noff + 4 + ln].decode("utf-8", "replace").strip()
        ents.append((off, size, name))
    return total, ents


def layout(first_off, sizes):
    offs, pos = [], first_off
    for s in sizes:
        offs.append(pos)
        pos = align(pos + s)
    return offs, pos


def check_layout(total, ents, label):
    offs, end = layout(ents[0][0], [e[1] for e in ents])
    if offs != [e[0] for e in ents] or end != total:
        raise SystemExit("[%s] tata letak GPDA tidak sesuai aturan (offset rapat, kelipatan 2048). "
                         "Dibatalkan, tidak ada file ditulis." % label)


def rebuild_level(level_bytes, ents, new_child):
    first_off = ents[0][0]
    hdr = bytearray(level_bytes[:first_off])
    struct.pack_into("<QI", hdr, 16, first_off, len(new_child))
    new_total = align(first_off + len(new_child))
    struct.pack_into("<Q", hdr, 4, new_total)
    out = bytearray(new_total)
    out[:first_off] = hdr
    out[first_off:first_off + len(new_child)] = new_child
    return bytes(out)


def read_top_header(f):
    f.seek(0)
    head32 = f.read(32)
    first_off = struct.unpack_from("<Q", head32, 16)[0]
    f.seek(0)
    head = f.read(first_off)
    total, ents = parse_gpda(head)
    return head, total, ents


def find_main_resource(path):
    with open(path, "rb") as f:
        head, total, ents = read_top_header(f)
        check_layout(total, ents, "RES.DAT tingkat atas")
        idx = [i for i, e in enumerate(ents) if e[2] == "main_resource.dat"]
        if not idx:
            raise SystemExit("main_resource.dat tidak ada di RES.DAT ini.")
        i = idx[0]
        f.seek(ents[i][0])
        data = f.read(ents[i][1])
    return i, data


def descend(a_bytes):
    """Turun lewat entri 0 sampai bukan GPDA. Kembalikan (levels, leaf, path_names)."""
    levels, cur, names = [], a_bytes, ["main_resource.dat"]
    while cur[:4] == b"GPDA":
        total, ents = parse_gpda(cur)
        if len(ents) != 1:
            raise SystemExit("container bersarang punya %d entri (diharapkan 1). Dibatalkan." % len(ents))
        check_layout(total, ents, "/".join(names))
        levels.append((cur, ents))
        off, size, name = ents[0]
        cur = cur[off:off + size]
        names.append(name)
    return levels, cur, names


def rebuild_chain(levels, new_leaf):
    child = new_leaf
    for lb, ents in reversed(levels):
        child = rebuild_level(lb, ents, child)
    return child


def write_top(src, dst, idx, new_entry):
    with open(src, "rb") as f:
        head, total, ents = read_top_header(f)
        sizes = [e[1] for e in ents]
        sizes[idx] = len(new_entry)
        offs, new_total = layout(ents[0][0], sizes)
        hdr = bytearray(head)
        for i in range(len(ents)):
            struct.pack_into("<QI", hdr, 16 + 16 * i, offs[i], sizes[i])
        struct.pack_into("<Q", hdr, 4, new_total)
        with open(dst, "wb") as o:
            o.write(hdr)
            for i, (off, size, name) in enumerate(ents):
                o.write(b"\x00" * (offs[i] - o.tell()))
                if i == idx:
                    o.write(new_entry)
                else:
                    f.seek(off)
                    left = size
                    while left:
                        chunk = f.read(min(left, 8 * 1024 * 1024))
                        if not chunk:
                            raise SystemExit("RES.DAT terpotong")
                        o.write(chunk)
                        left -= len(chunk)
            o.write(b"\x00" * (new_total - o.tell()))
    return total, new_total


# ------------------------------------------------------------------ string records
def ok_char(c):
    return (
        0x20 <= c <= 0x7E
        or 0x00A0 <= c <= 0x00FF
        or 0x2000 <= c <= 0x206F
        or 0x2190 <= c <= 0x25FF
        or 0x2600 <= c <= 0x26FF
        or 0x3000 <= c <= 0x30FF
        or 0x3400 <= c <= 0x4DBF
        or 0x4E00 <= c <= 0x9FFF
        or 0xF900 <= c <= 0xFAFF
        or 0xFF00 <= c <= 0xFFEF
    )


def find_records(buf):
    res, p, end = [], 0, len(buf)
    while p + 6 <= end:
        n = struct.unpack_from("<I", buf, p)[0]
        if 1 <= n <= 400 and p + 4 + 2 * n <= end:
            chars = struct.unpack_from("<%dH" % n, buf, p + 4)
            if all(ok_char(c) for c in chars) and not (n == 1 and chars[0] < 0x3000):
                res.append((p, n, "".join(map(chr, chars))))
                p += 4 + 2 * n
                continue
        p += 1
    return res


def enc(s):
    return struct.pack("<I", len(s)) + s.encode("utf-16-le")


def gaps_of(buf, recs):
    out, prev = [], 0
    for p, n, _ in recs:
        out.append(bytes(buf[prev:p]))
        prev = p + 4 + 2 * n
    out.append(bytes(buf[prev:]))
    return out


def guess_kind(jp):
    if jp == "header":
        return "header"
    if jp in BRANCH_SET:
        return "branch"
    if jp.endswith("ルート") and len(jp) <= 14:
        return "route"
    if MARK in jp or len(jp) >= 26:
        return "desc"
    return "title/label"


def norm_en(s):
    s = s.replace("|", MARK).replace("'", "\u2019").replace("\u2014", "--").replace("\u2026", "...")
    return s.strip()


# ------------------------------------------------------------------ commands
def load_leaf(path):
    idx, a = find_main_resource(path)
    levels, leaf, names = descend(a)
    # uji identitas: membangun ulang dengan isi asli harus sama persis
    if rebuild_chain(levels, leaf) != a:
        raise SystemExit("Uji identitas gagal: membangun ulang container dengan isi asli TIDAK sama persis. "
                         "Dibatalkan (kemungkinan ada padding/format tak terduga).")
    return idx, a, levels, leaf, names


def cmd_extract(a):
    idx, ab, levels, leaf, names = load_leaf(a.res)
    recs = find_records(leaf)
    prefill = {}
    if a.remaining:
        with open(a.remaining, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("kind") or "").strip() == "scene title":
                    en = (r.get("english_text") or "").strip()
                    for k in ("jp_text", "jp_clean"):
                        jp = (r.get(k) or "").strip()
                        if jp and en:
                            prefill.setdefault(jp, en)
    order, cnt = [], {}
    for _, _, t in recs:
        if t not in cnt:
            order.append(t)
            cnt[t] = 0
        cnt[t] += 1
    filled = 0
    with open(a.csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["jp", "count", "kind", "english"])
        for t in order:
            k = guess_kind(t)
            en = BUILTIN.get(t, "")
            if not en and k == "title/label":
                en = prefill.get(t, "")
            if en:
                filled += 1
            w.writerow([t, cnt[t], k, en])
    gap_bytes = sum(len(g) for g in gaps_of(leaf, recs))
    kinds = {}
    for t in order:
        kinds[guess_kind(t)] = kinds.get(guess_kind(t), 0) + 1
    print("Jalur container : " + " > ".join(names))
    print("Ukuran data     : %d byte" % len(leaf))
    print("Record string   : %d (unik %d), byte biner di antaranya: %d" % (len(recs), len(order), gap_bytes))
    print("Jenis (unik)    : %s" % kinds)
    print("Terisi otomatis : %d dari %d" % (filled, len(order)))
    print("Ditulis         : %s" % a.csv)


def cmd_patch(a):
    idx, ab, levels, leaf, names = load_leaf(a.res)
    mapping, warn = {}, []
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            jp = (r.get("jp") or "").strip("\r\n")
            en = norm_en(r.get("english") or "")
            if jp and en:
                mapping[jp] = en
                kind = (r.get("kind") or "").strip()
                if kind == "desc":
                    lines = en.split(MARK)
                    if max(len(x) for x in lines) > a.width or len(lines) > a.max_lines:
                        warn.append("desc  %2d baris, terpanjang %2d: %s" % (len(lines), max(len(x) for x in lines), en[:50]))
                elif kind in ("title/label", "route", "branch") and len(en) > a.title_max:
                    warn.append("label %2d huruf: %s" % (len(en), en))
    recs = find_records(leaf)
    out, prev, changed = bytearray(), 0, 0
    for p, n, t in recs:
        out += leaf[prev:p]
        if t in mapping:
            out += enc(mapping[t])
            changed += 1
        else:
            out += leaf[p:p + 4 + 2 * n]
        prev = p + 4 + 2 * n
    out += leaf[prev:]
    new_leaf = bytes(out)
    # verifikasi: byte biner antar-record harus identik, jumlah record sama
    nrecs = find_records(new_leaf)
    if len(nrecs) != len(recs) or gaps_of(new_leaf, nrecs) != gaps_of(leaf, recs):
        raise SystemExit("Verifikasi gagal: struktur biner berubah. Dibatalkan, tidak ada file ditulis.")
    untouched = sum(1 for _, _, t in recs if t not in mapping)
    print("Record diganti  : %d   masih Jepang: %d" % (changed, untouched))
    print("Data tabel      : %d -> %d byte" % (len(leaf), len(new_leaf)))
    if warn:
        print("PERINGATAN panjang (%d), mungkin terpotong di layar:" % len(warn))
        for w in warn[:25]:
            print("   " + w)
        if len(warn) > 25:
            print("   ... +%d lagi" % (len(warn) - 25))
    if a.check:
        print("Mode --check: tidak ada file ditulis.")
        return
    new_a = rebuild_chain(levels, new_leaf)
    old_total, new_total = write_top(a.res, a.out, idx, new_a)
    print("main_resource   : %d -> %d byte" % (len(ab), len(new_a)))
    print("RES.DAT         : %d -> %d byte" % (old_total, new_total))
    print("Ditulis         : %s" % a.out)
    print("LANGKAH WAJIB   : python seekmap_rebuild.py build %s <first.dat asli> first_new.dat" % a.out)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Alat terjemahan tabel Flowchart")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("res")
    e.add_argument("csv")
    e.add_argument("--remaining", help="FULL_remaining_wrap_fixed.csv (untuk mengisi judul scene otomatis)")
    e.set_defaults(fn=cmd_extract)
    p = sub.add_parser("patch")
    p.add_argument("res")
    p.add_argument("csv")
    p.add_argument("out", nargs="?")
    p.add_argument("--check", action="store_true")
    p.add_argument("--width", type=int, default=30, help="peringatan bila satu baris deskripsi lebih dari N huruf")
    p.add_argument("--max-lines", type=int, default=5)
    p.add_argument("--title-max", type=int, default=26)
    p.set_defaults(fn=cmd_patch)
    a = ap.parse_args()
    if a.cmd == "patch" and not a.check and not a.out:
        ap.error("patch butuh nama file keluaran (atau pakai --check)")
    a.fn(a)


if __name__ == "__main__":
    main()
