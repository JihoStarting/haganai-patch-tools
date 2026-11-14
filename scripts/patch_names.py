"""
patch_names.py - ganti nama pembicara (夜空 -> Yozora, dst.) di RES.DAT yang SUDAH dipatch.

Tidak memakai CSV dan tidak menyentuh teks dialog: hanya awalan nama di instruksi op100
(speaker_field: dari +15 sampai tepat sebelum 「). Jumlah instruksi, urutan opcode, dan teks
setelah 「 tidak berubah, jadi aman dipakai di atas RES_v30_flow_test.DAT (atau build lain).

Pakai (di folder yang sama dengan pipeline.py):
    python patch_names.py RES_v30_flow_test.DAT --check
    python patch_names.py RES_v30_flow_test.DAT RES_v31_names.DAT
Lalu: python seekmap_rebuild.py build RES_v31_names.DAT "<first.dat asli>" first_new_v31_names.dat
"""
import gzip
import struct
import sys
import time
from collections import Counter
from pathlib import Path

import pipeline as P

NAME_MAP = {
    "夜空": "Yozora", "星奈": "Sena", "幸村": "Yukimura", "理科": "Rika",
    "小鳩": "Kobato", "マリア": "Maria", "天馬": "Tenma", "小鷹": "Kodaka",
}
EN_NAMES = set(NAME_MAP.values())
KAGI = b"\x0c\x30"  # 「 UTF-16LE


def rename_inst(inst: bytes):
    """Balikin (inst_baru, label) atau (None, alasan). label = nama JP yang diganti."""
    if inst[4:7] != b"\x64\x00\x00":
        return None, "bukan dialog"
    k = None
    for j in range(0, 12):                      # nama maks ~11 karakter
        p = 15 + 2 * j
        if inst[p:p + 2] == KAGI:
            k = j
            break
    if k is None:
        return None, "tanpa 「 di awal"
    sp = inst[15:15 + 2 * k]
    try:
        name = sp.decode("utf-16-le")
    except UnicodeDecodeError:
        return None, "speaker bukan UTF-16"
    if name in EN_NAMES:
        return None, "sudah Inggris"
    if name not in NAME_MAP:
        return None, f"speaker tak dikenal: {name!r}"
    text_start = 15 + 2 * k
    try:
        txt, end = P.decode_utf16le_until_null(inst, 15)
    except ValueError as e:
        return None, f"gagal decode: {e}"
    length_field = struct.unpack_from("<H", inst, 11)[0]
    if length_field != len(txt):
        return None, f"header mismatch (field={length_field}, len={len(txt)})"
    if any(inst[end:]):
        return None, "data non-nol setelah teks"
    new_sp = NAME_MAP[name].encode("utf-16-le")
    body = bytearray(inst[:11])
    body += struct.pack("<H", len(txt) - len(name) + len(NAME_MAP[name]))
    body += b"\x00\x00"
    body += new_sp
    body += inst[text_start:end]               # 「...」 + terminator, utuh
    c_new = len(bytes(body).rstrip(b"\x00"))
    new_size = P.ceil16(c_new + 5)
    body += b"\x00" * (new_size - len(body))
    struct.pack_into("<I", body, 0, new_size)
    return bytes(body), name


def process_objbin(data: bytes):
    count, first, insts = P.parse_instructions(data)
    if not P._is_aligned(insts):
        return None, Counter(), Counter({"file tidak 16-aligned": 1})
    done, why = Counter(), Counter()
    out = bytearray(data[:first])
    changed = 0
    for pos, size, op in insts:
        inst = data[pos:pos + size]
        if op == P.DIALOG_OPCODE:
            new, info = rename_inst(inst)
            if new is not None:
                done[info] += 1
                out += new
                changed += 1
                continue
            why[info if not info.startswith("speaker tak dikenal") else "speaker tak dikenal"] += 1
        out += inst
    if not changed:
        return None, done, why
    new_bytes = bytes(out)
    P.verify_objbin(data, new_bytes)
    return new_bytes, done, why


def main():
    a = sys.argv[1:]
    check = "--check" in a
    a = [x for x in a if x != "--check"]
    if not a or (not check and len(a) != 2):
        print(__doc__); sys.exit(1)
    t0 = time.time()
    res_data = Path(a[0]).read_bytes()
    res = P.GPDAContainer.parse(res_data)
    si = next(i for i, nm in enumerate(res.names) if nm.strip() == "script.dat")
    script = P.GPDAContainer.parse(res.entry_bytes(si))
    print(f"script.dat: {len(script.entries)} scene")
    repl, tot_done, tot_why, errs = {}, Counter(), Counter(), []
    for i, name in enumerate(script.names):
        try:
            mid = P.GPDAContainer.parse(script.entry_bytes(i))
            inner = P.GPDAContainer.parse(mid.entry_bytes(0))
            gz_idx = next((j for j, nm in enumerate(inner.names) if ".obj.gz" in nm), None)
            if gz_idx is None:
                continue
            obj = gzip.decompress(inner.entry_bytes(gz_idx))
            new, done, why = process_objbin(obj)
        except Exception as e:
            errs.append((name.strip(), repr(e)))
            continue
        tot_done.update(done)
        tot_why.update(why)
        if new is not None and not check:
            new_gz = gzip.compress(new, compresslevel=9, mtime=0)
            repl[i] = mid.rebuild({0: inner.rebuild({gz_idx: new_gz})})
    print("Nama yang diganti:", dict(tot_done), "| total", sum(tot_done.values()))
    print("Tidak diganti:", dict(tot_why))
    if errs:
        print(f"!! {len(errs)} scene error (TIDAK diubah), contoh:", errs[:3])
    if check:
        print(f"--check selesai ({time.time()-t0:.1f}s), tidak menulis file."); return
    new_res = res.rebuild({si: script.rebuild(repl)})
    Path(a[1]).write_bytes(new_res)
    print(f"{len(repl)} scene diubah. Ditulis: {a[1]} ({len(res_data)} -> {len(new_res)} byte), {time.time()-t0:.1f}s")
    print('LANGKAH BERIKUTNYA: python seekmap_rebuild.py build', a[1], '"<first.dat asli>" first_new_names.dat')


if __name__ == "__main__":
    main()
