"""
dump.py -- alat INSPEKSI & recon: lihat isi RES.DAT, scene, instruksi, dan cari pola byte/teks.
(gabungan extract_one + dump_inst + dump_choice2 + gpda_v2 CLI + extract_from_resdat + scan_shiftjis + scan_utf16 +
 find_exact_bytes + find_gpda_entry + locate_seekmap_in_resdat + verify_text)
Taruh satu folder dengan pipeline.py.

LIHAT ISI RES.DAT
  python dump.py tree  <file> [--report out.txt] [--max-depth 4]
      Struktur GPDA semua level nested (nama, offset, ukuran).
  python dump.py entry <RES.DAT>                      -> daftar entri level atas (tandai script.dat = GPDA count 674)
  python dump.py entry <RES.DAT> <index> <out.dat>    -> simpan satu entri level atas ke file
  python dump.py obj   <RES.DAT> <stem> <out.obj>
      Simpan .obj (hasil gunzip) satu scene + cetak header-nya (u32 per 4 byte). <stem> = potongan nama (0011ess0).
  python dump.py inst  <RES.DAT> <scene> <inst_index> [<inst_index> ...]
      Hex dump instruksi + coba decode UTF-16LE (buat reverse format opcode).  Contoh: dump.py inst RES.DAT 0000Index 3 4 5
  python dump.py hex   <RES.DAT> <out.txt> <scene:inst> [<scene:inst> ...]
      Hex dump beberapa instruksi sekaligus.  Contoh: dump.py hex RES.DAT dump_fail.txt 0023kob0:19 a490ess1:78

CARI / SCAN (recon; path TIDAK lagi hardcode, kasih sebagai argumen)
  python dump.py scan  sjis|utf16 <dir> [<dir> ...] [--out report.txt] [--min N]
      Cari kandidat teks Shift-JIS (min default 3) / UTF-16LE Jepang (min default 2) di semua file dalam folder
      (mis. dat_gz/ dan obj_gz/ hasil extract.py scripts).
  python dump.py find  <teks | hex:AABBCC...> <path> [<path> ...]
      Cari pola byte persis (UTF-16LE, Shift-JIS, UTF-8 dari teks; atau hex mentah) di file / semua file dalam folder
      (boleh termasuk RES.DAT mentah).  Contoh: dump.py find ボンヤリ obj_gz RES.DAT   |   dump.py find hex:DC30F330 obj_gz
  python dump.py text  <file.obj.bin> <offset_hex> [--before 100] [--after 400]
      Hex dump + decode UTF-16LE di sekitar offset (buat memastikan teks ketemu benar-benar kalimat utuh).
  python dump.py gpda-entry <RES.DAT> <first.dat> <nama_hint> [--scan-mb 4]
      Cari representasi 4-byte LE dari offset/size entri seekmap (first.dat) di header RES.DAT.
  python dump.py seekmap-pos <seekmap.dat> <RES.DAT>
      Cek apakah seekmap.dat muncul persis sebagai substring di RES.DAT.

INVENTARIS OPCODE (dulu jumpscan.py)
  python dump.py opcodes <RES.DAT> [--out jumpscan.txt]
      Daftar semua opcode di semua scene: jumlah, jumlah scene, ukuran terbanyak, dan contoh byte.
      Hanya membaca; menulis jumpscan.txt. Dipakai untuk mencari instruksi yang membawa target lompat.
"""
import collections
import gzip
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pipeline as pl  # noqa: E402
import seekmap_rebuild as sm  # noqa: E402
from pipeline import GPDAContainer, parse_instructions  # noqa: E402


def _script_container(res_path):
    res = GPDAContainer.parse(Path(res_path).read_bytes())
    sidx = next(i for i, n in enumerate(res.names) if n.strip() == "script.dat")
    return GPDAContainer.parse(res.entry_bytes(sidx))


def _scene_obj(script, i):
    """Entri script.dat ke-i -> bytes .obj (sudah di-gunzip)."""
    mid = GPDAContainer.parse(script.entry_bytes(i))
    inner = GPDAContainer.parse(mid.entry_bytes(0))
    gz = next(j for j, nm in enumerate(inner.names) if ".obj.gz" in nm)
    return gzip.decompress(inner.entry_bytes(gz))


def _scene_index(script, scene):
    """Cocok persis pada nama scene (tanpa '_' depan dan '.dat'), None kalau tidak ada."""
    return next((k for k, n in enumerate(script.names)
                 if n.strip().lstrip("_").rsplit(".dat", 1)[0] == scene), None)


def _hexdump(b):
    return "\n".join(f"{i:04x}  " + " ".join(f"{x:02x}" for x in b[i:i + 16]) for i in range(0, len(b), 16))


# ---------------------------------------------------------------- obj
def cmd_obj(res_path, stem, out_path):
    script = _script_container(res_path)
    mi = next(i for i, n in enumerate(script.names) if stem in n)
    obj = _scene_obj(script, mi)
    Path(out_path).write_bytes(obj)
    print(f"{out_path}: {len(obj)} byte")
    print("Header (u32 per 4 byte):")
    for off in range(0, 0x40, 4):
        v = struct.unpack_from("<I", obj, off)[0]
        print(f"  0x{off:02X}: {v:>10}  (0x{v:X})")


# ---------------------------------------------------------------- inst
def cmd_inst(res_path, scene, idxs):
    script = _script_container(res_path)
    i = _scene_index(script, scene)
    if i is None:
        print("scene tidak ditemukan")
        return
    data = _scene_obj(script, i)
    count, first, insts = parse_instructions(data)
    print(f"scene={scene} jumlah instruksi={count} first={first:#x}")
    for k in idxs:
        pos, size, op = insts[k]
        raw = data[pos:pos + size]
        print(f"\n--- inst#{k} opcode={op} pos={pos:#x} size={size}")
        for o in range(0, len(raw), 16):
            print(f"{o:04x}  {raw[o:o + 16].hex(' ')}")
        try:
            print("utf16 (dari +11):", raw[11:].decode("utf-16-le", errors="replace").replace("\x00", "·"))
        except Exception as e:
            print("decode gagal:", e)


# ---------------------------------------------------------------- hex
def cmd_hex(res_path, out_path, specs):
    script = _script_container(res_path)
    lines = []
    for spec in specs:
        scene, inst = spec.split(":")
        inst = int(inst)
        i = _scene_index(script, scene)
        if i is None:
            lines.append(f"=== {scene}: tidak ketemu di script.dat")
            continue
        data = _scene_obj(script, i)
        _, _first, insts = parse_instructions(data)
        pos, size, op = insts[inst]
        lines.append(f"=== scene={scene} inst#{inst} opcode={op} pos={pos:#x} size={size}")
        lines.append(_hexdump(data[pos:pos + size]))
        lines.append("")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    print("Ditulis ke", out_path)


# ---------------------------------------------------------------- entry (dulu extract_from_resdat)
def cmd_entry(res_path, index=None, out_path=None):
    data = Path(res_path).read_bytes()
    top = GPDAContainer.parse(data)
    if index is None:
        print(f"RES.DAT: total_size={top.total_size} (file size={len(data)}) count={len(top.entries)}\n")
        for i, (off, size, _noff) in enumerate(top.entries):
            info = ""
            if data[off:off + 4] == b"GPDA":
                nested_total, _res, nested_count = struct.unpack_from("<III", data, off + 4)
                info = f"  <-- GPDA nested, count={nested_count}, nested_total_size={nested_total}"
                if nested_count == 674:
                    info += "   *** INI KEMUNGKINAN script.dat ***"
            print(f"[{i}] name={top.names[i].strip()!r} offset={off:#x} ({off}) size={size}{info}")
        return
    off, size, _ = top.entries[int(index)]
    chunk = data[off:off + size]
    Path(out_path).write_bytes(chunk)
    print(f"Extracted entry[{index}]: offset={off:#x} size={size} -> {out_path}")
    print(f"Magic check: {chunk[:4]}")


# ---------------------------------------------------------------- scan (dulu scan_shiftjis + scan_utf16)
def _is_sjis_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def _is_sjis_trail(b):
    return (0x40 <= b <= 0x7E) or (0x80 <= b <= 0xFC)


def _find_sjis_runs(data, min_run):
    """Rangkaian karakter 2-byte Shift-JIS valid berurutan >= min_run. Balikin [(start, end, raw)]."""
    runs, i, n = [], 0, len(data)
    while i < n - 1:
        if _is_sjis_lead(data[i]) and _is_sjis_trail(data[i + 1]):
            start, count = i, 0
            while i < n - 1 and _is_sjis_lead(data[i]) and _is_sjis_trail(data[i + 1]):
                i += 2
                count += 1
            if count >= min_run:
                runs.append((start, i, data[start:i]))
        else:
            i += 1
    return runs


def _is_jp_codepoint(cp):
    return (0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF or 0x4E00 <= cp <= 0x9FFF
            or 0xFF00 <= cp <= 0xFFEF or 0x3000 <= cp <= 0x303F)


def _find_utf16_runs(data, min_run):
    """Rangkaian code point Jepang (UTF-16LE) berurutan >= min_run. Balikin [(start, end, text)]."""
    runs, n, i = [], len(data), 0
    while i < n - 1:
        cp = data[i] | (data[i + 1] << 8)
        if _is_jp_codepoint(cp):
            start, chars = i, []
            while i < n - 1:
                cp2 = data[i] | (data[i + 1] << 8)
                if _is_jp_codepoint(cp2):
                    chars.append(chr(cp2))
                    i += 2
                else:
                    break
            if len(chars) >= min_run:
                runs.append((start, i, "".join(chars)))
        else:
            i += 1
    return runs


def cmd_scan(kind, dirs, out_path, min_run):
    label = "Shift-JIS" if kind == "sjis" else "UTF-16LE Jepang"
    limit = 20 if kind == "sjis" else 30
    report, total, with_text = [], 0, 0
    for scan_dir in dirs:
        if not os.path.isdir(scan_dir):
            print(f"!! Folder tidak ditemukan, skip: {scan_dir}")
            continue
        print(f"\nScanning folder: {scan_dir}")
        names = sorted(os.listdir(scan_dir))
        for idx, fname in enumerate(names, 1):
            fpath = os.path.join(scan_dir, fname)
            if not os.path.isfile(fpath):
                continue
            total += 1
            data = Path(fpath).read_bytes()
            if kind == "sjis":
                snippets = []
                for start, _end, raw in _find_sjis_runs(data, min_run):
                    try:
                        text = raw.decode("shift_jis")
                    except UnicodeDecodeError:
                        continue
                    if text.strip():
                        snippets.append((start, text))
            else:
                snippets = [(s, t) for s, _e, t in _find_utf16_runs(data, min_run)]
            if not snippets:
                continue
            with_text += 1
            report += [f"\n{'=' * 70}", f"FILE: {fpath}", f"Jumlah kandidat teks: {len(snippets)}"]
            report += [f"  [offset 0x{s:X}] {t}" for s, t in snippets[:limit]]
            if len(snippets) > limit:
                report.append(f"  ... dan {len(snippets) - limit} lainnya")
            if idx % 200 == 0:
                print(f"  ... {idx}/{len(names)} file diproses")
    print(f"\n{'=' * 70}\nSELESAI. Total file di-scan: {total}")
    print(f"File yang mengandung kandidat teks {label}: {with_text}")
    print(f"Laporan lengkap disimpan di: {out_path}")
    Path(out_path).write_text(f"Total file di-scan: {total}\nFile dengan kandidat teks {label}: {with_text}\n"
                              + "\n".join(report), encoding="utf-8")


# ---------------------------------------------------------------- find (dulu find_exact_bytes)
def cmd_find(needle, paths):
    if needle.startswith("hex:"):
        pats = {"hex": bytes.fromhex(needle[4:])}
    else:
        pats = {"UTF-16LE": needle.encode("utf-16-le"), "UTF-8": needle.encode("utf-8")}
        try:
            pats["Shift-JIS"] = needle.encode("shift_jis")
        except UnicodeEncodeError:
            pass
    print("Pola yang dicari:")
    for label, pat in pats.items():
        print(f"  {label}: {pat.hex(' ').upper()}")
    print()
    total = 0

    def scan_file(fpath, shown):
        nonlocal total
        data = Path(fpath).read_bytes()
        for label, pat in pats.items():
            idx = data.find(pat)
            if idx != -1:
                total += 1
                print(f"  KETEMU di {shown}: {label} @ offset {idx} (0x{idx:X})")

    for path in paths:
        if os.path.isdir(path):
            print(f"Scanning: {path}")
            for fname in sorted(os.listdir(path)):
                fp = os.path.join(path, fname)
                if os.path.isfile(fp):
                    scan_file(fp, fname)
        elif os.path.isfile(path):
            print(f"Scanning file: {path} (file besar bisa lama)")
            scan_file(path, path)
        else:
            print(f"!! Tidak ditemukan, skip: {path}")
    print("\n" + "=" * 60)
    if total == 0:
        print("TIDAK ADA yang ketemu sama sekali.")
        print("Kesimpulan: teks di file storage BUKAN UTF-16LE/Shift-JIS/UTF-8 mentah (atau pola hex salah).")
    else:
        print(f"Total {total} kecocokan ditemukan. Lihat detail di atas.")


# ---------------------------------------------------------------- text (dulu verify_text)
def _is_jp_or_common(cp):
    return (0x3000 <= cp <= 0x303F or 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF
            or 0x4E00 <= cp <= 0x9FFF or 0xFF00 <= cp <= 0xFFEF or cp == 0x0000)


def cmd_text(path, center, before=100, after=400):
    with open(path, "rb") as f:
        f.seek(max(0, center - before))
        data = f.read(before + after)
    print("=" * 70 + "\nRAW HEX (untuk verifikasi manual):\n" + "=" * 70)
    for i in range(0, min(len(data), 200), 16):
        print(f"  +0x{i:04X}: " + " ".join(f"{b:02X}" for b in data[i:i + 16]))
    print("\n" + "=" * 70 + "\nDECODE SEBAGAI UTF-16LE (skip kalau error):\n" + "=" * 70)
    chars, i = [], 0
    while i < len(data) - 1:
        cp = data[i] | (data[i + 1] << 8)
        if _is_jp_or_common(cp) or (0x20 <= cp <= 0x7E):
            chars.append("\u2400" if cp == 0 else chr(cp))
        else:
            chars.append(f"[{cp:04X}]")
        i += 2
    print("".join(chars))


# ---------------------------------------------------------------- gpda-entry (dulu find_gpda_entry)
def _parse_seekmap_text(path):
    """Pakai parser tunggal seekmap_rebuild.parse_seekmap. Balikin [(nama, offset, size, crc)]."""
    raw = gzip.decompress(Path(path).read_bytes())
    return [(sm.rec_name(r).decode("latin1"), r.off, r.size, r.crc) for r in sm.parse_seekmap(raw)]


def cmd_gpda_entry(res_path, seekmap_path, hint, scan_mb=4):
    size_scan = scan_mb * 1024 * 1024
    print(f"Membaca {size_scan} byte pertama RES.DAT...")
    with open(res_path, "rb") as f:
        header = f.read(size_scan)
    print("Parsing first.dat (seekmap)...")
    entries = _parse_seekmap_text(seekmap_path)
    print(f"Total entries di first.dat: {len(entries)}")
    matches = [e for e in entries if hint in e[0]]
    print(f"\nEntries yang cocok dengan '{hint}': {len(matches)}")
    for name, offset, size, checksum in matches[:10]:
        print(f"  name={name!r}  offset={offset}  size={size}  checksum={checksum}")
    if not matches:
        print("Ganti nama_hint, tidak ada yang cocok.")
        return
    for name, offset, size, checksum in matches:
        idx_offset = header.find(struct.pack("<I", offset))
        idx_size = header.find(struct.pack("<I", size))
        print(f"\n=== {name} (offset={offset}, size={size}, checksum={checksum}) ===")
        print(f"  cari offset {offset} (0x{offset:X}) sbg 4-byte LE -> ketemu di header@ "
              f"{idx_offset if idx_offset != -1 else 'TIDAK KETEMU'}")
        print(f"  cari size   {size} sbg 4-byte LE -> ketemu di header@ {idx_size if idx_size != -1 else 'TIDAK KETEMU'}")
        if idx_offset != -1:
            start, end = max(0, idx_offset - 16), min(len(header), idx_offset + 32)
            chunk = header[start:end]
            print(f"  hexdump sekitar offset field (header@ {start:#x} .. {end:#x}):")
            for i in range(0, len(chunk), 16):
                mark = ">>" if start + i <= idx_offset < start + i + 16 else "  "
                print(f"    {mark} {start + i:#06x}: " + " ".join(f"{b:02x}" for b in chunk[i:i + 16]))
        if idx_size != -1 and idx_size != idx_offset and idx_offset != -1:
            print(f"  jarak offset_field -> size_field: {idx_size - idx_offset} byte")


# ---------------------------------------------------------------- seekmap-pos (dulu locate_seekmap_in_resdat)
def cmd_seekmap_pos(seekmap_path, res_path):
    sm = Path(seekmap_path).read_bytes()
    print(f"seekmap.dat size: {len(sm)} bytes")
    print(f"seekmap.dat 16 byte pertama (hex): {sm[:16].hex(' ')}")
    print(f"seekmap.dat ini gzip? {sm[:2] == bytes.fromhex('1f8b')}\n")
    print(f"RES.DAT size: {os.path.getsize(res_path)} bytes")
    with open(res_path, "rb") as f:
        head = f.read(64)
    print(f"RES.DAT 64 byte pertama (hex):\n  {head.hex(' ')}")
    print(f"RES.DAT ini gzip juga? {head[:2] == bytes.fromhex('1f8b')}\n")
    print("Scanning RES.DAT untuk mencari byte seekmap.dat persis di dalamnya...\n(ini bisa agak lama karena filenya 400+ MB)")
    chunk_size, overlap, found, pos, tail = 64 * 1024 * 1024, len(sm), None, 0, b""
    with open(res_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            area = tail + chunk
            idx = area.find(sm)
            if idx != -1:
                found = pos - len(tail) + idx
                break
            tail = chunk[-overlap:] if len(chunk) >= overlap else chunk
            pos += len(chunk)
    if found is not None:
        print(f"\n>>> KETEMU! seekmap.dat ada persis di RES.DAT pada offset {found} (0x{found:X})")
        print(f">>> Artinya seekmap.dat = RES.DAT[{found}:{found + len(sm)}]")
    else:
        print("\n>>> TIDAK ketemu persis sebagai substring di RES.DAT.")
        print(">>> Kemungkinan: seekmap.dat sudah dimodifikasi manual dulu (bukan raw carve),")
        print(">>> atau memang benar-benar file terpisah dari sumber lain (RAM dump, dll).")
        print(">>> Coba juga cocokkan cuma gzip header pertamanya saja (2 byte 1f 8b) ada berapa")
        print(">>> kali muncul di 1MB pertama RES.DAT, untuk cross-check manual:")
        with open(res_path, "rb") as f:
            first_mb = f.read(1024 * 1024)
        print(f">>> jumlah '1f 8b' (gzip magic) di 1MB pertama RES.DAT: {first_mb.count(bytes.fromhex('1f8b'))}")


# ---------------------------------------------------------------- opcodes (dulu jumpscan.py)
SAMPLES_PER_OP = 4
MAX_SAMPLE_BYTES = 96


def _iter_scenes(res_path):
    script = _script_container(res_path)
    for i, nm in enumerate(script.names):
        name = nm.strip().lstrip("_").rsplit(".dat", 1)[0]
        try:
            yield name, _scene_obj(script, i)
        except Exception as e:                       # noqa: BLE001
            print(f"lewati {name}: {e}")


def opcode_summary(scenes):
    """scenes: iterable of (name, data). Balikin (stats, samples, fails)."""
    stats = collections.OrderedDict()
    samples = collections.defaultdict(list)
    fails = []
    for name, data in scenes:
        try:
            count, _first, insts = parse_instructions(data)
        except Exception as e:                       # noqa: BLE001
            fails.append((name, str(e)))
            continue
        for k, (pos, size, op) in enumerate(insts):
            st = stats.setdefault(op, {"n": 0, "sizes": collections.Counter(), "scenes": set()})
            st["n"] += 1
            st["sizes"][size] += 1
            st["scenes"].add(name)
            sm_ = samples[op]
            if len(sm_) < SAMPLES_PER_OP and size not in {s[3] for s in sm_}:
                sm_.append((name, k, count, size, data[pos:pos + min(size, MAX_SAMPLE_BYTES)]))
    return stats, samples, fails


def opcode_render(stats, samples, fails):
    out = ["OPCODE  jumlah  scene  ukuran(terbanyak)"]
    for op in sorted(stats):
        st = stats[op]
        top = ", ".join(f"{s}x{c}" for s, c in st["sizes"].most_common(4))
        out.append(f"{op:>6}  {st['n']:>6}  {len(st['scenes']):>5}  {top}")
    out.append("")
    for op in sorted(stats):
        out.append(f"=== opcode {op} ===")
        for name, k, count, size, raw in samples[op]:
            out.append(f"scene={name} inst#{k}/{count} size={size}")
            for o in range(0, len(raw), 16):
                out.append(f"  {o:04x}  {raw[o:o + 16].hex(' ')}")
        out.append("")
    if fails:
        out.append(f"scene gagal parse: {len(fails)}")
        for n, e in fails[:20]:
            out.append(f"  {n}: {e}")
    return "\n".join(out)


def cmd_opcodes(res_path, out_path="jumpscan.txt"):
    stats, samples, fails = opcode_summary(_iter_scenes(res_path))
    text = opcode_render(stats, samples, fails)
    Path(out_path).write_text(text, encoding="utf-8")
    print("\n".join(text.splitlines()[: len(stats) + 1]))
    print(f"\nditulis: {out_path} ({len(text.splitlines())} baris); scene gagal parse: {len(fails)}")


def _opt(a, flag, default, cast=str):
    """Ambil '--flag val' dari list a (in-place). Balikin nilai (atau default)."""
    if flag in a:
        k = a.index(flag)
        val = cast(a[k + 1])
        del a[k:k + 2]
        return val
    return default


def main(a):
    a = list(a)
    c = a[0] if a else ""
    if c == "tree" and len(a) >= 2:
        pl._tree_cli(a[1:])
    elif c == "entry" and len(a) in (2, 4):
        cmd_entry(*a[1:])
    elif c == "obj" and len(a) == 4:
        cmd_obj(a[1], a[2], a[3])
    elif c == "inst" and len(a) >= 4:
        cmd_inst(a[1], a[2], [int(x) for x in a[3:]])
    elif c == "hex" and len(a) >= 4:
        cmd_hex(a[1], a[2], a[3:])
    elif c == "scan" and len(a) >= 3 and a[1] in ("sjis", "utf16"):
        out = _opt(a, "--out", f"{'shiftjis' if a[1] == 'sjis' else 'utf16'}_report.txt")
        mn = _opt(a, "--min", 3 if a[1] == "sjis" else 2, int)
        cmd_scan(a[1], a[2:], out, mn)
    elif c == "find" and len(a) >= 3:
        cmd_find(a[1], a[2:])
    elif c == "text" and len(a) >= 3:
        bf, af = _opt(a, "--before", 100, int), _opt(a, "--after", 400, int)
        cmd_text(a[1], int(a[2], 16), bf, af)
    elif c == "gpda-entry" and len(a) >= 4:
        mb = _opt(a, "--scan-mb", 4, int)
        cmd_gpda_entry(a[1], a[2], a[3], mb)
    elif c == "seekmap-pos" and len(a) == 3:
        cmd_seekmap_pos(a[1], a[2])
    elif c == "opcodes" and len(a) >= 2:
        out = _opt(a, "--out", "jumpscan.txt")
        cmd_opcodes(a[1], out)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
