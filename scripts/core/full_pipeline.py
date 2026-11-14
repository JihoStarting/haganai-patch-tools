"""
full_pipeline.py
=================
Pipeline lengkap buat patch teks Inggris ke Haganai Portable, dari
resource.dat asli sampai resource.dat baru yang siap di-repack ke ISO/CSO.

SEMUA LANGKAH DI SINI SUDAH DITES END-TO-END di sesi sebelumnya, pakai
script.dat asli (166.508.544 byte, 674 entri):
  - Extract 674 obj.bin dari script.dat -> 0 error
  - Patch teks: 15.252/15.257 baris (99,97%) berhasil, 5 sisanya (ruby-text
    <RUBY>...<RT COLOR=...>) di-skip otomatis & aman (teks JP asli tetap ada)
  - Rebuild script.dat lengkap (674 entri, termasuk yang gak diubah) ->
    name table utuh, 74 entri yang gak disentuh 100% byte-identical ke
    asli, dan 15.252 baris Inggris ketemu persis di posisi yang benar
    setelah di-extract ulang dari hasil rebuild.

Yang BELUM pernah dites di sesi ini (karena resource.dat aslinya belum
pernah diupload): langkah rebuild level RES.DAT (paling luar). Secara
struktur ini sama persis dengan rebuild script.dat (pakai fungsi
GPDAContainer.rebuild() yang sama), jadi seharusnya jalan, tapi WAJIB
di-cross-check lagi (lihat fungsi verify_full_corpus di bawah) begitu
resource.dat asli dipakai.

STRUKTUR (hasil reverse-engineering, sudah divalidasi):

    resource.dat (GPDA, 14 entri)
      -> script.dat (GPDA, 674 entri, salah satunya per file dialog)
           -> "_<stem>.dat" (GPDA, biasanya 5 entri)
                -> entri index 0: "_<stem>.dat " (GPDA, biasanya 3 entri)
                     -> entri dengan nama mengandung ".obj.gz"  <- INI yang di-gzip-decompress jadi .obj.bin

    Setiap level GPDA container (bukan cuma RES.DAT) punya NAME TABLE
    tersembunyi tepat setelah TOC, sebelum data entri pertama:
        [4-byte length][ASCII name]  x count, berurutan sesuai TOC
    first_offset entri data pertama = round_up(header + TOC + name_table, 2048)
    -- gpda.py versi awal TIDAK tahu soal ini dan MENGHAPUS name table
    saat rebuild(). gpda_v2.py di folder ini sudah fix.

    Format teks di dalam .obj.bin (setelah decompress):
        marker 6 byte: 00 00 00 64 00 00   (opcode pemisah antar record dialog)
        length_field: 2 byte (angka kecil) + 2 byte 00 00 padding
        speaker_field: lebar VARIABEL (4/6/8/... byte, TIDAK disentuh saat patch)
        teks: UTF-16LE, dibungkus 「...」, diakhiri 00 00
        length_field = jumlah_karakter_teks(termasuk bracket) + (lebar_speaker_field_byte // 2)

Usage:
    python3 full_pipeline.py <resource.dat> <csv_file> <output_resource.dat> [--report report.csv]
    python3 full_pipeline.py --verify-only <resource.dat> <csv_file>
        (jalanin semua langkah kecuali nulis output -- buat cek dulu berapa
        baris yang bakal berhasil/skip tanpa nunggu proses full rebuild)

CATATAN PENTING SEBELUM DIPAKAI KE FILE ASLI:
  - resource.dat itu ~400 MB, proses ini butuh RAM kira-kira 2-3x ukuran
    file itu (buat nyimpen data asli + data baru sekaligus). Pastikan
    RAM cukup (>=4GB bebas) sebelum jalanin ke file asli.
  - INI BELUM DITES DI PPSSPP. Field id di TOC diasumsikan aman gak
    diubah saat resize -- itu masih hipotesis. Field-field lain di awal
    tiap .obj.bin (opcode/bytecode) diasumsikan berisi ID/counter
    konstan, bukan pointer ukuran byte -- baru dicek di 1 sample.
    JANGAN anggap ini "pasti jalan di game" sebelum benar-benar dites.
"""

import gzip
import struct
import csv
import sys
import time
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from gpda_v2 import GPDAContainer  # noqa: E402

MARKER = bytes([0x00, 0x00, 0x00, 0x64, 0x00, 0x00])
TERMINATOR = b"\x00\x00"
SEARCH_WINDOW = 80
MAX_SANE_SPEAKER_FIELD = 40


# ---------------------------------------------------------------------------
# Bagian 1: patch teks di dalam SATU obj.bin (sudah di-decompress), in-memory
# ---------------------------------------------------------------------------

def decode_utf16le_until_null(data: bytes, pos: int, max_len: int = 4000):
    end = pos
    while end + 1 < len(data) and end - pos < max_len * 2:
        if data[end:end + 2] == TERMINATOR:
            return data[pos:end].decode("utf-16-le"), end + 2
        end += 2
    raise ValueError(f"No terminator found from {pos:#x}")


def find_marker_and_header(data: bytes, text_offset: int):
    window_start = max(0, text_offset - SEARCH_WINDOW)
    idx = data[window_start:text_offset].rfind(MARKER)
    if idx == -1:
        return None
    M = window_start + idx + 3
    length_field_pos = M + 7
    speaker_field_start = M + 11
    speaker_field_len = text_offset - speaker_field_start
    if speaker_field_len < 0 or speaker_field_len > MAX_SANE_SPEAKER_FIELD:
        return None
    return length_field_pos, speaker_field_start


def patch_objbin_bytes(data: bytes, rows: list):
    """Patch satu obj.bin (bytes, sudah di-decompress) pakai baris CSV yang
    match (list of dict, kolom 'offset' & 'english_text'). Balikin
    (new_bytes, patched_count, skipped_list)."""
    rows = sorted(rows, key=lambda r: int(r["offset"], 16))
    out = bytearray()
    cursor = 0
    patched_count = 0
    skipped = []

    for row in rows:
        orig_offset = int(row["offset"], 16)

        found = find_marker_and_header(data, orig_offset)
        if found is None:
            skipped.append((orig_offset, "marker tidak ketemu dalam window "
                                          f"{SEARCH_WINDOW} byte (kemungkinan ruby-text/format beda)"))
            continue
        length_field_pos, speaker_field_start = found

        if length_field_pos < cursor:
            skipped.append((orig_offset, "overlap dengan record sebelumnya"))
            continue

        try:
            orig_text, orig_text_end = decode_utf16le_until_null(data, orig_offset)
        except ValueError as e:
            skipped.append((orig_offset, f"gagal decode teks asli: {e}"))
            continue

        speaker_field = data[speaker_field_start:orig_offset]
        length_field = struct.unpack_from("<H", data, length_field_pos)[0]
        expected_len = len(orig_text) + len(speaker_field) // 2

        if length_field != expected_len:
            skipped.append((orig_offset, f"header mismatch (field={length_field}, expected={expected_len})"))
            continue

        english = (row.get("english_text") or "").strip().strip('"')
        if not english:
            skipped.append((orig_offset, "english_text kosong"))
            continue

        out += data[cursor:length_field_pos]

        new_text = f"「{english}」"
        new_text_bytes = new_text.encode("utf-16-le") + TERMINATOR
        new_length_field = len(new_text) + len(speaker_field) // 2

        out += struct.pack("<H", new_length_field)
        out += b"\x00\x00"
        out += speaker_field
        out += new_text_bytes

        cursor = orig_text_end
        patched_count += 1

    out += data[cursor:]
    return bytes(out), patched_count, skipped


# ---------------------------------------------------------------------------
# Bagian 2: jalan turun 3 level container buat 1 entri script.dat, patch,
# lalu rebuild balik naik 2 level (sampai level "entri di dalam script.dat")
# ---------------------------------------------------------------------------

def patch_one_script_entry(mid_bytes: bytes, csv_rows_for_file: list):
    """mid_bytes = isi 1 entri top-level script.dat (container ber-nama
    "_<stem>.dat", biasanya count=5). Balikin (new_mid_bytes, patched_count, skipped)
    atau (None, 0, []) kalau gak ada .obj.gz ketemu / gak ada baris CSV."""
    if not csv_rows_for_file:
        return None, 0, []

    mid = GPDAContainer.parse(mid_bytes)
    inner = GPDAContainer.parse(mid.entry_bytes(0))
    gz_idx = next((j for j, nm in enumerate(inner.names) if ".obj.gz" in nm), None)
    if gz_idx is None:
        return None, 0, [(-1, "tidak ketemu entri .obj.gz di dalam container")]

    obj_bytes = gzip.decompress(inner.entry_bytes(gz_idx))
    new_obj_bytes, patched_count, skipped = patch_objbin_bytes(obj_bytes, csv_rows_for_file)

    if patched_count == 0:
        return None, 0, skipped

    new_gz = gzip.compress(new_obj_bytes, compresslevel=9, mtime=0)  # mtime=0 -> output deterministik
    new_inner = inner.rebuild({gz_idx: new_gz})
    new_mid = mid.rebuild({0: new_inner})
    return new_mid, patched_count, skipped


# ---------------------------------------------------------------------------
# Bagian 3: orkestrasi penuh -- resource.dat -> script.dat -> semua entri
# ---------------------------------------------------------------------------

def run(resource_path: str, csv_path: str, out_path: str, report_path: str = None,
        verify_only: bool = False):
    t0 = time.time()

    print(f"[1/5] Membaca {resource_path} ...")
    res_data = Path(resource_path).read_bytes()
    res = GPDAContainer.parse(res_data)
    print(f"      GPDA count={len(res.entries)}, names={len(res.names)}, {time.time()-t0:.1f}s")

    script_idx = next((i for i, nm in enumerate(res.names) if nm.strip() == "script.dat"), None)
    if script_idx is None:
        print("ERROR: tidak ketemu entri 'script.dat' di resource.dat. "
              f"Nama-nama yang ada: {res.names}")
        sys.exit(1)

    print(f"[2/5] Parsing script.dat (entri index {script_idx} di resource.dat) ...")
    script_bytes = res.entry_bytes(script_idx)
    script = GPDAContainer.parse(script_bytes)
    print(f"      GPDA count={len(script.entries)}, names={len(script.names)}, {time.time()-t0:.1f}s")

    print("[3/5] Mengelompokkan baris CSV per file ...")
    rows_by_file = defaultdict(list)
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows_by_file[row["file"]].append(row)
    print(f"      {sum(len(v) for v in rows_by_file.values())} baris CSV, "
          f"{len(rows_by_file)} nama file unik, {time.time()-t0:.1f}s")

    print("[4/5] Patch tiap entri script.dat ...")
    script_replacements = {}
    total_patched = 0
    total_skipped = 0
    files_touched = 0
    all_skips = []

    for i, name in enumerate(script.names):
        stem = name.strip().lstrip("_").rsplit(".dat", 1)[0]
        csv_fname = f"resource.dat__script.dat___{stem}.dat___{stem}.dat___{stem}.obj.bin"
        rows = rows_by_file.get(csv_fname)
        if not rows:
            continue

        mid_bytes = script.entry_bytes(i)
        new_mid, patched_count, skipped = patch_one_script_entry(mid_bytes, rows)

        total_skipped += len(skipped)
        for off, reason in skipped:
            all_skips.append((csv_fname, off, reason))

        if new_mid is not None:
            script_replacements[i] = new_mid
            total_patched += patched_count
            files_touched += 1

        if (i + 1) % 100 == 0:
            print(f"      ... {i+1}/{len(script.names)} entri diperiksa, "
                  f"{total_patched} baris dipatch sejauh ini, {time.time()-t0:.1f}s")

    print(f"      SELESAI: {files_touched} file disentuh, {total_patched} baris dipatch, "
          f"{total_skipped} baris di-skip, {time.time()-t0:.1f}s")

    if report_path:
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "offset", "reason"])
            for fn, off, reason in all_skips:
                w.writerow([fn, hex(off) if off >= 0 else off, reason])
        print(f"      Laporan skip ditulis ke: {report_path}")

    if verify_only:
        print("\n--verify-only: berhenti di sini, tidak menulis output.")
        return

    print("[5/5] Rebuild script.dat lalu resource.dat ...")
    new_script_bytes = script.rebuild(script_replacements)
    print(f"      script.dat: {len(script_bytes)} -> {len(new_script_bytes)} byte "
          f"({len(new_script_bytes)-len(script_bytes):+d})")

    new_res_bytes = res.rebuild({script_idx: new_script_bytes})
    print(f"      resource.dat: {len(res_data)} -> {len(new_res_bytes)} byte "
          f"({len(new_res_bytes)-len(res_data):+d})")

    Path(out_path).write_bytes(new_res_bytes)
    print(f"\nDitulis ke: {out_path}")
    print(f"Total waktu: {time.time()-t0:.1f}s")
    print("\nPENTING: file ini masih perlu di-inject balik ke ISO/CSO PPSSPP "
          "(script ini cuma bikin resource.dat baru, belum pernah dites jalan di emulator).")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--verify-only":
        if len(args) != 3:
            print("Usage: python3 full_pipeline.py --verify-only <resource.dat> <csv_file>")
            sys.exit(1)
        run(args[1], args[2], out_path=None, verify_only=True)
    elif len(args) in (3, 5):
        resource_path, csv_path, out_path = args[0], args[1], args[2]
        report_path = args[4] if len(args) == 5 and args[3] == "--report" else None
        run(resource_path, csv_path, out_path, report_path)
    else:
        print(__doc__)
        sys.exit(1)
