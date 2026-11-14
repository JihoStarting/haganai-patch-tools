"""
calibrate.py -- alat kalibrasi lebar kotak teks + penyiapan apostrof.
(gabungan make_ruler_test.py + make_ruler_test2.py + fix_csv.py + calibrate_lines.py)

1) ruler  -- KAPASITAS asli kotak dialog & choice dalam kolom (penggaris 123456789A123456789B...):
    python calibrate.py ruler <dialogue.csv> <remaining.csv> <dlg_ruler.csv> <rem_ruler.csv>
   Lalu build tanpa wrap:
    python pipeline.py RES.DAT dlg_ruler.csv rem_ruler.csv RES_ruler.DAT --width 0
   Rebuild seekmap/first.dat, jalankan 0011ess0 di PPSSPP, lihat di huruf mana baris patah.

2) ruler2 -- LEBAR KOLOM karakter non-angka (titik, apostrof, huruf sempit, elipsis):
    python calibrate.py ruler2 <dialogue.csv> <dlg_ruler2.csv>
   Lalu (remaining pakai yang asli, bukan rem_ruler):
    python pipeline.py RES.DAT dlg_ruler2.csv <remaining.csv> RES_ruler2.DAT --width 0
   Empat dialog pertama 0011ess0 = 10 karakter uji + penggaris. Baca di angka/huruf mana baris pertama
   patah (n). Lebar karakter uji = (39 - n) / 10 kolom.

3) apos -- ganti apostrof ASCII ' (tampil sebagai spade di font game) dengan karakter pengganti,
   sekaligus buang \\n:
    python calibrate.py apos ’ <in.csv> <out.csv>

4) apos-test -- bikin CSV uji 6 varian apostrof (A..F) untuk satu scene:
    python calibrate.py apos-test <dialogue.csv> <remaining.csv> <scene> <out_dialogue.csv> <out_remaining.csv>

5) lines -- ukur BERAPA BARIS yang muat di kotak teks (bukan lebar kolom). Tiap teks uji diganti 8 "kata" 30 karakter;
   tiap kata memenuhi satu baris penuh, jadi baris ke-N di layar berlabel L1..L8 (D = dialog, N = narasi di atas choice
   "...Neighbors Club?", M = narasi lain). Yang terlihat penuh di game = jumlah baris yang muat.
    python calibrate.py lines <dialogue.csv> <remaining.csv> <out_dialogue.csv> <out_remaining.csv>
   Lalu build DENGAN wrap bawaan (JANGAN --width 0), supaya tiap baris dipad pas:
    python pipeline.py RES.DAT <out_dialogue.csv> <out_remaining.csv> RES_lines.DAT
    python seekmap_rebuild.py build RES_lines.DAT first.dat first_lines.dat
   Jalankan 0011ess0 di PPSSPP, screenshot dialog + narasi + narasi sebelum choice.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from csv_tools import read, write  # noqa: E402

VARIANTS = [("A", "\u2019"), ("B", "\u00b4"), ("C", "\uff07"),
            ("D", "`"), ("E", "\u2018"), ("F", "\u2032")]


def ruler(n):
    return "".join("123456789" + chr(65 + i) for i in range(26))[:n]


def rewrite(src, dst, fn):
    fields, rows = read(src)
    fn(rows)
    write(dst, fields, rows)


# ---------------------------------------------------------------- ruler
def _ruler_dialog(rows):
    k = 0
    for r in rows:
        if "0011ess0" in r["file"] and k < 4:
            r["english_text"] = ruler(200 if k == 0 else 110 if k == 1 else 76 if k == 2 else 40)
            k += 1


def _ruler_remaining(rows):
    k = 0
    for r in rows:
        if r["scene"].strip() == "0011ess0" and r["kind"] == "narration/dialog" and k < 3:
            r["english_text"] = ruler(200 if k == 0 else 110 if k == 1 else 76)
            k += 1
        elif r["scene"].strip() == "0011ess0" and r["kind"] == "choice/menu":
            r["english_text"] = ruler(44 if r["str_index"] == "0" else 38)


def cmd_ruler(dlg, rem, out_dlg, out_rem):
    rewrite(dlg, out_dlg, _ruler_dialog)
    rewrite(rem, out_rem, _ruler_remaining)
    print("OK")


# ---------------------------------------------------------------- ruler2
def cmd_ruler2(dlg, out_dlg):
    tests = [".", "\u2019", "i", "\u2026"]
    fields, rows = read(dlg)
    k = 0
    for r in rows:
        if "0011ess0" in r["file"] and k < 4:
            r["english_text"] = tests[k] * 10 + ruler(90)
            k += 1
    write(out_dlg, fields, rows)
    print("OK")


# ---------------------------------------------------------------- apos
def cmd_apos(apos, src, dst):
    fields, rows = read(src)
    for r in rows:
        r["english_text"] = r["english_text"].replace("\n", " ").replace("'", apos)
    write(dst, fields, rows)


def cmd_apos_test(dlg, rem, scene, out_d, out_r):
    fd, d = read(dlg)
    fr, r = read(rem)
    d = [x for x in d if f"___{scene}.obj.bin" in x["file"]]
    r = [x for x in r if x["scene"].strip() == scene and x["opcode"] == "100"]
    i = 0
    for rows in (d, r):
        for x in rows:
            e = x["english_text"].replace("\n", " ")
            if "'" in e:
                tag, ch = VARIANTS[i % len(VARIANTS)]
                i += 1
                e = f"({tag}) " + e.replace("'", ch)
            x["english_text"] = e
    write(out_d, fd, d)
    write(out_r, fr, r)
    print("varian:", ", ".join(f"{t}={c!r}" for t, c in VARIANTS), "| baris diuji:", i)


def lines_text(tag, n=8, size=30):
    # tiap kata 30 karakter: dua kata tidak pernah muat sebaris (30+1+30 > 39), jadi 1 kata = 1 baris
    return " ".join(f"{tag}{k}" + "x" * (size - len(f"{tag}{k}")) for k in range(1, n + 1))


def cmd_lines(dlg, rem, out_dlg, out_rem):
    fd, d = read(dlg); fr, r = read(rem)
    k = 0
    for row in d:
        if "0011ess0" in row["file"] and k < 4:
            row["english_text"] = lines_text("D"); k += 1
    k = 0; hit = False
    for row in r:
        if row["scene"].strip() != "0011ess0" or row["kind"] != "narration/dialog":
            continue
        if "Neighbors Club?" in row["english_text"] and not hit:
            row["english_text"] = lines_text("N"); hit = True; continue   # kasus screenshot
        if k < 3:
            row["english_text"] = lines_text("M"); k += 1
    print("dialog diganti:", 4, "| narasi kasus screenshot ketemu:", hit, "| narasi lain:", k)
    write(out_dlg, fd, d); write(out_rem, fr, r)


def main(a):
    if a[:1] == ["ruler"] and len(a) == 5:
        cmd_ruler(*a[1:])
    elif a[:1] == ["ruler2"] and len(a) == 3:
        cmd_ruler2(*a[1:])
    elif a[:1] == ["apos"] and len(a) == 4:
        cmd_apos(*a[1:])
    elif a[:1] == ["apos-test"] and len(a) == 6:
        cmd_apos_test(*a[1:])
    elif a[:1] == ["lines"] and len(a) == 5:
        cmd_lines(*a[1:])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
