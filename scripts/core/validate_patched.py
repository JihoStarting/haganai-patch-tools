"""
validate_patched.py
====================
Validasi STRUKTURAL untuk file hasil patch (RES_patched.DAT) -- bukan
identity-check (jelas beda dari asli karena teksnya diganti), tapi cek:

1. Semua container GPDA (di semua level nested) bisa di-parse ulang
   tanpa error.
2. Semua entri di tiap container: offset+size tidak melewati batas
   container, tidak overlap satu sama lain, dan offset selalu kelipatan
   2048 (sector-aligned).
3. total_size di header tiap container konsisten dengan
   offset+size entri terakhir (harus persis sama, sesuai fix padding).
4. Spot-check: ambil beberapa nama file dari CSV, turun sampai ke
   .obj.bin-nya, decode, dan pastikan teks Inggris yang diharapkan
   ada persis di situ.

Cara pakai:
    python3 validate_patched.py RES_patched.DAT haganai_dialogue_EN_FIXED.csv
"""
import sys
import csv
import gzip
import struct
from pathlib import Path
from collections import defaultdict
from gpda_v2 import GPDAContainer

ALIGN = 2048
errors = []
containers_checked = 0


def check_container(data: bytes, label: str, depth: int = 0, max_depth: int = 6):
    global containers_checked
    try:
        c = GPDAContainer.parse(data)
    except Exception as e:
        return  # not a GPDA container, fine (leaf binary data)

    containers_checked += 1

    # header total_size harus sama dengan len(data) yang kita kasih
    if c.total_size != len(data):
        errors.append(f"{label}: total_size header ({c.total_size}) != actual data length ({len(data)})")

    # cek tiap entri: sector-aligned, tidak melewati batas, tidak overlap
    prev_end = None
    sorted_entries = sorted(enumerate(c.entries), key=lambda x: x[1][0])
    for idx, (off, size, name_off) in sorted_entries:
        if off % ALIGN != 0:
            errors.append(f"{label} entry[{idx}]: offset {off} tidak sector-aligned (2048)")
        if off + size > len(data):
            errors.append(f"{label} entry[{idx}]: offset+size ({off+size}) melewati batas container ({len(data)})")
        if prev_end is not None and off < prev_end:
            errors.append(f"{label} entry[{idx}]: overlap! offset {off} < prev_end {prev_end}")
        prev_end = ((off + size + ALIGN - 1) // ALIGN) * ALIGN

    # entri terakhir (by offset) harus pas di total_size (dengan padding 2048)
    if sorted_entries:
        last_idx, (last_off, last_size, _) = sorted_entries[-1]
        expected_total = ((last_off + last_size + ALIGN - 1) // ALIGN) * ALIGN
        if expected_total != len(data):
            errors.append(f"{label}: total container size ({len(data)}) != "
                           f"expected dari entri terakhir + padding ({expected_total})")

    if depth < max_depth:
        for i in range(c.count):
            entry_data = c.entry_bytes(i)
            check_container(entry_data, f"{label} > [{i}]({c.names[i]})", depth + 1, max_depth)


def spot_check_text(res: GPDAContainer, rows_by_file: dict, sample_files: list):
    script_idx = next(i for i, nm in enumerate(res.names) if nm.strip() == "script.dat")
    script = GPDAContainer.parse(res.entry_bytes(script_idx))

    print("\n--- SPOT-CHECK TEKS INGGRIS ---")
    for stem in sample_files:
        csv_fname = f"resource.dat__script.dat___{stem}.dat___{stem}.dat___{stem}.obj.bin"
        rows = rows_by_file.get(csv_fname)
        if not rows:
            print(f"  [{stem}] tidak ada di CSV, skip")
            continue

        idx = next((i for i, nm in enumerate(script.names)
                    if nm.strip().lstrip("_").rsplit(".dat", 1)[0] == stem), None)
        if idx is None:
            print(f"  [{stem}] TIDAK KETEMU di script.dat! (masalah)")
            errors.append(f"spot-check {stem}: entry tidak ditemukan di script.dat hasil patch")
            continue

        mid = GPDAContainer.parse(script.entry_bytes(idx))
        inner = GPDAContainer.parse(mid.entry_bytes(0))
        gz_idx = next((j for j, nm in enumerate(inner.names) if ".obj.gz" in nm), None)
        obj_bytes = gzip.decompress(inner.entry_bytes(gz_idx))

        found, total = 0, 0
        for r in rows:
            english = (r.get("english_text") or "").strip().strip('"')
            if not english:
                continue
            total += 1
            needle = english.encode("utf-16-le")
            if needle in obj_bytes:
                found += 1

        status = "OK" if found == total else "ADA YANG HILANG!"
        print(f"  [{stem}] {found}/{total} baris English ketemu di obj.bin hasil extract  [{status}]")
        if found != total:
            errors.append(f"spot-check {stem}: cuma {found}/{total} baris English ketemu")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 validate_patched.py RES_patched.DAT haganai_dialogue_EN_FIXED.csv")
        sys.exit(1)

    res_path, csv_path = sys.argv[1], sys.argv[2]

    print(f"Membaca {res_path} ...")
    data = Path(res_path).read_bytes()
    print(f"Ukuran: {len(data)} byte\n")

    print("=== 1. Cek struktur GPDA rekursif (semua level) ===")
    check_container(data, "RES_patched.DAT")
    print(f"Container GPDA diperiksa: {containers_checked}")

    print("\n=== 2. Spot-check teks Inggris ===")
    rows_by_file = defaultdict(list)
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows_by_file[row["file"]].append(row)

    res = GPDAContainer.parse(data)
    sample_files = ["0011ess0", "0012ess0", "0090ed10", "a076ess2", "a271sen0",
                     "0023mar0", "0044sen0"]
    spot_check_text(res, rows_by_file, sample_files)

    print(f"\n{'='*60}")
    if errors:
        print(f"❌ DITEMUKAN {len(errors)} MASALAH:")
        for e in errors:
            print(f"  - {e}")
        print("\nJANGAN inject ke ISO dulu -- ada yang perlu diperbaiki.")
        sys.exit(1)
    else:
        print("✅ SEMUA CEK LOLOS. Struktur valid, teks Inggris ketemu semua di sample.")
        print("File ini seharusnya aman untuk di-inject ke ISO/CSO.")


if __name__ == "__main__":
    main()
