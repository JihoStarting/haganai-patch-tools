#!/usr/bin/env python3
"""Terapkan fixes_dialog_v27_all.csv ke CSV dialog (kolom: file, offset, speaker, text, clean_text, english_text).

Pakai:
  python apply_dialog_v27.py haganai_dialogue_EN_v6.csv fixes_dialog_v27_all.csv haganai_dialogue_EN_v27.csv [--force]

Pencocokan: file + offset (hex atau desimal). Teks lama di fix dibandingkan dengan english_text
saat ini (apostrof/kutip disamakan). Yang tidak cocok TIDAK diterapkan (kecuali --force) dan
ditulis ke apply_dialog_v27_mismatch.csv. Satu fix tidak diterapkan dua kali.
"""
import csv, sys

def norm(s):
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u300c", ""), ("\u300d", "")):
        s = s.replace(a, b)
    return " ".join(s.split())

def stem(f):
    # "resource.dat__script.dat___0011ess0.dat___0011ess0.dat___0011ess0.obj.bin" -> "0011ess0"
    # "0011ess0.dat" -> "0011ess0"
    f = f.strip().split("___")[-1]
    for suf in (".obj.bin", ".obj.gz", ".dat", ".obj"):
        if f.endswith(suf):
            f = f[:-len(suf)]
    return f

def off(x):
    x = x.strip()
    try:
        return int(x, 16) if x.lower().startswith("0x") else int(x)
    except ValueError:
        return int(x, 16)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    if len(args) != 3:
        print(__doc__); sys.exit(1)
    src, fixes, dst = args
    raw = open(src, "rb").read()
    bom = raw[:3] == b"\xef\xbb\xbf"
    nl = "\r\n" if b"\r\n" in raw else "\n"
    rd = csv.DictReader(open(src, encoding="utf-8-sig", newline=""))
    fields, rows = rd.fieldnames, list(rd)
    for c in ("file", "offset", "english_text"):
        if c not in fields:
            sys.exit(f"kolom '{c}' tidak ada di {src}: {fields}")
    idx = {}
    for r in rows:
        idx.setdefault((stem(r["file"]), off(r["offset"])), []).append(r)
    applied = nf = mm = 0
    bad = []
    done = set()
    for f in csv.DictReader(open(fixes, encoding="utf-8-sig", newline="")):
        name, o = f["kunci"].rsplit(" ", 1)
        k = (stem(name), off(o))
        if k in done:
            continue
        g = idx.get(k)
        if not g:
            nf += 1; bad.append([f["kunci"], "tidak ketemu", "", f["english_text"]]); continue
        r = g[0]; cur = r["english_text"]
        if norm(cur) != norm(f["english_text_lama"]) and not force:
            mm += 1; bad.append([f["kunci"], "teks lama beda", cur, f["english_text"]]); continue
        new = f["english_text"]
        if cur.startswith("\u300c") and cur.endswith("\u300d"):
            new = "\u300c" + new + "\u300d"
        r["english_text"] = new
        done.add(k); applied += 1
    with open(dst, "w", encoding="utf-8-sig" if bom else "utf-8", newline="") as o:
        w = csv.DictWriter(o, fieldnames=fields, lineterminator=nl)
        w.writeheader(); w.writerows(rows)
    if bad:
        with open("apply_dialog_v27_mismatch.csv", "w", encoding="utf-8-sig", newline="") as o:
            w = csv.writer(o); w.writerow(["kunci", "masalah", "teks_sekarang", "teks_fix"]); w.writerows(bad)
    print(f"diterapkan: {applied} | tidak ketemu: {nf} | teks lama beda: {mm}")
    if bad:
        print("detail: apply_dialog_v27_mismatch.csv")

main()
