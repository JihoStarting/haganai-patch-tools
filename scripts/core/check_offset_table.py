import gzip
from pathlib import Path
from gpda_v2 import GPDAContainer

def extract_objbin(resource_path, stem):
    res = GPDAContainer.parse(Path(resource_path).read_bytes())
    script_idx = next(i for i, nm in enumerate(res.names) if nm.strip() == "script.dat")
    script = GPDAContainer.parse(res.entry_bytes(script_idx))

    top_idx = next(i for i, nm in enumerate(script.names)
                    if nm.strip().lstrip("_").rsplit(".dat", 1)[0] == stem)
    mid = GPDAContainer.parse(script.entry_bytes(top_idx))
    inner = GPDAContainer.parse(mid.entry_bytes(0))
    gz_idx = next(j for j, nm in enumerate(inner.names) if ".obj.gz" in nm)
    return gzip.decompress(inner.entry_bytes(gz_idx))


# ============================================================
# GANTI 3 baris di bawah ini sesuai punya kamu:
# ============================================================

STEM = "0011ess0"

ORIG_RESOURCE_PATH = r"D:\Reverse engginering\project haganai\data ekstrak\RES.DAT"
PATCHED_RESOURCE_PATH = r"D:\Reverse engginering\project haganai\script_output\file final\RES_patched.DAT"
# ============================================================
# Tidak perlu diubah di bawah sini
# ============================================================

orig = extract_objbin(ORIG_RESOURCE_PATH, STEM)
patched = extract_objbin(PATCHED_RESOURCE_PATH, STEM)

print(f"orig size:    {len(orig)}")
print(f"patched size: {len(patched)}  (diff: {len(patched)-len(orig):+d})")
print()
print("--- 64 byte pertama ORIGINAL ---")
print(orig[:64].hex(" "))
print()
print("--- 64 byte pertama PATCHED ---")
print(patched[:64].hex(" "))
