"""
gpda_v2.py  (FIXED)
====================
Parser & rebuilder untuk container format "GPDA" yang dipakai di semua
level Haganai Portable (resource.dat, script.dat, dan container nested
di dalamnya).

=== BUGFIX (root cause dari game crash "CPU Jump to 00000006") ===

Asumsi lama: "entri TERAKHIR dalam container tidak di-pad ke 2048,
offset+size entri terakhir == total_size container persis".

Ini SALAH. Dibuktikan dengan test_identity_rebuild.py di RES.DAT asli:
- Di level resource.dat (top), tebakan lama kelihatan "benar" HANYA
  karena size aslinya (402.360.320) SUDAH kelipatan 2048 secara
  kebetulan -- padding 0 byte jadi tidak kelihatan bedanya.
- Begitu turun ke level nested (chara00.dat, image_bg.dat, dst, yang
  ukuran datanya TIDAK kebetulan pas 2048), rebuild versi lama
  menghasilkan file yang lebih PENDEK dari aslinya persis sebesar sisa
  padding yang seharusnya ada. Semua kasus MISMATCH di
  test_identity_rebuild.py, kalau di-round_up(rebuilt_size, 2048),
  hasilnya PERSIS SAMA dengan original size -- 100% konsisten di semua
  sample yang dicek.

Kesimpulan yang benar: SEMUA entri, TERMASUK yang terakhir, di-pad ke
kelipatan 2048. Tidak ada pengecualian untuk entri terakhir.

Versi lama yang salah inilah yang membuat setiap container nested yang
ukurannya tidak kebetulan 2048-aligned jadi lebih pendek dari
seharusnya saat rebuild -- akibatnya seluruh data SESUDAHNYA (baik di
dalam script.dat, maupun implikasinya ke resource.dat) bergeser dari
posisi yang game harapkan, dan PPSSPP crash baca alamat sampah begitu
game coba lompat ke kode/data yang sudah tidak ada di tempatnya lagi.

=== STRUKTUR (terverifikasi) ===

    Header (16 byte):
        [4]  magic        = b"GPDA"
        [4]  total_size   = ukuran total file/container ini (uint32 LE)
        [4]  reserved     = 0 (uint32 LE)
        [4]  count        = jumlah entri (uint32 LE)

    TOC (16 byte x count, langsung setelah header):
        [4]  data_offset  = offset absolut ke data entri (uint32 LE)
        [4]  reserved     = 0 (uint32 LE)
        [4]  size         = ukuran data entri dalam byte (uint32 LE)
        [4]  name_offset  = offset absolut ke entri nama di name table (uint32 LE)

    Name table (mulai tepat setelah TOC, di offset 16 + count*16):
        Untuk tiap entri (urutan sesuai TOC), di posisi name_offset-nya:
        [4]  length       = panjang string (uint32 LE)
        [length] ascii    = nama file, termasuk trailing space, TIDAK
                             null-terminated secara eksplisit (panjangnya
                             sudah dari field length)

    Padding nol dari akhir name table sampai first_offset (round_up ke
    kelipatan 2048).

    Data entri: masing-masing dimulai di data_offset (selalu kelipatan
    2048), diikuti padding nol sampai kelipatan 2048 berikutnya --
    TERMASUK entri terakhir (total_size container juga selalu kelipatan
    2048).

BUG v1 (gpda.py lama, sebelum v2) yang diperbaiki di v2:
    v1 menghapus name table saat rebuild() -- rebuild cuma nulis ulang
    header+TOC+data entri tanpa name table di antaranya, jadi file hasil
    rebuild rusak (game gak nemu nama entrinya). v2 ini SELALU
    menyalin name table asli apa adanya (byte-for-byte, karena nama-nama
    entri tidak pernah berubah saat proses patch teks) di antara TOC dan
    data entri pertama.
"""

import struct
from pathlib import Path


ALIGN = 2048


def _round_up(value: int, align: int = ALIGN) -> int:
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


# ---------------------------------------------------------------------------
# CLI: jalankan langsung "python gpda_v2.py <file> [--report out.txt]" buat
# lihat struktur file GPDA (semua level nested) tanpa perlu script lain.
# Ini BUKAN tes rebuild (itu ada di test_identity_rebuild.py) -- ini cuma
# dump struktur: nama entri, ukuran, offset, dan level nested-nya.
# ---------------------------------------------------------------------------

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


def _cli():
    import argparse
    import sys
    import traceback

    parser = argparse.ArgumentParser(
        description="Dump struktur container GPDA (semua level nested) ke layar + file report txt."
    )
    parser.add_argument("path", help="Path ke file GPDA (mis. resource.dat)")
    parser.add_argument("--report", default="gpda_structure_report.txt",
                         help="Nama file report txt (default: gpda_structure_report.txt)")
    parser.add_argument("--max-depth", type=int, default=4,
                         help="Batas kedalaman rekursi ke container nested (default: 4)")
    args = parser.parse_args()

    report_path = Path(args.report)
    lines = [f"Struktur GPDA untuk: {args.path}"]

    # Semua langkah di bawah dibungkus try/except supaya kalau ada error
    # di tengah jalan (file gak ketemu, ukuran gak masuk akal, container
    # korup di kedalaman tertentu, dll), report PARSIAL yang sudah
    # berhasil dikumpulkan tetap ditulis ke file -- tidak hilang semua.
    try:
        path_obj = Path(args.path)
        if not path_obj.is_file():
            raise FileNotFoundError(f"File tidak ditemukan: {path_obj}")

        data = path_obj.read_bytes()
        lines.append(f"Ukuran file di disk: {len(data)} byte")
        lines.append("")

        print(f"Membaca {path_obj} ({len(data)} byte)...", file=sys.stderr)
        _dump_recursive(data, path_obj.name, lines, 0, args.max_depth)
        print("Selesai parsing.", file=sys.stderr)

    except Exception:
        lines.append("")
        lines.append("!!! ERROR -- proses berhenti sebelum selesai !!!")
        lines.append(traceback.format_exc())
        # tetap lanjut ke bawah supaya report parsial ini ditulis & ditampilkan

    text = "\n".join(lines)
    print(text)

    report_path.write_text(text, encoding="utf-8")
    print(f"\n(Report -- lengkap atau parsial -- disimpan ke: {report_path.resolve()})")

    if "!!! ERROR" in text:
        sys.exit(1)


if __name__ == "__main__":
    _cli()