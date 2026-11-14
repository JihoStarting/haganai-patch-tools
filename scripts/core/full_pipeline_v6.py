"""
full_pipeline_v6.py  --  berdasarkan full_pipeline_v5.py (by: KangJiho)
Perubahan dari v5 (berdasarkan hasil ruler test di PPSSPP):
  * Lebar kolom dihitung dalam SETENGAH kolom: ASCII = 1 kolom, U+2019 (') = --apos-w (default 1.5), karakter
    non-ASCII lain = 2 kolom.
  * Lebar wrap DIPISAH:
      --width  N : dialog dengan nama pembicara (CSV dialog)  default 37  (39 kolom - 2 kolom indent untuk tanda kurung)
      --nwidth N : narasi tanpa pembicara (CSV remaining, kind narration/dialog)  default 39
    --width 0 mematikan wrap untuk keduanya (kecuali --nwidth diisi eksplisit).
  * Teks yang butuh lebih dari --max-lines baris (default 3) dicatat di --overflow (default overflow.csv).
  * choice/menu TIDAK di-wrap (engine tidak melipat choice; batas aman di layar sekitar 41 karakter).

Taruh satu folder dengan full_pipeline.py, full_pipeline_v3.py, gpda_v2.py, choice_patch.py.

Usage:
    python full_pipeline_v6.py --verify-only <RES.DAT> <dialogue.csv> <remaining.csv> [opsi]
    python full_pipeline_v6.py <RES.DAT> <dialogue.csv> <remaining.csv> <output.DAT> [opsi]
Opsi:
    --width N  --nwidth N  --apos X  --apos-w F  --max-lines N  --overflow file.csv  --report skip.csv
    --apos "'"   pakai apostrof ASCII biasa (lebar 1 kolom) -- kalau glyph-nya tampil benar di game,
                 ini menghilangkan semua ketidakpastian lebar apostrof.
Setelah ini tetap wajib rebuild seekmap/first.dat (seekmap_rebuild.py build ...).
"""
import csv, gzip, sys, time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import full_pipeline_v3 as v3  # noqa: E402
from full_pipeline import parse_instructions, verify_objbin, _is_aligned  # noqa: E402
from gpda_v2 import GPDAContainer  # noqa: E402
from choice_patch import rewrite_choice_instruction  # noqa: E402


def clean_en(s, apos):
    return (s or "").replace("\r\n", " ").replace("\n", " ").replace("'", apos).strip()


DEFAULT_WIDTH = 37    # dialog dengan pembicara: 39 kolom - indent 2 untuk tanda kurung
DEFAULT_NWIDTH = 39   # narasi tanpa pembicara (hasil ruler: 39 karakter ASCII per baris)
MAX_LINES = 3
APOS_W = 1.5          # lebar kolom U+2019 (terukur ~1.5 dari ruler test)
OTHER_W = 2.0         # lebar kolom karakter non-ASCII lain (perkiraan)
OVERFLOW_PATH = "overflow.csv"
OVERFLOW = []         # (sumber, kunci, jumlah_baris, teks)


def cw(s):
    """Lebar dalam SETENGAH kolom (ASCII = 2 unit)."""
    t = 0
    for c in s:
        if ord(c) < 128:
            t += 2
        elif c == "\u2019":
            t += int(round(APOS_W * 2))
        else:
            t += int(round(OTHER_W * 2))
    return t


def wrap_lines(s, W):
    """Pecah per kata; W dalam kolom (dibandingkan dalam setengah kolom). Balikin list baris."""
    lim, lines, cur = int(W * 2), [], ""
    for w in s.split():
        while cw(w) > lim:                      # kata lebih panjang dari satu baris: potong
            if cur:
                lines.append(cur); cur = ""
            k, acc = 0, 0
            while k < len(w) and acc + cw(w[k]) <= lim:
                acc += cw(w[k]); k += 1
            lines.append(w[:k]); w = w[k:]
        if not cur:
            cur = w
        elif cw(cur) + 2 + cw(w) <= lim:        # +2 = satu spasi (1 kolom)
            cur += " " + w
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def wrap_pad(s, W):
    """Isi tiap baris (kecuali terakhir) dengan spasi sampai W kolom (sisa setengah kolom dibuang).
    W harus sama dengan kapasitas asli kotak; W<=0 -> tidak di-wrap."""
    if not W or W <= 0:
        return s
    lines = wrap_lines(s, W)
    if not lines:
        return ""
    lim = int(W * 2)
    return "".join(l + " " * ((lim - cw(l)) // 2) for l in lines[:-1]) + lines[-1]


def note_overflow(src, key, text, W):
    if W and W > 0:
        n = len(wrap_lines(text, W))
        if n > MAX_LINES:
            OVERFLOW.append((src, key, n, text))


def patch_choices(orig, cur, groups):
    """cur = bytes setelah patch dialog/narasi; groups = {inst_index: [rows urut str_index]}."""
    skipped = []

    def skip_all(reason):
        return cur, 0, [(f"inst#{i}", reason) for i in groups]

    try:
        _, first, insts = parse_instructions(cur)
        if not _is_aligned(insts):
            raise ValueError("instruksi tidak 16-aligned")
    except ValueError as e:
        return skip_all(f"struktur instruksi tidak valid: {e}")
    new = {}
    for idx, rows in groups.items():
        label = f"inst#{idx}"
        if not (0 <= idx < len(insts)):
            skipped.append((label, f"inst_index di luar jumlah instruksi ({len(insts)})")); continue
        pos, size, op = insts[idx]
        if op != 103:
            skipped.append((label, f"instruksi bukan choice (opcode {op})")); continue
        if [int(r["str_index"]) for r in rows] != list(range(len(rows))):
            skipped.append((label, "str_index tidak berurutan 0..n-1")); continue
        ni, reason = rewrite_choice_instruction(
            cur[pos:pos + size], [r["jp_text"] for r in rows], [r["english_text"] for r in rows])
        if ni is None:
            skipped.append((label, reason)); continue
        new[idx] = ni
    if not new:
        return cur, 0, skipped
    out = bytearray(cur[:first])
    for i, (pos, size, _) in enumerate(insts):
        out += new.get(i, cur[pos:pos + size])
    out = bytes(out)
    try:
        verify_objbin(orig, out)
    except ValueError as e:
        return skip_all(f"verify_objbin gagal, choice file ini TIDAK dipatch: {e}")
    return out, len(new), skipped


def patch_one_script_entry(mid_bytes, d_rows, n_rows, c_groups):
    if not d_rows and not n_rows and not c_groups:
        return None, 0, []
    mid = GPDAContainer.parse(mid_bytes)
    inner = GPDAContainer.parse(mid.entry_bytes(0))
    gz_idx = next((j for j, nm in enumerate(inner.names) if ".obj.gz" in nm), None)
    if gz_idx is None:
        return None, 0, [("-", "tidak ketemu entri .obj.gz di dalam container")]
    orig = gzip.decompress(inner.entry_bytes(gz_idx))
    cur, n, skipped = v3.patch_objbin_combined(orig, d_rows, n_rows)
    if c_groups:
        cur, nc, sk2 = patch_choices(orig, cur, c_groups)
        n += nc
        skipped = skipped + sk2
    if n == 0:
        return None, 0, skipped
    new_gz = gzip.compress(cur, compresslevel=9, mtime=0)
    new_inner = inner.rebuild({gz_idx: new_gz})
    return mid.rebuild({0: new_inner}), n, skipped


def run(resource_path, dialog_csv, narr_csv, out_path, apos, report_path=None, verify_only=False,
        width=DEFAULT_WIDTH, nwidth=DEFAULT_NWIDTH):
    t0 = time.time()
    print(f"[1/5] Membaca {resource_path} ...")
    res_data = Path(resource_path).read_bytes()
    res = GPDAContainer.parse(res_data)
    script_idx = next((i for i, nm in enumerate(res.names) if nm.strip() == "script.dat"), None)
    if script_idx is None:
        print("ERROR: tidak ketemu 'script.dat' di resource.dat"); sys.exit(1)
    script = GPDAContainer.parse(res.entry_bytes(script_idx))
    print(f"[2/5] script.dat: {len(script.entries)} entri, {time.time()-t0:.1f}s")

    print(f"[3/5] Mengelompokkan baris CSV (apostrof -> {apos!r}, lebar dialog = {width}, "
          f"lebar narasi = {nwidth}, apos-w = {APOS_W}) ...")
    dialog_by = defaultdict(list)
    with open(dialog_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t = clean_en(row.get("english_text"), apos)
            note_overflow("dialog", f"{row['file'].split('___')[1]} {row['offset']}", t, width)
            row["english_text"] = wrap_pad(t, width)
            dialog_by[row["file"]].append(row)
    narr_by, choice_by, n_other = defaultdict(list), defaultdict(lambda: defaultdict(list)), defaultdict(int)
    with open(narr_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["english_text"] = clean_en(row.get("english_text"), apos)
            if row["kind"] == "narration/dialog":   # choice/menu TIDAK di-wrap/pad
                note_overflow("narasi", f"{row['scene'].strip()} inst{row['inst_index']}",
                              row["english_text"], nwidth)
                row["english_text"] = wrap_pad(row["english_text"], nwidth)
            sc = row["scene"].strip()
            if row["kind"] == "narration/dialog" and row["opcode"] == "100":
                narr_by[sc].append(row)
            elif row["kind"] == "choice/menu" and row["opcode"] == "103":
                choice_by[sc][int(row["inst_index"])].append(row)
            else:
                n_other[row["kind"]] += 1
    for g in choice_by.values():
        for rows in g.values():
            rows.sort(key=lambda r: int(r["str_index"]))
    n_ch = sum(len(r) for g in choice_by.values() for r in g.values())
    print(f"      dialog: {sum(map(len, dialog_by.values()))} | narasi: {sum(map(len, narr_by.values()))} "
          f"| choice: {n_ch} baris di {len(choice_by)} scene")
    for k, v in n_other.items():
        print(f"      (belum didukung, dilewati) {k}: {v} baris")
    if OVERFLOW:
        with open(OVERFLOW_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["sumber", "kunci", "jumlah_baris", "english_text"])
            w.writerows(sorted(OVERFLOW, key=lambda r: -r[2]))
        print(f"      !! {len(OVERFLOW)} teks lebih dari {MAX_LINES} baris (akan tembus kotak) -> {OVERFLOW_PATH}")

    print("[4/5] Patch tiap entri script.dat ...")
    repl, total, touched, skips, seen = {}, 0, 0, [], set()
    for i, name in enumerate(script.names):
        stem = name.strip().lstrip("_").rsplit(".dat", 1)[0]
        fname = f"resource.dat__script.dat___{stem}.dat___{stem}.dat___{stem}.obj.bin"
        d, n, c = dialog_by.get(fname, []), narr_by.get(stem, []), dict(choice_by.get(stem, {}))
        if n or c:
            seen.add(stem)
        if not (d or n or c):
            continue
        try:
            mid, cnt, sk = patch_one_script_entry(script.entry_bytes(i), d, n, c)
        except Exception as e:
            skips.append((stem, "-", f"EXCEPTION: {e!r}")); continue
        skips += [(stem, lab, r) for lab, r in sk]
        if mid is not None:
            repl[i] = mid; total += cnt; touched += 1
    for sc in sorted((set(narr_by) | set(choice_by)) - seen):
        skips.append((sc, "-", "scene tidak ada di script.dat"))
    print(f"      SELESAI: {touched} file, {total} instruksi dipatch, {len(skips)} skip, {time.time()-t0:.1f}s")
    cnt = defaultdict(int)
    for _, _, r in skips:
        cnt[r.split("(")[0].split(":")[0].strip()] += 1
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:10]:
        print(f"        {v:6d}  {k}")
    if report_path:
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["file_or_scene", "offset_or_inst", "reason"]); w.writerows(skips)
        print(f"      Laporan skip: {report_path}")
    if verify_only:
        print("\n--verify-only: berhenti di sini."); return
    print("[5/5] Rebuild script.dat lalu resource.dat ...")
    new_res = res.rebuild({script_idx: script.rebuild(repl)})
    Path(out_path).write_bytes(new_res)
    print(f"Ditulis ke: {out_path}  ({len(res_data)} -> {len(new_res)} byte)")
    print("LANGKAH BERIKUTNYA: python seekmap_rebuild.py build <output.DAT> <first.dat> <first_baru.dat>, lalu tes di PPSSPP.")


if __name__ == "__main__":
    a = sys.argv[1:]
    report, apos, width, nwidth = None, "\u2019", DEFAULT_WIDTH, None
    for flag in ("--report", "--apos", "--width", "--nwidth", "--apos-w", "--max-lines", "--overflow"):
        if flag in a:
            k = a.index(flag); val = a[k + 1] if k + 1 < len(a) else None
            a = a[:k] + a[k + 2:]
            if flag == "--report": report = val
            elif flag == "--width": width = int(val)
            elif flag == "--nwidth": nwidth = int(val)
            elif flag == "--apos-w": APOS_W = float(val)
            elif flag == "--max-lines": MAX_LINES = int(val)
            elif flag == "--overflow": OVERFLOW_PATH = val
            else: apos = val
    if nwidth is None:
        nwidth = 0 if width == 0 else DEFAULT_NWIDTH
    if a and a[0] == "--verify-only" and len(a) == 4:
        run(a[1], a[2], a[3], None, apos, report, True, width, nwidth)
    elif len(a) == 4:
        run(a[0], a[1], a[2], a[3], apos, report, False, width, nwidth)
    else:
        print(__doc__); sys.exit(1)
