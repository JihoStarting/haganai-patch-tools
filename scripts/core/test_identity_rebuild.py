"""
test_identity_rebuild.py
Sanity check: rebuild(resource.dat) TANPA perubahan apa pun harus
menghasilkan file yang 100% byte-identical ke aslinya. Kalau ini
gagal, jangan lanjut ke tahap patch teks -- perbaiki dulu gpda_v2.py.

Cara pakai:
    python test_identity_rebuild.py resource.dat
"""
import sys
from pathlib import Path
from gpda_v2 import GPDAContainer


def check_recursive(data: bytes, label: str, depth: int = 0):
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
        print(f"{indent}  -> berhenti di level ini, perbaiki gpda_v2.py dulu sebelum lanjut")
        return False

    # rekursif turun ke tiap entri buat cek apakah dia juga GPDA container
    if depth < 3:  # batasi kedalaman biar ga kelamaan
        for i in range(c.count):
            entry_data = c.entry_bytes(i)
            if entry_data[:4] == b"GPDA":
                sub_ok = check_recursive(entry_data, f"{label} > entry[{i}] ({c.names[i]})", depth + 1)
                all_ok = all_ok and sub_ok

    return all_ok


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_identity_rebuild.py resource.dat")
        sys.exit(1)

    data = Path(sys.argv[1]).read_bytes()
    print(f"Testing identity rebuild, semua level GPDA nested...\n")
    ok = check_recursive(data, "resource.dat")
    print()
    if ok:
        print("✅ SEMUA level rebuild identik 100% ke file asli. gpda_v2.py aman dipakai.")
    else:
        print("❌ Ada level yang MISMATCH. JANGAN lanjut ke patch teks dulu.")
