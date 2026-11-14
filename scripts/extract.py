"""
extract.py -- tahap awal: ambil dan cek dialog dari hasil ekstrak RES.DAT.
(gabungan extract_scripts.py + extract_dialogue.py + clean_dialogue.py + validate_dialogue.py)

Urutan lama:
    python extract.py scripts    # seekmap.dat + RES.DAT -> dat_gz/ & obj_gz/ (.bin per scene)
    python extract.py dialogue   # obj_gz/ -> dialogue_export.csv   (file, offset, speaker, text)
    python extract.py clean      # buang tag RUBY -> dialogue_export_clean.csv
    python extract.py validate   # cek kualitas dialogue_export.csv -> validation_report.txt

Path default ada di blok CONFIG di bawah (sama seperti script aslinya). Edit sesuai folder kamu.
"""
import csv
import gzip
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seekmap_rebuild as S  # noqa: E402

# ============ CONFIG - sesuaikan path ini ============
SEEKMAP_PATH = r"D:\Reverse engginering\project haganai\hasil_extract\first\seekmap.dat"
RESDAT_PATH  = r"D:\Reverse engginering\project haganai\data ekstrak\RES.DAT"
OUTPUT_DIR   = r"D:\Reverse engginering\project haganai\script_output"
OBJ_GZ_DIR   = r"D:\Reverse engginering\project haganai\script_output\obj_gz"
DIALOGUE_CSV = r"D:\Reverse engginering\project haganai\script_output\dialogue_export.csv"
CLEAN_CSV    = r"D:\Reverse engginering\project haganai\script_output\dialogue_export_clean.csv"
REPORT_PATH  = r"D:\Reverse engginering\project haganai\script_output\validation_report.txt"
# =======================================================

# ---------------------------------------------------------------- scripts
class Entry:
    __slots__ = ("name", "offset", "size", "checksum", "child_count", "depth", "path")

    def __init__(self, name, offset, size, checksum, child_count, depth):
        self.name = name
        self.offset = offset
        self.size = size
        self.checksum = checksum
        self.child_count = child_count
        self.depth = depth
        self.path = ""  # diisi belakangan (full path termasuk parent)


def parse_seekmap(path):
    """Baca seekmap.dat (gzip) lewat parser tunggal seekmap_rebuild.parse_seekmap, return list Entry."""
    with open(path, "rb") as f:
        recs = S.parse_seekmap(gzip.decompress(f.read()))
    entries, stack = [], []   # stack of (depth, path_so_far)
    for r in recs:
        name = S.rec_name(r).decode("latin1")
        while stack and stack[-1][0] >= r.depth:
            stack.pop()
        parent_path = stack[-1][1] if stack else ""
        e = Entry(name, r.off, r.size, r.crc, int(r.cc) if r.cc is not None else 0, r.depth)
        e.path = f"{parent_path}/{name}" if parent_path else name
        entries.append(e)
        stack.append((r.depth, e.path))
    return entries


def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def cmd_scripts():
    print("=" * 60)
    print("STEP 1: Parsing seekmap.dat ...")
    entries = parse_seekmap(SEEKMAP_PATH)
    print(f"Total entries ditemukan: {len(entries)}")

    print("\nSTEP 2: Mencari scene script (.dat.gz dan .obj.gz) di dalam script.dat ...")
    targets = [
        e for e in entries
        if "script.dat/" in e.path
        and (e.name.endswith(".dat.gz") or e.name.endswith(".obj.gz"))
    ]
    print(f"Ditemukan {len(targets)} file target untuk di-extract.")

    if not targets:
        print("!! Tidak ada target ditemukan. Cek lagi path/parsing seekmap.dat.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dat_gz_dir = os.path.join(OUTPUT_DIR, "dat_gz")   # kandidat teks dialog
    obj_gz_dir = os.path.join(OUTPUT_DIR, "obj_gz")   # kandidat bytecode
    os.makedirs(dat_gz_dir, exist_ok=True)
    os.makedirs(obj_gz_dir, exist_ok=True)

    print(f"\nSTEP 3: Membuka RES.DAT dan extract {len(targets)} file ...")
    ok_count = 0
    fail_count = 0

    with open(RESDAT_PATH, "rb") as res:
        for i, e in enumerate(targets, 1):
            try:
                res.seek(e.offset)
                raw_chunk = res.read(e.size)

                # coba decompress gzip
                try:
                    decompressed = gzip.decompress(raw_chunk)
                except Exception:
                    decompressed = None

                # tentukan nama file output dari path (biar gampang dilacak scene-nya)
                safe_path = sanitize(e.path.replace("/", "__"))

                if e.name.endswith(".dat.gz"):
                    out_dir = dat_gz_dir
                else:
                    out_dir = obj_gz_dir

                if decompressed is not None:
                    out_name = safe_path.replace(".gz", "") + ".bin"
                    out_path = os.path.join(out_dir, out_name)
                    with open(out_path, "wb") as out:
                        out.write(decompressed)
                else:
                    # simpan mentah kalau gagal decompress, biar bisa dicek manual
                    out_name = safe_path + ".raw"
                    out_path = os.path.join(out_dir, out_name)
                    with open(out_path, "wb") as out:
                        out.write(raw_chunk)

                ok_count += 1
            except Exception as ex:
                print(f"  GAGAL pada {e.path}: {ex}")
                fail_count += 1

            if i % 100 == 0:
                print(f"  ... {i}/{len(targets)} diproses")

    print("\n" + "=" * 60)
    print(f"SELESAI. Berhasil: {ok_count}, Gagal: {fail_count}")
    print(f"Hasil disimpan di:\n  {dat_gz_dir}\n  {obj_gz_dir}")
    print("=" * 60)


# ---------------------------------------------------------------- dialogue
OPEN_QUOTE = 0x300C   # 「
CLOSE_QUOTE = 0x300D  # 」


def is_name_char(cp):
    """Karakter yang wajar muncul di nama karakter (kanji/hiragana/katakana, TANPA simbol)."""
    return (
        0x3040 <= cp <= 0x309F or   # hiragana
        0x30A0 <= cp <= 0x30FF or   # katakana
        0x4E00 <= cp <= 0x9FFF      # kanji
    )


def read_utf16_char(data, i):
    """Baca 1 code unit UTF-16LE di posisi i. Return (codepoint, next_i) atau None kalau habis."""
    if i + 1 >= len(data):
        return None
    cp = data[i] | (data[i + 1] << 8)
    return cp, i + 2


def extract_from_file(fpath):
    with open(fpath, "rb") as f:
        data = f.read()

    results = []
    n = len(data)
    i = 0
    while i < n - 1:
        cp = data[i] | (data[i + 1] << 8)
        if cp == OPEN_QUOTE:
            dialogue_start = i
            # 1. Baca mundur untuk cari nama karakter (maks 8 karakter ke belakang)
            speaker_chars = []
            j = i - 2
            steps = 0
            while j >= 0 and steps < 8:
                cp_back = data[j] | (data[j + 1] << 8)
                if is_name_char(cp_back):
                    speaker_chars.insert(0, chr(cp_back))
                    j -= 2
                    steps += 1
                else:
                    break
            speaker = "".join(speaker_chars)

            # 2. Baca maju dari 「 sampai ketemu 」 (maks 2000 byte biar ga infinite loop kalau corrupt)
            dialogue_chars = []
            k = i + 2
            limit = min(n - 1, i + 2000)
            closed = False
            while k < limit:
                cp_fwd = data[k] | (data[k + 1] << 8)
                if cp_fwd == CLOSE_QUOTE:
                    closed = True
                    k += 2
                    break
                dialogue_chars.append(chr(cp_fwd))
                k += 2

            if closed and speaker:
                text = "".join(dialogue_chars)
                results.append((dialogue_start, speaker, text))
                i = k  # lanjut scan dari setelah 」
                continue

        i += 1  # scan per 1 byte, supaya alignment genap MAUPUN ganjil ke-cover
                 # (posisi teks UTF-16LE di file ini ternyata nggak selalu genap)

    return results


def cmd_dialogue():
    if not os.path.isdir(OBJ_GZ_DIR):
        print(f"!! Folder tidak ditemukan: {OBJ_GZ_DIR}")
        return

    all_rows = []
    filenames = sorted(os.listdir(OBJ_GZ_DIR))
    total = len(filenames)

    for idx, fname in enumerate(filenames, 1):
        fpath = os.path.join(OBJ_GZ_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            found = extract_from_file(fpath)
        except Exception as ex:
            print(f"  GAGAL di {fname}: {ex}")
            continue

        for offset, speaker, text in found:
            all_rows.append({
                "file": fname,
                "offset": f"0x{offset:X}",
                "speaker": speaker,
                "text": text,
            })

        if idx % 100 == 0:
            print(f"  ... {idx}/{total} file diproses, {len(all_rows)} dialog ditemukan sejauh ini")

    print(f"\nTotal dialog ditemukan: {len(all_rows)}")

    with open(DIALOGUE_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "offset", "speaker", "text"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Hasil disimpan di: {DIALOGUE_CSV}")
    print("Buka file ini pakai Excel atau Notepad untuk cek hasilnya.")


# ---------------------------------------------------------------- clean
# Pola: ≪RUBY≫[kanji]≪RT COLOR=#FFFFFF≫[bacaan]≪/RUBY≫  ->  ambil [kanji] saja
RUBY_PATTERN = re.compile(r'≪RUBY≫(.*?)≪RT COLOR=#FFFFFF≫(.*?)≪/RUBY≫')


def clean_text(text):
    return RUBY_PATTERN.sub(lambda m: m.group(1), text)


def cmd_clean():
    rows = []
    with open(DIALOGUE_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Total baris dibaca: {len(rows)}")

    ruby_count = 0
    for row in rows:
        original = row["text"]
        cleaned = clean_text(original)
        row["clean_text"] = cleaned
        if cleaned != original:
            ruby_count += 1

    print(f"Baris yang mengandung tag RUBY (dibersihkan): {ruby_count}")

    with open(CLEAN_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "offset", "speaker", "text", "clean_text"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Hasil disimpan di: {CLEAN_CSV}")

    # tampilkan beberapa contoh before/after biar bisa dicek cepat
    print("\nContoh before/after (5 baris pertama yang ada tag RUBY):")
    shown = 0
    for row in rows:
        if row["text"] != row["clean_text"]:
            print(f"  BEFORE: {row['text']}")
            print(f"  AFTER : {row['clean_text']}")
            print()
            shown += 1
        if shown >= 5:
            break


# ---------------------------------------------------------------- validate
# karakter yang "normal" ada di dialog: kanji, hiragana, katakana, ASCII biasa,
# tanda baca umum Jepang, dan beberapa simbol umum di VN (…, ―, dsb)
NORMAL_PATTERN = re.compile(
    r'^[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF'
    r'\uFF00-\uFFEF\u0020-\u007E\u2010-\u2015\u2026\u2018\u2019\u201C\u201D]*$'
)


def cmd_validate():
    rows = []
    with open(DIALOGUE_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Total baris: {len(rows)}")

    report = []
    report.append(f"Total baris: {len(rows)}")

    # 1. Cek nama karakter unik
    speakers = Counter(r["speaker"] for r in rows)
    report.append(f"\n{'='*60}")
    report.append(f"DAFTAR NAMA KARAKTER UNIK ({len(speakers)} total):")
    report.append(f"{'='*60}")
    for name, count in speakers.most_common():
        report.append(f"  {name}  ({count}x)")

    # 2. Cek teks dengan simbol "aneh" (di luar rentang normal)
    weird_rows = []
    for r in rows:
        text = r["text"]
        if not NORMAL_PATTERN.match(text):
            weird_chars = set(c for c in text if not NORMAL_PATTERN.match(c))
            weird_rows.append((r["file"], r["offset"], r["speaker"], text, weird_chars))

    report.append(f"\n{'='*60}")
    report.append(f"BARIS DENGAN SIMBOL DI LUAR RENTANG NORMAL ({len(weird_rows)} baris):")
    report.append(f"{'='*60}")
    for file, offset, speaker, text, chars in weird_rows[:50]:
        chars_hex = ", ".join(f"U+{ord(c):04X}({c})" for c in chars)
        report.append(f"  [{file} @ {offset}] {speaker}: {text}")
        report.append(f"      simbol aneh: {chars_hex}")
    if len(weird_rows) > 50:
        report.append(f"  ... dan {len(weird_rows) - 50} baris lainnya")

    # 3. Cek teks terlalu pendek (mungkin salah tangkap)
    short_rows = [r for r in rows if len(r["text"]) <= 1]
    report.append(f"\n{'='*60}")
    report.append(f"BARIS DENGAN TEKS SANGAT PENDEK (<=1 karakter): {len(short_rows)} baris")
    report.append(f"{'='*60}")
    for r in short_rows[:30]:
        report.append(f"  [{r['file']} @ {r['offset']}] {r['speaker']}: '{r['text']}'")

    # 4. Cek teks terlalu panjang (mungkin gagal nemu penutup, kebaca sampai jauh)
    long_rows = [r for r in rows if len(r["text"]) > 200]
    report.append(f"\n{'='*60}")
    report.append(f"BARIS DENGAN TEKS SANGAT PANJANG (>200 karakter): {len(long_rows)} baris")
    report.append(f"{'='*60}")
    for r in long_rows[:20]:
        preview = r["text"][:100] + "..." if len(r["text"]) > 100 else r["text"]
        report.append(f"  [{r['file']} @ {r['offset']}] {r['speaker']}: {preview}")

    # 5. Cek baris duplikat persis (file+offset sama = beneran duplikat proses)
    seen = Counter((r["file"], r["offset"]) for r in rows)
    dupes = [k for k, v in seen.items() if v > 1]
    report.append(f"\n{'='*60}")
    report.append(f"BARIS DENGAN (file+offset) DUPLIKAT: {len(dupes)} kasus")
    report.append(f"{'='*60}")
    for file, offset in dupes[:20]:
        report.append(f"  {file} @ {offset}")

    # 6. Cek nama karakter yang "aneh" (bukan pola kanji/hiragana/katakana wajar)
    NAME_PATTERN = re.compile(r'^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]*$')
    weird_names = [n for n in speakers if not NAME_PATTERN.match(n)]
    report.append(f"\n{'='*60}")
    report.append(f"NAMA KARAKTER YANG POLANYA MENCURIGAKAN: {len(weird_names)}")
    report.append(f"{'='*60}")
    for n in weird_names:
        report.append(f"  '{n}'  ({speakers[n]}x)")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"\nLaporan lengkap disimpan di: {REPORT_PATH}")
    print(f"Ringkasan:")
    print(f"  - {len(speakers)} nama karakter unik")
    print(f"  - {len(weird_rows)} baris dengan simbol di luar rentang normal")
    print(f"  - {len(short_rows)} baris teks sangat pendek")
    print(f"  - {len(long_rows)} baris teks sangat panjang")
    print(f"  - {len(dupes)} duplikat (file+offset)")
    print(f"  - {len(weird_names)} nama karakter mencurigakan")

COMMANDS = {"scripts": cmd_scripts, "dialogue": cmd_dialogue, "clean": cmd_clean, "validate": cmd_validate}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
