"""
pipeline.py  --  SATU file untuk build patch teks Inggris Haganai Portable (RES.DAT -> RES.DAT baru).
(gabungan gpda_v2.py + choice_patch.py + full_pipeline.py + full_pipeline_v3.py + full_pipeline_v6.py;
 v4/v5 sudah tercakup v6.  Logika TIDAK diubah, hanya dijadikan satu modul.)

Isi file ini:
  1. GPDAContainer      -- parser/rebuilder container GPDA (RES.DAT, script.dat, dst; name table & padding 2048 dijaga)
  2. parse_instructions / verify_objbin -- parser instruksi .obj.bin + pengecekan struktur (16-aligned, urutan opcode)
  3. rewrite_dialog_instruction   (opcode 100, dialog ber-speaker, kunci: file + offset)
     rewrite_narration_instruction(opcode 100, narasi tanpa speaker,  kunci: scene + inst_index)
     rewrite_choice_instruction   (opcode 103, choice/menu,           kunci: scene + inst_index + str_index)
  4. wrap/pad teks (lebar kolom: ASCII=1, U+2019=--apos-w, non-ASCII lain=2) + build penuh (run)

Pakai (build):
    python pipeline.py --verify-only <RES.DAT> <dialogue.csv> <remaining.csv> [opsi]
    python pipeline.py <RES.DAT> <dialogue.csv> <remaining.csv> <output.DAT> [opsi]
Opsi:
    --width N     lebar wrap dialog ber-speaker (default 37 = 39 kolom - 2 indent kurung)
    --nwidth N    lebar wrap narasi tanpa speaker (default 39).  --width 0 mematikan wrap (kecuali --nwidth diisi)
    --apos X      pengganti apostrof ASCII (default U+2019).  --apos "'" = pakai apostrof biasa
    --apos-w F    lebar kolom U+2019 (default 1.5)
    --max-lines N batas baris (default 3); teks yang lebih dicatat di --overflow (default overflow.csv)
    --report f.csv  laporan skip
Setelah build WAJIB rebuild seekmap/first.dat:
    python seekmap_rebuild.py build <output.DAT> <first.dat> <first_baru.dat>

Pakai (lihat struktur container GPDA, semua level nested):
    python pipeline.py tree <file> [--report out.txt] [--max-depth 4]
    (sama dengan "python dump.py tree ...")

Struktur data (hasil reverse-engineering):
    RES.DAT (GPDA) -> script.dat (GPDA, 674 entri) -> "_<stem>.dat" (GPDA) -> entri 0 (GPDA) -> "*.obj.gz" -> .obj.bin
    Instruksi dialog (opcode 100):  +0 u32 size (kelipatan 16) | +4 u16 opcode | +11 u16 length_field | +13 pad 2 |
        +15 speaker_field (variabel) | teks UTF-16LE (dialog dibungkus 「...」) + 00 00 | nol sampai size
    Pengaman: file yang gagal parse/verify TIDAK dipatch (JP asli utuh) dan alasannya masuk laporan skip.
"""
import csv
import gzip
import struct
import sys
import time
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path



# ===========================================================================
# 1. GPDA container
# ===========================================================================

GPDA_ALIGN = 2048


def _round_up(value: int, align: int = GPDA_ALIGN) -> int:
    return ((value + align - 1) // align) * align


class GPDAContainer:
    def __init__(self, data: bytes, count: int, entries: list,
                 names: list, header_and_toc_size: int, name_table_end: int,
                 total_size: int):
        self.data = data
        self.count = count
        # entries[i] = (data_offset, size, name_offset)
        self.entries = entries
        self.names = names
        self.header_and_toc_size = header_and_toc_size
        self.name_table_end = name_table_end
        self.total_size = total_size

    # ------------------------------------------------------------------
    @classmethod
    def parse(cls, data: bytes) -> "GPDAContainer":
        magic, total_size, reserved, count = struct.unpack_from("<4sIII", data, 0)
        if magic != b"GPDA":
            raise ValueError(f"Bukan container GPDA (magic={magic!r})")

        entries = []
        for i in range(count):
            off = 16 + i * 16
            data_offset, _reserved2, size, name_offset = struct.unpack_from("<IIII", data, off)
            entries.append((data_offset, size, name_offset))

        header_and_toc_size = 16 + count * 16

        names = []
        name_table_end = header_and_toc_size
        for (_off, _size, name_offset) in entries:
            length = struct.unpack_from("<I", data, name_offset)[0]
            text = data[name_offset + 4: name_offset + 4 + length].decode("ascii")
            names.append(text)
            name_table_end = max(name_table_end, name_offset + 4 + length)

        return cls(data, count, entries, names, header_and_toc_size,
                   name_table_end, total_size)

    # ------------------------------------------------------------------
    def entry_bytes(self, i: int) -> bytes:
        off, size, _name_offset = self.entries[i]
        return self.data[off:off + size]

    # ------------------------------------------------------------------
    def rebuild(self, replacements: dict) -> bytes:
        """Bikin ulang container ini sebagai bytes baru.

        replacements: dict {index_entri: bytes_baru}. Entri yang tidak
        disebut di sini dipertahankan persis dari data asli (byte-for-byte).
        Name table SELALU disalin apa adanya (nama entri tidak pernah
        berubah). Ukuran & offset di header/TOC dihitung ulang otomatis
        mengikuti alignment 2048, sama seperti file asli -- SEMUA entri
        (termasuk yang terakhir) di-pad ke kelipatan 2048.
        """
        new_sizes = []
        for i in range(self.count):
            if i in replacements:
                new_sizes.append(len(replacements[i]))
            else:
                new_sizes.append(self.entries[i][1])

        first_offset = _round_up(self.name_table_end)

        new_offsets = []
        cur = first_offset
        for i in range(self.count):
            new_offsets.append(cur)
            end = cur + new_sizes[i]
            # FIX: round up SETIAP entri, termasuk yang terakhir -- tidak
            # ada pengecualian. Ini beda utama dari versi lama.
            cur = _round_up(end)
        new_total_size = cur

        out = bytearray()
        out += struct.pack("<4sIII", b"GPDA", new_total_size, 0, self.count)

        for i in range(self.count):
            _old_off, _old_size, name_offset = self.entries[i]
            out += struct.pack("<IIII", new_offsets[i], 0, new_sizes[i], name_offset)

        # name table disalin apa adanya
        out += self.data[self.header_and_toc_size:self.name_table_end]

        # padding nol dari akhir name table sampai first_offset entri pertama
        pad_len = first_offset - len(out)
        if pad_len < 0:
            raise ValueError("Name table lebih besar dari first_offset -- tidak seharusnya terjadi")
        out += b"\x00" * pad_len

        assert len(out) == first_offset

        for i in range(self.count):
            assert len(out) == new_offsets[i], (
                f"Offset entri {i} meleset: len(out)={len(out)}, expected={new_offsets[i]}"
            )
            if i in replacements:
                entry_data = replacements[i]
            else:
                old_off, old_size, _ = self.entries[i]
                entry_data = self.data[old_off:old_off + old_size]
            out += entry_data

            # FIX: padding sampai kelipatan 2048 berikutnya, SELALU --
            # termasuk untuk i == self.count - 1 (entri terakhir).
            end = new_offsets[i] + new_sizes[i]
            next_boundary = _round_up(end)
            out += b"\x00" * (next_boundary - end)

        assert len(out) == new_total_size, (
            f"Total ukuran meleset: len(out)={len(out)}, expected={new_total_size}"
        )

        return bytes(out)


# ===========================================================================
# 2. Instruksi .obj.bin: konstanta, parser, verifikasi, patch dialog (opcode 100)
# ===========================================================================

MARKER = bytes([0x00, 0x00, 0x00, 0x64, 0x00, 0x00])
TERMINATOR = b"\x00\x00"
SEARCH_WINDOW = 80
MAX_SANE_SPEAKER_FIELD = 40
DIALOG_OPCODE = 100
ALIGN = 16


def ceil16(n: int) -> int:
    return (n + ALIGN - 1) // ALIGN * ALIGN


# ---------------------------------------------------------------------------
# Bagian 0: parser instruksi .obj.bin + verifikasi
# ---------------------------------------------------------------------------

def parse_instructions(data: bytes):
    """Balikin (count, first_offset, [(pos, size, opcode), ...]).
    Raise ValueError kalau penelusuran tidak konsisten."""
    if len(data) < 8:
        raise ValueError("file terlalu kecil")
    count, first = struct.unpack_from("<II", data, 0)
    if first < 8 or first > len(data):
        raise ValueError(f"offset instruksi pertama tidak masuk akal ({first:#x})")
    insts = []
    pos = first
    for n in range(count):
        if pos + 6 > len(data):
            raise ValueError(f"instruksi #{n} keluar dari file (pos={pos:#x})")
        size = struct.unpack_from("<I", data, pos)[0]
        if size < 6 or pos + size > len(data):
            raise ValueError(f"ukuran instruksi #{n} tidak valid ({size}) @ {pos:#x}")
        opcode = struct.unpack_from("<H", data, pos + 4)[0]
        insts.append((pos, size, opcode))
        pos += size
    if pos != len(data):
        raise ValueError(f"penelusuran berakhir di {pos:#x}, bukan di akhir file {len(data):#x}")
    return count, first, insts


def _is_aligned(insts):
    return all(p % ALIGN == 0 and s % ALIGN == 0 for p, s, _ in insts)


def verify_objbin(orig: bytes, new: bytes):
    """Raise ValueError kalau struktur hasil patch tidak konsisten."""
    c0, f0, i0 = parse_instructions(orig)
    c1, f1, i1 = parse_instructions(new)
    if c0 != c1:
        raise ValueError(f"jumlah instruksi berubah {c0} -> {c1}")
    if f0 != f1 or orig[:f0] != new[:f1]:
        raise ValueError("header berubah")
    if [o for _, _, o in i0] != [o for _, _, o in i1]:
        raise ValueError("urutan opcode berubah")
    if not _is_aligned(i1):
        raise ValueError("ada instruksi yang tidak 16-aligned")


# ---------------------------------------------------------------------------
# Bagian 1: patch teks di dalam SATU instruksi dialog
# ---------------------------------------------------------------------------

def decode_utf16le_until_null(data: bytes, pos: int, max_len: int = 4000):
    end = pos
    while end + 1 < len(data) and end - pos < max_len * 2:
        if data[end:end + 2] == TERMINATOR:
            return data[pos:end].decode("utf-16-le"), end + 2
        end += 2
    raise ValueError(f"No terminator found from {pos:#x}")


def rewrite_dialog_instruction(inst: bytes, rel_text_offset: int, english: str):
    """inst = bytes 1 instruksi dialog ASLI. Balikin (new_inst, None) atau (None, alasan)."""
    # Posisi tetap relatif awal instruksi (Rekap §13.2): opcode u16 @+4 (=100, byte 64 00),
    # length-field u16 @+11, padding 2 byte @+13, speaker_field mulai @+15.
    # JANGAN cari marker 00 00 00 64 00 00 dari +1: untuk instruksi >= 256 byte,
    # byte +1 bukan nol (prefix ukuran u32) sehingga marker tidak cocok.
    length_field_pos = 11
    speaker_field_start = 15
    if inst[4:7] != b"\x64\x00\x00":
        return None, "opcode/marker dialog tidak ada di +4 (format beda, mis. ruby-text)"
    speaker_len = rel_text_offset - speaker_field_start
    if speaker_len < 0 or speaker_len > MAX_SANE_SPEAKER_FIELD or speaker_len % 2:
        return None, f"lebar speaker field tidak masuk akal ({speaker_len} byte)"

    try:
        orig_text, orig_text_end = decode_utf16le_until_null(inst, rel_text_offset)
    except ValueError as e:
        return None, f"gagal decode teks asli: {e}"

    speaker_field = inst[speaker_field_start:rel_text_offset]
    length_field = struct.unpack_from("<H", inst, length_field_pos)[0]
    expected_len = len(orig_text) + len(speaker_field) // 2
    if length_field != expected_len:
        return None, f"header mismatch (field={length_field}, expected={expected_len})"

    if any(inst[orig_text_end:]):
        return None, "ada data non-nol setelah teks dalam instruksi (lebih dari satu teks?)"

    old_size = struct.unpack_from("<I", inst, 0)[0]
    c_old = len(inst.rstrip(b"\x00"))
    if old_size != len(inst) or len(inst) != ceil16(c_old + 5):
        return None, (f"aturan padding ceil16(c+5) tidak cocok di instruksi asli "
                      f"(size={len(inst)}, c={c_old})")

    new_text = f"「{english}」"
    new_text_bytes = new_text.encode("utf-16-le") + TERMINATOR
    new_length_field = len(new_text) + len(speaker_field) // 2

    body = bytearray(inst[:length_field_pos])
    body += struct.pack("<H", new_length_field)
    body += b"\x00\x00"
    body += speaker_field
    body += new_text_bytes

    c_new = len(bytes(body).rstrip(b"\x00"))
    new_size = ceil16(c_new + 5)
    body += b"\x00" * (new_size - len(body))
    struct.pack_into("<I", body, 0, new_size)
    return bytes(body), None


# ---------------------------------------------------------------------------
# Bagian 1b: patch satu obj.bin penuh (in-memory)
# ---------------------------------------------------------------------------

def patch_objbin_bytes(data: bytes, rows: list):
    """Balikin (new_bytes, patched_count, skipped_list[(offset, alasan)]).
    Kalau file gagal parse/verify -> (data asli, 0, semua baris di-skip)."""
    rows = sorted(rows, key=lambda r: int(r["offset"], 16))

    def skip_all(reason):
        return data, 0, [(int(r["offset"], 16), reason) for r in rows]

    try:
        count, first, insts = parse_instructions(data)
        if not _is_aligned(insts):
            raise ValueError("instruksi asli tidak 16-aligned (aturan padding belum terbukti di file ini)")
    except ValueError as e:
        return skip_all(f"struktur instruksi asli tidak valid: {e}")

    starts = [p for p, _, _ in insts]
    skipped = []
    new_insts = {}  # index instruksi -> bytes baru

    for row in rows:
        off = int(row["offset"], 16)
        idx = bisect_right(starts, off) - 1
        if idx < 0:
            skipped.append((off, "offset sebelum instruksi pertama"))
            continue
        pos, size, opcode = insts[idx]
        if off >= pos + size:
            skipped.append((off, "offset di luar instruksi manapun"))
            continue
        if opcode != DIALOG_OPCODE:
            skipped.append((off, f"instruksi bukan dialog (opcode {opcode})"))
            continue
        if idx in new_insts:
            skipped.append((off, "lebih dari satu baris CSV di satu instruksi"))
            continue

        english = (row.get("english_text") or "").strip().strip('"')
        if not english:
            skipped.append((off, "english_text kosong"))
            continue

        new_inst, reason = rewrite_dialog_instruction(data[pos:pos + size], off - pos, english)
        if new_inst is None:
            skipped.append((off, reason))
            continue
        new_insts[idx] = new_inst

    if not new_insts:
        return data, 0, skipped

    out = bytearray(data[:first])
    for i, (pos, size, _) in enumerate(insts):
        out += new_insts.get(i, data[pos:pos + size])
    new_bytes = bytes(out)

    try:
        verify_objbin(data, new_bytes)
    except ValueError as e:
        return skip_all(f"verify_objbin gagal, file TIDAK dipatch: {e}")

    return new_bytes, len(new_insts), skipped


# ===========================================================================
# 3. Narasi tanpa speaker (opcode 100)
# ===========================================================================

def read_dialog_string(inst: bytes):
    """Balikin (full_string_dari_+15, end_pos) atau raise ValueError."""
    if inst[4:7] != b"\x64\x00\x00":
        raise ValueError("opcode/marker dialog tidak ada di +4")
    return decode_utf16le_until_null(inst, 15)


def rewrite_narration_instruction(inst: bytes, jp_text: str, english: str):
    """Balikin (new_inst, None) atau (None, alasan)."""
    try:
        full, end_pos = read_dialog_string(inst)
    except ValueError as e:
        return None, f"gagal decode instruksi asli: {e}"

    length_field = struct.unpack_from("<H", inst, 11)[0]
    if length_field != len(full):
        return None, f"header mismatch (field={length_field}, len={len(full)})"

    if any(inst[end_pos:]):
        return None, "ada data non-nol setelah teks dalam instruksi (lebih dari satu teks?)"

    if not full.endswith(jp_text):
        return None, "teks Jepang di instruksi tidak sama dengan jp_text CSV"
    speaker_chars = len(full) - len(jp_text)
    if speaker_chars * 2 > MAX_SANE_SPEAKER_FIELD:
        return None, f"speaker field tidak masuk akal ({speaker_chars * 2} byte)"
    if speaker_chars:
        # bukan narasi polos (ada speaker) -> jangan disentuh, itu urusan CSV dialog
        return None, f"instruksi punya speaker field {speaker_chars * 2} byte (bukan narasi polos)"
    if jp_text.startswith("「"):
        return None, "teks asli ber-kurung 「 (dialog, bukan narasi)"

    old_size = struct.unpack_from("<I", inst, 0)[0]
    c_old = len(inst.rstrip(b"\x00"))
    if old_size != len(inst) or len(inst) != ceil16(c_old + 5):
        return None, (f"aturan padding ceil16(c+5) tidak cocok di instruksi asli "
                      f"(size={len(inst)}, c={c_old})")

    new_text_bytes = english.encode("utf-16-le") + TERMINATOR
    body = bytearray(inst[:11])
    body += struct.pack("<H", len(english))
    body += b"\x00\x00"
    body += new_text_bytes

    c_new = len(bytes(body).rstrip(b"\x00"))
    new_size = ceil16(c_new + 5)
    body += b"\x00" * (new_size - len(body))
    struct.pack_into("<I", body, 0, new_size)
    return bytes(body), None


# ---------------------------------------------------------------------------
# Patch satu .obj.bin dengan dua jenis baris
# ---------------------------------------------------------------------------

def _narration_matches(data, insts, idx, jp_text):
    if not (0 <= idx < len(insts)):
        return False
    pos, size, opcode = insts[idx]
    if opcode != DIALOG_OPCODE:
        return False
    try:
        full, _ = read_dialog_string(data[pos:pos + size])
    except ValueError:
        return False
    return full.endswith(jp_text)


def patch_objbin_combined(data: bytes, dialog_rows: list, narr_rows: list):
    """Balikin (new_bytes, patched_count, skipped[(label, alasan)]), label = offset hex / 'inst#N'."""
    def skip_all(reason):
        s = [(r["offset"], reason) for r in dialog_rows] + \
            [(f"inst#{r['inst_index']}", reason) for r in narr_rows]
        return data, 0, s

    try:
        count, first, insts = parse_instructions(data)
        if not _is_aligned(insts):
            raise ValueError("instruksi asli tidak 16-aligned")
    except ValueError as e:
        return skip_all(f"struktur instruksi asli tidak valid: {e}")

    starts = [p for p, _, _ in insts]
    skipped = []
    new_insts = {}

    # --- dialog (logika lama persis) ---
    for row in sorted(dialog_rows, key=lambda r: int(r["offset"], 16)):
        off = int(row["offset"], 16)
        idx = bisect_right(starts, off) - 1
        if idx < 0:
            skipped.append((hex(off), "offset sebelum instruksi pertama")); continue
        pos, size, opcode = insts[idx]
        if off >= pos + size:
            skipped.append((hex(off), "offset di luar instruksi manapun")); continue
        if opcode != DIALOG_OPCODE:
            skipped.append((hex(off), f"instruksi bukan dialog (opcode {opcode})")); continue
        if idx in new_insts:
            skipped.append((hex(off), "lebih dari satu baris CSV di satu instruksi")); continue
        english = (row.get("english_text") or "").strip().strip('"')
        if not english:
            skipped.append((hex(off), "english_text kosong")); continue
        new_inst, reason = rewrite_dialog_instruction(data[pos:pos + size], off - pos, english)
        if new_inst is None:
            skipped.append((hex(off), reason)); continue
        new_insts[idx] = new_inst

    # --- narasi (BARU) ---
    for row in narr_rows:
        label = f"inst#{row['inst_index']}"
        idx = int(row["inst_index"])
        jp = row["jp_text"]
        english = (row.get("english_text") or "").strip()
        if not english:
            skipped.append((label, "english_text kosong")); continue
        if idx in new_insts:
            skipped.append((label, "instruksi ini sudah dipatch dari CSV dialog")); continue
        if not (0 <= idx < len(insts)):
            skipped.append((label, f"inst_index di luar jumlah instruksi ({len(insts)})")); continue
        pos, size, opcode = insts[idx]
        if opcode != DIALOG_OPCODE:
            hint = ""
            for d in (-1, 1):
                if _narration_matches(data, insts, idx + d, jp):
                    hint = f" (teks cocok di inst_index {idx + d}: kemungkinan salah basis indeks)"
            skipped.append((label, f"instruksi bukan dialog (opcode {opcode}){hint}")); continue
        new_inst, reason = rewrite_narration_instruction(data[pos:pos + size], jp, english)
        if new_inst is None:
            if "tidak sama dengan jp_text" in reason:
                for d in (-1, 1):
                    if _narration_matches(data, insts, idx + d, jp):
                        reason += f" (cocok di inst_index {idx + d}: kemungkinan salah basis indeks)"
            skipped.append((label, reason)); continue
        new_insts[idx] = new_inst

    if not new_insts:
        return data, 0, skipped

    out = bytearray(data[:first])
    for i, (pos, size, _) in enumerate(insts):
        out += new_insts.get(i, data[pos:pos + size])
    new_bytes = bytes(out)
    try:
        verify_objbin(data, new_bytes)
    except ValueError as e:
        return skip_all(f"verify_objbin gagal, file TIDAK dipatch: {e}")
    return new_bytes, len(new_insts), skipped


# ===========================================================================
# 4. Choice/menu (opcode 103)
# ===========================================================================

def parse_choice(inst: bytes):
    """Balikin (header10, n_header, entries, body_end).
    entries = [(target, text, tail_bytes)] ; tail_bytes = flag(4) [+ ekstensi] persis seperti aslinya.
    Raise ValueError kalau struktur tidak dikenal."""
    if len(inst) < 10:
        raise ValueError("instruksi terlalu pendek")
    size, op, n, _z = struct.unpack_from("<IHHH", inst, 0)
    if op != 0x67:
        raise ValueError(f"bukan opcode 103 (op={op:#x})")
    if size != len(inst):
        raise ValueError(f"size field {size} != panjang {len(inst)}")
    pos, entries = 10, []

    def read_entry(pos):
        if pos + 8 > len(inst):
            raise ValueError("entri melewati akhir instruksi")
        target, ln = struct.unpack_from("<II", inst, pos)
        t0, t1 = pos + 8, pos + 8 + 2 * ln
        if t1 + 4 > len(inst):
            raise ValueError("teks melewati akhir instruksi")
        text = inst[t0:t1].decode("utf-16-le")
        flag = struct.unpack_from("<I", inst, t1)[0]
        end = t1 + 4
        if flag == 1:
            if end + 4 > len(inst):
                raise ValueError("ekstensi melewati akhir instruksi")
            cnt = struct.unpack_from("<I", inst, end)[0]
            end += 4 + 2 * cnt
            if cnt > 16 or end > len(inst):
                raise ValueError(f"ekstensi entri tidak masuk akal (count={cnt})")
        elif flag != 0:
            raise ValueError(f"flag entri tidak dikenal ({flag:#x}), bukan 0/1")
        return (target, text, inst[t1:end]), end

    for _ in range(n):
        e, pos = read_entry(pos)
        entries.append(e)
    # entri ekstra di luar n header (kasus a490ess1): lanjut selama masih ada data non-nol
    while any(inst[pos:]):
        e, pos = read_entry(pos)
        entries.append(e)
    return inst[:10], n, entries, pos


def rewrite_choice_instruction(inst: bytes, jp_list: list, en_list: list):
    """Balikin (new_inst, None) atau (None, alasan)."""
    try:
        header, n_hdr, entries, body_end = parse_choice(inst)
    except (ValueError, UnicodeDecodeError, struct.error) as e:
        return None, f"gagal parse choice asli: {e}"
    total = len(entries)
    if len(jp_list) not in (n_hdr, total) or len(jp_list) != len(en_list):
        return None, f"jumlah pilihan beda (instruksi={n_hdr}, entri nyata={total}, CSV={len(jp_list)})"
    k = len(jp_list)  # banyaknya entri yang dipatch (sisanya disalin utuh)
    for i, ((_, txt, _), jp) in enumerate(zip(entries[:k], jp_list)):
        if txt != jp:
            return None, f"teks Jepang pilihan #{i} tidak sama dengan jp_text CSV"
    if len(inst) not in (ceil16(body_end), ceil16(body_end + 1)):
        return None, f"aturan padding tidak cocok di instruksi asli (size={len(inst)}, end={body_end})"
    if any(not e.strip() for e in en_list):
        return None, "ada english_text kosong"

    body = bytearray(header)
    for i, (target, jp, tail) in enumerate(entries):
        txt = en_list[i] if i < k else jp
        body += struct.pack("<II", target, len(txt)) + txt.encode("utf-16-le") + tail
    new_size = ceil16(len(body) + 1)
    body += b"\x00" * (new_size - len(body))
    struct.pack_into("<I", body, 0, new_size)
    return bytes(body), None


# ===========================================================================
# 5. Wrap teks + build penuh
# ===========================================================================

def clean_en(s, apos):
    return (s or "").replace("\r\n", " ").replace("\n", " ").replace("'", apos).strip()


DEFAULT_WIDTH = 37    # dialog dengan pembicara: 39 kolom - indent 2 untuk tanda kurung
DEFAULT_NWIDTH = 39   # narasi tanpa pembicara (hasil ruler: 39 karakter ASCII per baris)
MAX_LINES = 3
APOS_W = 1.5          # lebar kolom U+2019 (terukur ~1.5 dari ruler test)
OTHER_W = 2.0         # lebar kolom karakter non-ASCII lain (perkiraan)
OVERFLOW_PATH = "overflow.csv"
OVERFLOW = []         # (sumber, kunci, jumlah_baris, teks)


def cw(s):
    """Lebar dalam SETENGAH kolom (ASCII = 2 unit)."""
    t = 0
    for c in s:
        if ord(c) < 128:
            t += 2
        elif c == "\u2019":
            t += int(round(APOS_W * 2))
        else:
            t += int(round(OTHER_W * 2))
    return t


def wrap_lines(s, W):
    """Pecah per kata; W dalam kolom (dibandingkan dalam setengah kolom). Balikin list baris."""
    lim, lines, cur = int(W * 2), [], ""
    for w in s.split():
        while cw(w) > lim:                      # kata lebih panjang dari satu baris: potong
            if cur:
                lines.append(cur); cur = ""
            k, acc = 0, 0
            while k < len(w) and acc + cw(w[k]) <= lim:
                acc += cw(w[k]); k += 1
            lines.append(w[:k]); w = w[k:]
        if not cur:
            cur = w
        elif cw(cur) + 2 + cw(w) <= lim:        # +2 = satu spasi (1 kolom)
            cur += " " + w
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def wrap_pad(s, W):
    """Isi tiap baris (kecuali terakhir) dengan spasi sampai W kolom (sisa setengah kolom dibuang).
    W harus sama dengan kapasitas asli kotak; W<=0 -> tidak di-wrap."""
    if not W or W <= 0:
        return s
    lines = wrap_lines(s, W)
    if not lines:
        return ""
    lim = int(W * 2)
    return "".join(l + " " * ((lim - cw(l)) // 2) for l in lines[:-1]) + lines[-1]


def note_overflow(src, key, text, W):
    if W and W > 0:
        n = len(wrap_lines(text, W))
        if n > MAX_LINES:
            OVERFLOW.append((src, key, n, text))


def patch_choices(orig, cur, groups):
    """cur = bytes setelah patch dialog/narasi; groups = {inst_index: [rows urut str_index]}."""
    skipped = []

    def skip_all(reason):
        return cur, 0, [(f"inst#{i}", reason) for i in groups]

    try:
        _, first, insts = parse_instructions(cur)
        if not _is_aligned(insts):
            raise ValueError("instruksi tidak 16-aligned")
    except ValueError as e:
        return skip_all(f"struktur instruksi tidak valid: {e}")
    new = {}
    for idx, rows in groups.items():
        label = f"inst#{idx}"
        if not (0 <= idx < len(insts)):
            skipped.append((label, f"inst_index di luar jumlah instruksi ({len(insts)})")); continue
        pos, size, op = insts[idx]
        if op != 103:
            skipped.append((label, f"instruksi bukan choice (opcode {op})")); continue
        if [int(r["str_index"]) for r in rows] != list(range(len(rows))):
            skipped.append((label, "str_index tidak berurutan 0..n-1")); continue
        ni, reason = rewrite_choice_instruction(
            cur[pos:pos + size], [r["jp_text"] for r in rows], [r["english_text"] for r in rows])
        if ni is None:
            skipped.append((label, reason)); continue
        new[idx] = ni
    if not new:
        return cur, 0, skipped
    out = bytearray(cur[:first])
    for i, (pos, size, _) in enumerate(insts):
        out += new.get(i, cur[pos:pos + size])
    out = bytes(out)
    try:
        verify_objbin(orig, out)
    except ValueError as e:
        return skip_all(f"verify_objbin gagal, choice file ini TIDAK dipatch: {e}")
    return out, len(new), skipped


def patch_one_script_entry(mid_bytes, d_rows, n_rows, c_groups):
    if not d_rows and not n_rows and not c_groups:
        return None, 0, []
    mid = GPDAContainer.parse(mid_bytes)
    inner = GPDAContainer.parse(mid.entry_bytes(0))
    gz_idx = next((j for j, nm in enumerate(inner.names) if ".obj.gz" in nm), None)
    if gz_idx is None:
        return None, 0, [("-", "tidak ketemu entri .obj.gz di dalam container")]
    orig = gzip.decompress(inner.entry_bytes(gz_idx))
    cur, n, skipped = patch_objbin_combined(orig, d_rows, n_rows)
    if c_groups:
        cur, nc, sk2 = patch_choices(orig, cur, c_groups)
        n += nc
        skipped = skipped + sk2
    if n == 0:
        return None, 0, skipped
    new_gz = gzip.compress(cur, compresslevel=9, mtime=0)
    new_inner = inner.rebuild({gz_idx: new_gz})
    return mid.rebuild({0: new_inner}), n, skipped


def run(resource_path, dialog_csv, narr_csv, out_path, apos, report_path=None, verify_only=False,
        width=DEFAULT_WIDTH, nwidth=DEFAULT_NWIDTH):
    t0 = time.time()
    print(f"[1/5] Membaca {resource_path} ...")
    res_data = Path(resource_path).read_bytes()
    res = GPDAContainer.parse(res_data)
    script_idx = next((i for i, nm in enumerate(res.names) if nm.strip() == "script.dat"), None)
    if script_idx is None:
        print("ERROR: tidak ketemu 'script.dat' di resource.dat"); sys.exit(1)
    script = GPDAContainer.parse(res.entry_bytes(script_idx))
    print(f"[2/5] script.dat: {len(script.entries)} entri, {time.time()-t0:.1f}s")

    print(f"[3/5] Mengelompokkan baris CSV (apostrof -> {apos!r}, lebar dialog = {width}, "
          f"lebar narasi = {nwidth}, apos-w = {APOS_W}) ...")
    dialog_by = defaultdict(list)
    with open(dialog_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            t = clean_en(row.get("english_text"), apos)
            note_overflow("dialog", f"{row['file'].split('___')[1]} {row['offset']}", t, width)
            row["english_text"] = wrap_pad(t, width)
            dialog_by[row["file"]].append(row)
    narr_by, choice_by, n_other = defaultdict(list), defaultdict(lambda: defaultdict(list)), defaultdict(int)
    with open(narr_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["english_text"] = clean_en(row.get("english_text"), apos)
            if row["kind"] == "narration/dialog":   # choice/menu TIDAK di-wrap/pad
                note_overflow("narasi", f"{row['scene'].strip()} inst{row['inst_index']}",
                              row["english_text"], nwidth)
                row["english_text"] = wrap_pad(row["english_text"], nwidth)
            sc = row["scene"].strip()
            if row["kind"] == "narration/dialog" and row["opcode"] == "100":
                narr_by[sc].append(row)
            elif row["kind"] == "choice/menu" and row["opcode"] == "103":
                choice_by[sc][int(row["inst_index"])].append(row)
            else:
                n_other[row["kind"]] += 1
    for g in choice_by.values():
        for rows in g.values():
            rows.sort(key=lambda r: int(r["str_index"]))
    n_ch = sum(len(r) for g in choice_by.values() for r in g.values())
    print(f"      dialog: {sum(map(len, dialog_by.values()))} | narasi: {sum(map(len, narr_by.values()))} "
          f"| choice: {n_ch} baris di {len(choice_by)} scene")
    for k, v in n_other.items():
        print(f"      (belum didukung, dilewati) {k}: {v} baris")
    if OVERFLOW:
        with open(OVERFLOW_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["sumber", "kunci", "jumlah_baris", "english_text"])
            w.writerows(sorted(OVERFLOW, key=lambda r: -r[2]))
        print(f"      !! {len(OVERFLOW)} teks lebih dari {MAX_LINES} baris (akan tembus kotak) -> {OVERFLOW_PATH}")

    print("[4/5] Patch tiap entri script.dat ...")
    repl, total, touched, skips, seen = {}, 0, 0, [], set()
    for i, name in enumerate(script.names):
        stem = name.strip().lstrip("_").rsplit(".dat", 1)[0]
        fname = f"resource.dat__script.dat___{stem}.dat___{stem}.dat___{stem}.obj.bin"
        d, n, c = dialog_by.get(fname, []), narr_by.get(stem, []), dict(choice_by.get(stem, {}))
        if n or c:
            seen.add(stem)
        if not (d or n or c):
            continue
        try:
            mid, cnt, sk = patch_one_script_entry(script.entry_bytes(i), d, n, c)
        except Exception as e:
            skips.append((stem, "-", f"EXCEPTION: {e!r}")); continue
        skips += [(stem, lab, r) for lab, r in sk]
        if mid is not None:
            repl[i] = mid; total += cnt; touched += 1
    for sc in sorted((set(narr_by) | set(choice_by)) - seen):
        skips.append((sc, "-", "scene tidak ada di script.dat"))
    print(f"      SELESAI: {touched} file, {total} instruksi dipatch, {len(skips)} skip, {time.time()-t0:.1f}s")
    cnt = defaultdict(int)
    for _, _, r in skips:
        cnt[r.split("(")[0].split(":")[0].strip()] += 1
    for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])[:10]:
        print(f"        {v:6d}  {k}")
    if report_path:
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["file_or_scene", "offset_or_inst", "reason"]); w.writerows(skips)
        print(f"      Laporan skip: {report_path}")
    if verify_only:
        print("\n--verify-only: berhenti di sini."); return
    print("[5/5] Rebuild script.dat lalu resource.dat ...")
    new_res = res.rebuild({script_idx: script.rebuild(repl)})
    Path(out_path).write_bytes(new_res)
    print(f"Ditulis ke: {out_path}  ({len(res_data)} -> {len(new_res)} byte)")
    print("LANGKAH BERIKUTNYA: python seekmap_rebuild.py build <output.DAT> <first.dat> <first_baru.dat>, lalu tes di PPSSPP.")


# ===========================================================================
# 6. CLI
# ===========================================================================

def _dump_recursive(data: bytes, label: str, lines: list, depth: int = 0, max_depth: int = 4):
    indent = "  " * depth
    try:
        c = GPDAContainer.parse(data)
    except Exception as e:
        lines.append(f"{indent}{label}: bukan GPDA container ({e})")
        return

    lines.append(f"{indent}{label}")
    lines.append(f"{indent}  magic=GPDA  total_size={c.total_size}  count={c.count}  "
                 f"header_and_toc_size={c.header_and_toc_size}  name_table_end={c.name_table_end}")

    for i in range(c.count):
        off, size, name_offset = c.entries[i]
        name = c.names[i]
        lines.append(f"{indent}  [{i}] name={name!r:25} offset={off:#010x} ({off})  "
                     f"size={size:>10}  name_offset={name_offset:#x}")

        if depth < max_depth:
            entry_data = c.entry_bytes(i)
            if entry_data[:4] == b"GPDA":
                _dump_recursive(entry_data, f"-> entry[{i}] ({name})", lines, depth + 1, max_depth)


def _tree_cli(args):
    """python pipeline.py tree <file> [--report out.txt] [--max-depth N]  -- dump struktur GPDA nested."""
    import argparse
    import traceback
    ap = argparse.ArgumentParser(prog="pipeline.py tree",
                                 description="Dump struktur container GPDA (semua level nested) ke layar + file report txt.")
    ap.add_argument("path", help="Path ke file GPDA (mis. RES.DAT)")
    ap.add_argument("--report", default="gpda_structure_report.txt")
    ap.add_argument("--max-depth", type=int, default=4)
    a = ap.parse_args(args)
    lines = [f"Struktur GPDA untuk: {a.path}"]
    try:
        p = Path(a.path)
        if not p.is_file():
            raise FileNotFoundError(f"File tidak ditemukan: {p}")
        data = p.read_bytes()
        lines += [f"Ukuran file di disk: {len(data)} byte", ""]
        print(f"Membaca {p} ({len(data)} byte)...", file=sys.stderr)
        _dump_recursive(data, p.name, lines, 0, a.max_depth)
        print("Selesai parsing.", file=sys.stderr)
    except Exception:
        lines += ["", "!!! ERROR -- proses berhenti sebelum selesai !!!", traceback.format_exc()]
    text = "\n".join(lines)
    print(text)
    Path(a.report).write_text(text, encoding="utf-8")
    print(f"\n(Report -- lengkap atau parsial -- disimpan ke: {Path(a.report).resolve()})")
    if "!!! ERROR" in text:
        sys.exit(1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["tree"]:
        _tree_cli(a[1:]); sys.exit(0)
    report, apos, width, nwidth = None, "\u2019", DEFAULT_WIDTH, None
    for flag in ("--report", "--apos", "--width", "--nwidth", "--apos-w", "--max-lines", "--overflow"):
        if flag in a:
            k = a.index(flag); val = a[k + 1] if k + 1 < len(a) else None
            a = a[:k] + a[k + 2:]
            if flag == "--report": report = val
            elif flag == "--width": width = int(val)
            elif flag == "--nwidth": nwidth = int(val)
            elif flag == "--apos-w": APOS_W = float(val)
            elif flag == "--max-lines": MAX_LINES = int(val)
            elif flag == "--overflow": OVERFLOW_PATH = val
            else: apos = val
    if nwidth is None:
        nwidth = 0 if width == 0 else DEFAULT_NWIDTH
    if a and a[0] == "--verify-only" and len(a) == 4:
        run(a[1], a[2], a[3], None, apos, report, True, width, nwidth)
    elif len(a) == 4:
        run(a[0], a[1], a[2], a[3], apos, report, False, width, nwidth)
    else:
        print(__doc__); sys.exit(1)
