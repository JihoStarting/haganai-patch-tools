"""
csv_tools.py -- semua alat untuk MERAWAT CSV terjemahan (dialog + remaining) dalam satu file.
(gabungan apply_fixes + apply_short + apply_choice_fixes + apply_choice_short + choice_gaps + choice_missing +
 fill_todo + find_long_choices + "Fix encoding chars" + verify_length)
Taruh satu folder dengan pipeline.py (dipakai untuk wrap/lebar kolom & baca RES.DAT).

SUBCOMMAND                               FUNGSI
  fix            terapkan perbaikan terjemahan kepanjangan / buat daftar kerja (dulu apply_fixes)
  short          terapkan teks yang dipendekkan ke CSV dialog+remaining (dulu apply_short)
  choice-fixes   terapkan choice_fixes.csv (kolom english_baru) ke remaining (dulu apply_choice_fixes)
  choice-short   terapkan choice_unik.csv (kolom pendek_baru) ke remaining (dulu apply_choice_short)
  choice-gaps    list | merge  -- lengkapi entri choice yang tidak ada di CSV (dulu choice_gaps)
  choice-missing lengkapi entri choice bersyarat dari RES.DAT + bikin todo (dulu choice_missing)
  fill-todo      isi english_text kosong dari todo yang sudah diterjemahkan (dulu fill_todo)
  long-choices   daftar choice lebih panjang dari batas (dulu find_long_choices)
  encoding       ganti karakter yang tidak bisa di-encode (dulu "Fix encoding chars")
  verify-length  cek panjang byte terjemahan vs asli, format lama id/original/translated (dulu verify_length)

Usage:  python csv_tools.py <subcommand> <argumen...>     (tanpa argumen = tampil bantuan ini)

--- fix ---------------------------------------------------------------------------------------------
  1) terapkan:   python csv_tools.py fix fixes_batch1.csv FULL_dialogue_wrap.csv FULL_remaining_wrap.csv
     -> menulis *_fixed.csv (file asli TIDAK diubah; kalau input sudah berakhiran _fixed, ditimpa + .bak).
     Perbaikan yang SETELAH diterapkan masih > max-lines baris ditolak (kecuali --force).
  2) daftar kerja teks > max-lines baris (paling parah dulu):
     python csv_tools.py fix --worklist next.csv --limit 40 FULL_dialogue_wrap_fixed.csv FULL_remaining_wrap_fixed.csv
  3) daftar choice kepanjangan (> --cmax):
     python csv_tools.py fix --choice-worklist choice_long.csv FULL_dialogue_wrap_fixed.csv FULL_remaining_wrap_fixed.csv
  fixes.csv: kolom  type,scene,ref,english_new
     type  = dialog | narration | choice
     scene = dialog: potongan nama file di antara '___' (mis. a070rcs0.dat) ; narasi/choice: kolom scene (mis. 0048ess3)
     ref   = dialog: offset (0x14D3) ; narasi: inst#N ; choice: inst#N:str_index (inst#19:1)
  Opsi: --width 37 --nwidth 39 --max-lines 3 --cmax 38 --apos-w 1.5 --force

--- short -------------------------------------------------------------------------------------------
  python csv_tools.py short <fixes.csv> <dialogue.csv> <remaining.csv> <out_dialogue.csv> <out_remaining.csv> [--lines 2]
  fixes.csv: sumber,scene,id,english_text   (sumber = dialog|narasi ; id = offset hex (dialog) atau inst_index (narasi))
  Teks yang tidak muat <= --lines baris tetap diterapkan tapi diberi PERINGATAN.

--- choice-fixes ------------------------------------------------------------------------------------
  python csv_tools.py choice-fixes choice_fixes.csv FULL_remaining_wrap_fixed.csv [out.csv]
  Kunci: scene + inst_index + str_index (ref "inst#86:1"); jp_text harus sama dengan kolom jp. Tanpa out.csv ->
  remaining ditimpa (backup .bak dibuat dulu). Batas aman choice: 38 kolom (ASCII=1, U+2019=1.5, lainnya=2).

--- choice-short ------------------------------------------------------------------------------------
  python csv_tools.py choice-short <remaining.csv> <choice_unik.csv> <out.csv>
  Dicocokkan lewat (jp_text, english_text asli) -> satu edit berlaku ke semua baris sama. pendek_baru kosong = diabaikan.

--- choice-gaps -------------------------------------------------------------------------------------
  python csv_tools.py choice-gaps list  <RES.DAT asli> <remaining.csv> <skip.csv> <choice_full.csv>
  python csv_tools.py choice-gaps merge <remaining.csv> <choice_full_terisi.csv> <remaining_out.csv>
  list : tulis SEMUA entri tiap instruksi choice yang "jumlah pilihan beda"; yang tidak ada di CSV status=missing.
  merge: setelah english_text 'missing' diisi, gabungkan ke remaining.

--- choice-missing ----------------------------------------------------------------------------------
  python csv_tools.py choice-missing <RES.DAT> <remaining.csv> <skip.csv> <remaining_out.csv> [--todo todo.csv]
  Entri hilang diisi KOSONG (terjemahan lama dipertahankan lewat teks Jepang). 0000Index tidak disentuh
  (8 entri pertamanya ditulis ke index_preview.txt).

--- fill-todo ---------------------------------------------------------------------------------------
  python csv_tools.py fill-todo <remaining_dengan_baris_kosong.csv> <choice_todo_terisi.csv> <remaining_out.csv>
  Kunci (scene, inst_index, str_index) + jp_text harus sama persis; baris yang sudah terisi tidak ditimpa.

--- long-choices ------------------------------------------------------------------------------------
  python csv_tools.py long-choices <remaining.csv> [--max 22] [--out choice_terlalu_panjang.csv]

--- encoding ----------------------------------------------------------------------------------------
  python csv_tools.py encoding <in.csv> [--col-translated english_text] [--en-encoding cp1252] [--output out.csv] [--list-only]
  Edit dict REPLACEMENTS di bawah kalau mau mapping sendiri.

--- verify-length -----------------------------------------------------------------------------------
  python csv_tools.py verify-length <in.csv> [--output verify_report.csv] [--tolerance N] [--max-chars-line N] [--en-encoding cp1252]
  (alat LAMA: CSV berkolom id,original,translated[,max_bytes]; pipeline baru mengubah ukuran instruksi sendiri,
   jadi untuk cek lebar/baris pakai "fix --worklist".)
"""
import argparse
import csv
import gzip
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pipeline as pl  # noqa: E402
from pipeline import GPDAContainer, parse_instructions, parse_choice  # noqa: E402

USAGE_FIX = USAGE_SHORT = USAGE_CHOICE_FIXES = USAGE_CHOICE_SHORT = USAGE_CHOICE_MISSING = USAGE_FILL_TODO = USAGE_LONG = __doc__




# ---------------------------------------------------------------------------
# fix
# ---------------------------------------------------------------------------

APOS = "\u2019"


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def write(path, fields, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def out_path(src):
    pth = Path(src)
    if pth.stem.endswith("_fixed"):
        shutil.copyfile(pth, str(pth) + ".bak")
        return pth
    return pth.with_name(pth.stem + "_fixed" + pth.suffix)


def nlines(text, W):
    return len(pl.wrap_lines(pl.clean_en(text, APOS), W))


def cut_needed(text, W, max_lines):
    t = pl.clean_en(text, APOS); words = t.split(); k = 0
    while k < len(words) and len(pl.wrap_lines(" ".join(words[:len(words) - k]), W)) > max_lines:
        k += 1
    return len(t) - len(" ".join(words[:len(words) - k]))


def collect(drows, nrows, W, NW, ml):
    out = []
    for r in drows:
        n = nlines(r["english_text"], W)
        if n > ml:
            out.append(dict(type="dialog", scene=r["file"].split("___")[1], ref=r["offset"], speaker=r["speaker"],
                            jp=r["text"], english=pl.clean_en(r["english_text"], APOS), lines=n,
                            cut=cut_needed(r["english_text"], W, ml)))
    for r in nrows:
        if r["kind"] == "narration/dialog" and r["opcode"] == "100":
            n = nlines(r["english_text"], NW)
            if n > ml:
                out.append(dict(type="narration", scene=r["scene"].strip(), ref=f"inst#{r['inst_index']}", speaker="",
                                jp=r["jp_text"], english=pl.clean_en(r["english_text"], APOS), lines=n,
                                cut=cut_needed(r["english_text"], NW, ml)))
    out.sort(key=lambda x: (-x["cut"], x["scene"], x["ref"]))
    return out


def cmd_fix(a):
    a = list(a)
    opt = dict(width=37, nwidth=39, ml=3, force=False, worklist=None, limit=0, cmax=38, cwork=None)
    for flag, key, cast in (("--width", "width", int), ("--nwidth", "nwidth", int), ("--max-lines", "ml", int), ("--cmax", "cmax", int),
                            ("--apos-w", None, float), ("--worklist", "worklist", str), ("--choice-worklist", "cwork", str), ("--limit", "limit", int)):
        if flag in a:
            k = a.index(flag); val = a[k + 1]; a = a[:k] + a[k + 2:]
            if key: opt[key] = cast(val)
            else: pl.APOS_W = cast(val)
    if "--force" in a:
        a.remove("--force"); opt["force"] = True
    W, NW, ml = opt["width"], opt["nwidth"], opt["ml"]

    if opt["cwork"]:
        if len(a) != 2: print(USAGE_FIX); sys.exit(1)
        _, nrows = read(a[1])
        out = []
        for r in nrows:
            if r["kind"] == "choice/menu" and r["opcode"] == "103":
                t = pl.clean_en(r["english_text"], APOS)
                n = pl.cw(t) / 2
                if n > opt["cmax"]:
                    out.append(dict(scene=r["scene"].strip(), ref=f"inst#{r['inst_index']}:{r['str_index']}",
                                    jp=r["jp_text"], english=t, kolom=n))
        out.sort(key=lambda x: -x["kolom"])
        write(opt["cwork"], ["scene", "ref", "jp", "english", "kolom"], out)
        print(f"{len(out)} choice lebih dari {opt['cmax']} kolom -> {opt['cwork']}")
        return
    if opt["worklist"]:
        if len(a) != 2: print(USAGE_FIX); sys.exit(1)
        _, drows = read(a[0]); _, nrows = read(a[1])
        wl = collect(drows, nrows, W, NW, ml)
        if opt["limit"]: wl = wl[:opt["limit"]]
        write(opt["worklist"], ["type", "scene", "ref", "speaker", "jp", "english", "lines", "cut"], wl)
        print(f"{len(wl)} teks ditulis ke {opt['worklist']} (kolom cut = perkiraan karakter yang perlu dibuang)")
        return
    if len(a) != 3: print(USAGE_FIX); sys.exit(1)

    _, fixes = read(a[0])
    dfields, drows = read(a[1]); nfields, nrows = read(a[2])
    didx, nidx = {}, {}
    for i, r in enumerate(drows):
        didx.setdefault((r["file"].split("___")[1], r["offset"].strip()), []).append(i)
    for i, r in enumerate(nrows):
        if r["kind"] == "narration/dialog" and r["opcode"] == "100":
            nidx.setdefault((r["scene"].strip(), f"inst#{r['inst_index']}"), []).append(i)
    cidx = {}
    for i, r in enumerate(nrows):
        if r["kind"] == "choice/menu" and r["opcode"] == "103":
            cidx.setdefault((r["scene"].strip(), f"inst#{r['inst_index']}:{r['str_index']}"), []).append(i)
    ok = rejected = missing = 0
    log = []
    for fx in fixes:
        typ, key, new = fx["type"].strip(), (fx["scene"].strip(), fx["ref"].strip()), fx["english_new"].strip()
        idx, rows, lim = ((didx, drows, W) if typ == "dialog" else
                          (cidx, nrows, 0) if typ == "choice" else (nidx, nrows, NW))
        hit = idx.get(key, [])
        if len(hit) != 1:
            missing += 1; log.append((typ, *key, "TIDAK DITERAPKAN: baris " + ("tidak ketemu" if not hit else "ganda"))); continue
        if typ == "choice":
            if not new or (pl.cw(pl.clean_en(new, APOS)) > opt["cmax"] * 2 and not opt["force"]):
                rejected += 1; log.append((typ, *key, f"DITOLAK: kosong/lebih dari {opt['cmax']} karakter -> {new[:60]}")); continue
            rows[hit[0]]["english_text"] = new
            ok += 1; continue
        n = nlines(new, lim)
        if not new or (n > ml and not opt["force"]):
            rejected += 1; log.append((typ, *key, f"DITOLAK: masih {n} baris (maks {ml}) -> {new[:60]}")); continue
        rows[hit[0]]["english_text"] = new
        ok += 1
    po, pn = out_path(a[1]), out_path(a[2])
    write(po, dfields, drows); write(pn, nfields, nrows)
    print(f"diterapkan: {ok} | ditolak (masih kepanjangan): {rejected} | tidak ketemu: {missing}")
    for l in log: print("  ", *l)
    left = collect(drows, nrows, W, NW, ml)
    print(f"sisa teks > {ml} baris: {len(left)} (dialog {sum(x['type']=='dialog' for x in left)}, "
          f"narasi {sum(x['type']=='narration' for x in left)})")
    ch = [r for r in nrows if r["kind"] == "choice/menu" and r["opcode"] == "103"]
    empty = sum(1 for r in ch if not r["english_text"].strip())
    long_ = sum(1 for r in ch if pl.cw(pl.clean_en(r["english_text"], APOS)) > opt["cmax"] * 2)
    print(f"choice: {len(ch)} baris | kosong {empty} | lebih dari {opt['cmax']} karakter {long_}")
    print(f"ditulis: {po} , {pn}")


# ---------------------------------------------------------------------------
# short
# ---------------------------------------------------------------------------

def _short_cw(s):
    return sum(2 if ord(c) < 128 else (3 if c == "\u2019" else 4) for c in s)


def _short_nlines(s, W):
    lim, n, cur = int(W * 2), 0, ""
    words = s.replace("'", "\u2019").split()
    for w in words:
        while _short_cw(w) > lim:
            if cur:
                n += 1; cur = ""
            k, acc = 0, 0
            while k < len(w) and acc + _short_cw(w[k]) <= lim:
                acc += _short_cw(w[k]); k += 1
            n += 1; w = w[k:]
        if not cur:
            cur = w
        elif _short_cw(cur) + 2 + _short_cw(w) <= lim:
            cur += " " + w
        else:
            n += 1; cur = w
    return n + (1 if cur else 0)


def cmd_short(a):
    a = list(a)
    lines = 2
    if "--lines" in a:
        i = a.index("--lines"); lines = int(a[i + 1]); a = a[:i] + a[i + 2:]
    if len(a) != 5:
        print(USAGE_SHORT); sys.exit(1)
    _, fx = read(a[0]); fd, d = read(a[1]); fr, r = read(a[2])
    dmap = {}
    for x in d:
        sc = x["file"].split("___")[-1].replace(".obj.bin", "")
        dmap[(sc, int(x["offset"], 16))] = x
    nmap = {(x["scene"].strip(), x["inst_index"].strip()): x for x in r if x["kind"] == "narration/dialog"}
    ok = warn = miss = 0
    for f in fx:
        t = " ".join(f["english_text"].split())
        if f["sumber"] == "dialog":
            row, W = dmap.get((f["scene"].strip(), int(f["id"], 16))), 37
        else:
            row, W = nmap.get((f["scene"].strip(), f["id"].strip())), 39
        if row is None:
            miss += 1; print("TIDAK KETEMU:", f["sumber"], f["scene"], f["id"]); continue
        n = _short_nlines(t, W)
        if n > lines:
            warn += 1; print(f"PERINGATAN {n} baris: {f['sumber']} {f['scene']} {f['id']}: {t}")
        row["english_text"] = t; ok += 1
    write(a[3], fd, d); write(a[4], fr, r)
    print(f"{ok} teks diterapkan, {warn} masih > {lines} baris, {miss} tidak ketemu")


# ---------------------------------------------------------------------------
# choice-fixes
# ---------------------------------------------------------------------------

CHOICE_LIMIT = 38.0

def _cw1(s):
    return sum(1 if ord(c) < 128 else (1.5 if c == "\u2019" else 2) for c in s)

def cmd_choice_fixes(a):
    if len(a) not in (2, 3):
        print(USAGE_CHOICE_FIXES); sys.exit(1)
    fixes_p, rem_p = a[0], a[1]
    out_p = a[2] if len(a) == 3 else rem_p
    with open(fixes_p, encoding="utf-8-sig", newline="") as f:
        fixes = {}
        for r in csv.DictReader(f):
            inst, idx = r["ref"].replace("inst#", "").split(":")
            fixes[(r["scene"].strip(), inst, idx)] = r
    with open(rem_p, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f); fields = rd.fieldnames; rows = list(rd)
    need = {"scene", "inst_index", "str_index", "jp_text", "english_text", "kind"}
    if not need <= set(fields):
        print("ERROR: kolom remaining tidak lengkap, kurang:", need - set(fields)); sys.exit(1)
    done, seen = 0, set()
    for r in rows:
        k = (r["scene"].strip(), str(int(r["inst_index"])), str(int(r["str_index"])))
        fx = fixes.get(k)
        if not fx or r["kind"] != "choice/menu":
            continue
        if r["jp_text"].strip() != fx["jp"].strip():
            print(f"SKIP {k}: jp_text beda"); continue
        r["english_text"] = fx["english_baru"]; seen.add(k); done += 1
    for k in fixes.keys() - seen:
        print(f"TIDAK KETEMU/SKIP: {k}")
    if out_p == rem_p:
        import os, time
        bak = rem_p + ".bak"
        if os.path.exists(bak):          # jangan timpa backup lama
            bak = f"{rem_p}.{time.strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copyfile(rem_p, bak)
        print("backup:", bak)
    with open(out_p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    over = [r for r in rows if r["kind"] == "choice/menu" and _cw1(r["english_text"]) > CHOICE_LIMIT]
    print(f"{done}/{len(fixes)} choice diperbarui -> {out_p}")
    print(f"choice masih > {CHOICE_LIMIT} kolom: {len(over)}")
    for r in over[:30]:
        print(f"  {r['scene'].strip()} inst{r['inst_index']}:{r['str_index']}  {_cw1(r['english_text'])}  {r['english_text']}")


# ---------------------------------------------------------------------------
# choice-short
# ---------------------------------------------------------------------------

def norm(s):
    return " ".join((s or "").replace("\\n", " ").split())


def cmd_choice_short(a):
    if len(a) != 3:
        print(USAGE_CHOICE_SHORT); sys.exit(1)
    src, mapf, out = a
    mp = {}
    with open(mapf, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            new = (r.get("pendek_baru") or "").strip()
            if new:
                mp[(r["jp_text"], norm(r["english_text"]))] = new
    with open(src, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)
    n = 0
    for r in rows:
        if r.get("kind") == "choice/menu":
            k = (r["jp_text"], norm(r["english_text"]))
            if k in mp:
                r["english_text"] = mp[k]; n += 1
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    print(f"{len(mp)} pemetaan, {n} baris diganti -> {out}")


# ---------------------------------------------------------------------------
# choice-gaps (list | merge)
# ---------------------------------------------------------------------------

def align(entries_text, rows):
    """entries_text: [jp] urutan entri instruksi; rows: baris CSV urut. Balikin (status list, jumlah_baris_terpakai)."""
    out, p = [], 0
    for t in entries_text:
        if p < len(rows) and rows[p]["jp_text"] == t:
            out.append(rows[p]); p += 1
        else:
            out.append(None)
    return out, p


def load_choice_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f); fields = rd.fieldnames; rows = list(rd)
    g = defaultdict(list)
    for r in rows:
        if r["kind"] == "choice/menu" and r["opcode"] == "103":
            g[(r["scene"].strip(), int(r["inst_index"]))].append(r)
    for v in g.values():
        v.sort(key=lambda r: int(r["str_index"]))
    return fields, rows, g


def cmd_choice_gaps_list(res_path, rem_csv, skip_csv, out_csv):
    targets = []
    with open(skip_csv, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["reason"].startswith("jumlah pilihan beda"):
                targets.append((r["file_or_scene"].strip(), int(r["offset_or_inst"].replace("inst#", ""))))
    fields, _, groups = load_choice_rows(rem_csv)
    res = GPDAContainer.parse(Path(res_path).read_bytes())
    si = next(i for i, n in enumerate(res.names) if n.strip() == "script.dat")
    script = GPDAContainer.parse(res.entry_bytes(si))
    by_scene = defaultdict(list)
    for sc, ix in targets:
        by_scene[sc].append(ix)
    out, n_missing, problems = [], 0, []
    for i, name in enumerate(script.names):
        stem = name.strip().lstrip("_").rsplit(".dat", 1)[0]
        if stem not in by_scene:
            continue
        mid = GPDAContainer.parse(script.entry_bytes(i))
        inner = GPDAContainer.parse(mid.entry_bytes(0))
        gz = next(j for j, nm in enumerate(inner.names) if ".obj.gz" in nm)
        data = gzip.decompress(inner.entry_bytes(gz))
        _, _, insts = parse_instructions(data)
        for ix in sorted(by_scene[stem]):
            pos, size, op = insts[ix]
            _, _, entries, _ = parse_choice(data[pos:pos + size])
            texts = [t for _, t, _ in entries]
            rows = groups.get((stem, ix), [])
            matched, used = align(texts, rows)
            if used != len(rows):
                problems.append((stem, ix, f"hanya {used}/{len(rows)} baris CSV cocok urut dengan entri"))
            for k, (t, m) in enumerate(zip(texts, matched)):
                out.append({"scene": stem, "inst_index": ix, "opcode": 103, "str_index": k, "kind": "choice/menu",
                            "jp_text": t, "jp_clean": t, "english_text": m["english_text"] if m else "",
                            "status": "matched" if m else "missing"})
                n_missing += m is None
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields + ["status"]); w.writeheader(); w.writerows(out)
    print(f"{len(by_scene)} scene, {len({(r['scene'], r['inst_index']) for r in out})} instruksi, "
          f"{len(out)} entri, {n_missing} perlu diterjemahkan -> {out_csv}")
    for p in problems:
        print("PERINGATAN:", p)


def cmd_choice_gaps_merge(rem_csv, full_csv, out_csv):
    fields, rows, _ = load_choice_rows(rem_csv)
    with open(full_csv, encoding="utf-8-sig", newline="") as f:
        full = list(csv.DictReader(f))
    newg = defaultdict(list)
    for r in full:
        newg[(r["scene"].strip(), int(r["inst_index"]))].append(r)
    ok = {}
    for k, v in newg.items():
        v.sort(key=lambda r: int(r["str_index"]))
        if any(not (r["english_text"] or "").strip() for r in v):
            print(f"LEWATI {k[0]} inst#{k[1]}: masih ada english_text kosong"); continue
        ok[k] = [{c: r.get(c, "") for c in fields} for r in v]
    out, done = [], set()
    for r in rows:
        k = (r["scene"].strip(), int(r["inst_index"]) if r["inst_index"].strip().isdigit() else -1)
        if r["kind"] == "choice/menu" and k in ok:
            if k not in done:
                out += ok[k]; done.add(k)
            continue
        out.append(r)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    print(f"{len(done)} instruksi digabung, {len(newg) - len(done)} dilewati -> {out_csv}")


# ---------------------------------------------------------------------------
# choice-missing
# ---------------------------------------------------------------------------

def build_rows(entries_jp, old_rows, scene, inst):
    """entries_jp: [jp]; old_rows: baris CSV lama utk (scene, inst). Balikin baris lengkap (list dict)."""
    tmpl = dict(old_rows[0]) if old_rows else {}
    by_jp = {r["jp_text"]: r["english_text"] for r in old_rows}
    out = []
    for i, jp in enumerate(entries_jp):
        r = dict(tmpl)
        r.update(scene=scene, kind="choice/menu", opcode="103", inst_index=str(inst), str_index=str(i),
                 jp_text=jp, english_text=by_jp.get(jp, ""))
        out.append(r)
    return out


def cmd_choice_missing(a):
    a = list(a)
    todo_path = None
    if "--todo" in a:
        k = a.index("--todo"); todo_path = a[k + 1]; a = a[:k] + a[k + 2:]
    if len(a) != 4:
        print(USAGE_CHOICE_MISSING); sys.exit(1)
    res = GPDAContainer.parse(Path(a[0]).read_bytes())
    sidx = next(i for i, n in enumerate(res.names) if n.strip() == "script.dat")
    script = GPDAContainer.parse(res.entry_bytes(sidx))
    with open(a[1], encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f); fields = rd.fieldnames; rows = list(rd)
    with open(a[2], encoding="utf-8-sig", newline="") as f:
        skips = [r for r in csv.reader(f)][1:]
    want, preview = [], []
    for scene, inst, reason in skips:
        if not reason.startswith("jumlah pilihan beda") or not inst.startswith("inst#"):
            continue
        (preview if scene == "0000Index" else want).append((scene, int(inst[5:])))

    def entries_of(scene, inst):
        i = next(k for k, n in enumerate(script.names) if n.strip().lstrip("_").rsplit(".dat", 1)[0] == scene)
        mid = GPDAContainer.parse(script.entry_bytes(i))
        inner = GPDAContainer.parse(mid.entry_bytes(0))
        gz = next(j for j, nm in enumerate(inner.names) if ".obj.gz" in nm)
        data = gzip.decompress(inner.entry_bytes(gz))
        _, _, insts = parse_instructions(data)
        pos, size, _ = insts[inst]
        _, n_hdr, ents, _ = parse_choice(data[pos:pos + size])
        return [e[1] for e in ents]

    def key(r):
        return (r["scene"].strip(), r["inst_index"]) if r["kind"] == "choice/menu" and r["opcode"] == "103" else None

    new_sets, todo = {}, []
    for scene, inst in want:
        jp = entries_of(scene, inst)
        old = [r for r in rows if key(r) == (scene, str(inst))]
        full = build_rows(jp, old, scene, inst)
        new_sets[(scene, str(inst))] = full
        todo += [(scene, inst, r["str_index"], r["jp_text"]) for r in full if not r["english_text"].strip()]
    out, done = [], set()
    for r in rows:
        k = key(r)
        if k in new_sets:
            if k not in done:
                out += [{f: x.get(f, "") for f in fields} for x in new_sets[k]]; done.add(k)
            continue
        out.append(r)
    with open(a[3], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    if todo_path:
        with open(todo_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f); w.writerow(["scene", "inst_index", "str_index", "jp_text", "english_text"])
            w.writerows([t + ("",) for t in todo])
    with open("index_preview.txt", "w", encoding="utf-8") as f:
        for scene, inst in preview:
            jp = entries_of(scene, inst)
            f.write(f"{scene} inst#{inst}: {len(jp)} entri\n" + "\n".join(f"   {j}" for j in jp[:8]) + "\n\n")
    print(f"{len(want)} instruksi dilengkapi, {len(todo)} baris masih kosong -> {todo_path or '(tidak ditulis)'}")
    print(f"{len(preview)} instruksi 0000Index -> index_preview.txt ; hasil: {a[3]}")


# ---------------------------------------------------------------------------
# fill-todo
# ---------------------------------------------------------------------------

def cmd_fill_todo(a):
    if len(a) != 3:
        print(USAGE_FILL_TODO); sys.exit(1)
    with open(a[1], encoding="utf-8-sig", newline="") as f:
        todo = {(r["scene"].strip(), r["inst_index"].strip(), r["str_index"].strip()): r for r in csv.DictReader(f)}
    with open(a[0], encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f); fields = rd.fieldnames; rows = list(rd)
    filled = blank = mismatch = 0
    for r in rows:
        if r["kind"] != "choice/menu" or (r["english_text"] or "").strip():
            continue
        t = todo.get((r["scene"].strip(), r["inst_index"].strip(), r["str_index"].strip()))
        if t is None:
            blank += 1; continue
        if t["jp_text"] != r["jp_text"]:
            mismatch += 1; print("TIDAK COCOK jp_text:", r["scene"], r["inst_index"], r["str_index"]); continue
        if (t["english_text"] or "").strip():
            r["english_text"] = t["english_text"].strip(); filled += 1
        else:
            blank += 1
    with open(a[2], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"{filled} baris diisi, {blank} choice masih kosong, {mismatch} tidak cocok -> {a[2]}")


# ---------------------------------------------------------------------------
# long-choices
# ---------------------------------------------------------------------------

def cmd_long_choices(a):
    a = list(a)
    mx, out = 22, "choice_terlalu_panjang.csv"
    for flag in ("--max", "--out"):
        if flag in a:
            k = a.index(flag)
            val = a[k + 1] if k + 1 < len(a) else None
            a = a[:k] + a[k + 2:]
            if flag == "--max":
                mx = int(val)
            else:
                out = val
    if len(a) != 1:
        print(USAGE_LONG)
        sys.exit(1)

    with open(a[0], encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("kind") == "choice/menu"]

    def clean(s):
        return (s or "").replace("\\n", " ").replace("\r\n", " ").replace("\n", " ").strip()

    bad = [r for r in rows if len(clean(r.get("english_text"))) > mx]
    print(f"{len(bad)} dari {len(rows)} baris choice lebih dari {mx} karakter")

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["scene", "inst_index", "str_index", "jp_text", "english_text", "len"])
        for r in bad:
            t = clean(r.get("english_text"))
            w.writerow([r["scene"], r["inst_index"], r["str_index"], r.get("jp_text", ""), t, len(t)])
    print("Ditulis ke", out)


# ---------------------------------------------------------------------------
# encoding
# ---------------------------------------------------------------------------

# Mapping default: silakan diedit sesuai kebutuhan/gaya translasi kamu
REPLACEMENTS = {
    "①": "",      # penanda efek/nada suara di eroge, biasanya dekoratif -> dihapus
    "②": "",
    "③": "",
    "④": "",
    "⑤": "",
    "♪": "",      # musical note dekoratif -> dihapus (bisa juga diganti "~")
    "☆": "*",
    "♥": "<3",
    "▽": "o",     # bagian emoticon (＾▽＾) -> (^o^)
    "△": "^",     # bagian emoticon (＞△＜) -> (>^<)
    "〃": '"',     # ditto mark
    "≧": ">=",
    "≦": "<=",
    "―": "-",     # horizontal bar (U+2015, INVALID di cp1252) -> hyphen
    # catatan: em dash biasa "—" (U+2014) TIDAK perlu diganti, itu valid di cp1252
    "ō": "o",
    "ē": "e",
    "ā": "a",
    "ī": "i",
    "ū": "u",
}


def try_encode(text, encoding):
    try:
        text.encode(encoding)
        return True
    except UnicodeEncodeError:
        return False


def cmd_encoding(args):
    parser = argparse.ArgumentParser(prog="csv_tools.py encoding", description="Fix karakter yang gak bisa di-encode ke target encoding.")
    parser.add_argument("input_csv")
    parser.add_argument("--col-translated", default="english_text", help="Nama kolom teks Inggris")
    parser.add_argument("--en-encoding", default="cp1252", help="Target encoding (default cp1252)")
    parser.add_argument("--output", default="fixed_output.csv", help="Nama file CSV hasil fix")
    parser.add_argument("--list-only", action="store_true", help="Cuma tampilin karakter bermasalah, gak ubah file")
    args = parser.parse_args(args)

    try:
        with open(args.input_csv, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
    except FileNotFoundError:
        print(f"File tidak ditemukan: {args.input_csv}")
        sys.exit(1)

    if args.col_translated not in fieldnames:
        print(f"Kolom '{args.col_translated}' tidak ada. Kolom tersedia: {', '.join(fieldnames)}")
        sys.exit(1)

    if args.list_only:
        found = {}
        for r in rows:
            text = r.get(args.col_translated, "") or ""
            for ch in text:
                if ord(ch) > 127 and not try_encode(ch, args.en_encoding):
                    found[ch] = found.get(ch, 0) + 1
        print("Karakter bermasalah yang ditemukan (dan jumlah kemunculan):")
        for ch, count in sorted(found.items(), key=lambda x: -x[1]):
            mapped = REPLACEMENTS.get(ch, "??? BELUM ADA DI MAPPING ???")
            print(f"  {ch!r:6} x{count:<4} -> akan diganti jadi: {mapped!r}")
        return

    fixed_count = 0
    still_broken = []
    for r in rows:
        text = r.get(args.col_translated, "") or ""
        original_text = text
        for bad_char, replacement in REPLACEMENTS.items():
            # cuma ganti kalau karakter itu BENERAN gagal di-encode ke target,
            # biar karakter valid (misal em dash "—" di cp1252) gak ikut keganti
            if bad_char in text and not try_encode(bad_char, args.en_encoding):
                text = text.replace(bad_char, replacement)
        if text != original_text:
            fixed_count += 1
        r[args.col_translated] = text

        if not try_encode(text, args.en_encoding):
            unmapped = [ch for ch in text if ord(ch) > 127 and not try_encode(ch, args.en_encoding)]
            still_broken.append((r.get("offset") or r.get("id") or "?", text, unmapped))

    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Selesai. {fixed_count} baris diubah.")
    print(f"Hasil disimpan di: {args.output}")

    if still_broken:
        print(f"\n⚠️  Masih ada {len(still_broken)} baris dengan karakter yang BELUM ada di mapping:")
        for row_id, text, unmapped in still_broken:
            print(f"  ID {row_id}: {unmapped} -> \"{text}\"")
        print("\nTambahin karakter di atas ke dict REPLACEMENTS di script ini, lalu jalankan ulang.")
    else:
        print("✅ Semua karakter sekarang aman di-encode ke", args.en_encoding)


# ---------------------------------------------------------------------------
# verify-length
# ---------------------------------------------------------------------------

def safe_encode_len(text, encoding):
    try:
        return len(text.encode(encoding)), None
    except UnicodeEncodeError as e:
        return None, f"Karakter tidak bisa di-encode ke {encoding}: {e}"


def check_row(row, tolerance, max_chars_line, en_encoding):
    original = row.get("original", "") or ""
    translated = row.get("translated", "") or ""
    manual_limit = row.get("max_bytes", "") or ""

    orig_bytes, _ = safe_encode_len(original, "shift_jis")
    trans_bytes, enc_err = safe_encode_len(translated, en_encoding)

    if enc_err:
        return {
            **row,
            "orig_bytes": orig_bytes if orig_bytes is not None else "",
            "trans_bytes": "",
            "limit_used": "",
            "diff": "",
            "status": "ENCODING_ERROR",
            "note": enc_err,
        }

    if manual_limit.strip():
        try:
            limit = int(manual_limit)
        except ValueError:
            limit = orig_bytes
    else:
        limit = orig_bytes if orig_bytes is not None else 0

    limit_with_tolerance = limit + tolerance
    diff = trans_bytes - limit_with_tolerance

    status = "OK"
    note = ""

    if diff > 0:
        status = "OVERFLOW"
        note = f"Kelebihan {diff} byte dari limit ({limit_with_tolerance})"
    elif trans_bytes > limit:
        status = "WARNING"
        note = f"Melebihi panjang asli tapi masih dalam toleransi (+{trans_bytes - limit} byte)"

    if max_chars_line:
        for i, line in enumerate(translated.split("\\n"), start=1):
            if len(line) > max_chars_line:
                extra = f"Baris ke-{i} kepanjangan ({len(line)} char > {max_chars_line})"
                note = (note + " | " + extra).strip(" |")
                if status == "OK":
                    status = "WARNING"

    return {
        **row,
        "orig_bytes": orig_bytes,
        "trans_bytes": trans_bytes,
        "limit_used": limit_with_tolerance,
        "diff": diff,
        "status": status,
        "note": note,
    }


def cmd_verify_length(args):
    parser = argparse.ArgumentParser(prog="csv_tools.py verify-length", description="Cek panjang hasil translate vs teks asli.")
    parser.add_argument("input_csv", help="File CSV berisi original & translated")
    parser.add_argument("--output", default="verify_report.csv", help="Nama file hasil laporan")
    parser.add_argument("--tolerance", type=int, default=0,
                         help="Toleransi kelebihan byte yang masih dianggap aman (default 0)")
    parser.add_argument("--max-chars-line", type=int, default=0,
                         help="Batas karakter per baris untuk cek wrap textbox (0 = tidak dicek)")
    parser.add_argument("--en-encoding", default="cp1252",
                         help="Encoding target teks Inggris di ROM, misal cp1252, ascii, utf-8 (default cp1252)")
    args = parser.parse_args(args)

    try:
        with open(args.input_csv, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"File tidak ditemukan: {args.input_csv}")
        sys.exit(1)

    if not rows or "original" not in rows[0] or "translated" not in rows[0]:
        print("CSV harus punya minimal kolom: id, original, translated (max_bytes opsional)")
        sys.exit(1)

    results = [check_row(r, args.tolerance, args.max_chars_line, args.en_encoding) for r in rows]

    fieldnames = ["id", "original", "translated", "orig_bytes", "trans_bytes",
                  "limit_used", "diff", "status", "note"]
    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    total = len(results)
    overflow = sum(1 for r in results if r["status"] == "OVERFLOW")
    warning = sum(1 for r in results if r["status"] == "WARNING")
    enc_err = sum(1 for r in results if r["status"] == "ENCODING_ERROR")
    ok = total - overflow - warning - enc_err

    print(f"\n=== HASIL VERIFY LENGTH ===")
    print(f"Total baris     : {total}")
    print(f"OK              : {ok}")
    print(f"WARNING         : {warning}")
    print(f"OVERFLOW        : {overflow}")
    print(f"ENCODING_ERROR  : {enc_err}")
    print(f"Laporan lengkap disimpan di: {args.output}\n")

    if overflow or enc_err:
        print("⚠️  Ada baris yang perlu direvisi/dipersingkat sebelum insert ke ROM.")
    else:
        print("✅ Semua baris aman untuk di-insert (sesuai limit yang dipakai).")


# ---------------------------------------------------------------------------
# dispatcher
# ---------------------------------------------------------------------------

def main(a):
    cmd, rest = (a[0], a[1:]) if a else ("", [])
    if cmd == "fix":
        cmd_fix(rest)
    elif cmd == "short":
        cmd_short(rest)
    elif cmd == "choice-fixes":
        cmd_choice_fixes(rest)
    elif cmd == "choice-short":
        cmd_choice_short(rest)
    elif cmd == "choice-gaps":
        if rest[:1] == ["list"] and len(rest) == 5:
            cmd_choice_gaps_list(*rest[1:])
        elif rest[:1] == ["merge"] and len(rest) == 4:
            cmd_choice_gaps_merge(*rest[1:])
        else:
            print(__doc__); sys.exit(1)
    elif cmd == "choice-missing":
        cmd_choice_missing(rest)
    elif cmd == "fill-todo":
        cmd_fill_todo(rest)
    elif cmd == "long-choices":
        cmd_long_choices(rest)
    elif cmd == "encoding":
        cmd_encoding(rest)
    elif cmd == "verify-length":
        cmd_verify_length(rest)
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
