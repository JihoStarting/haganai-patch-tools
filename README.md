<div align="center">

# Haganai Portable: English Text Patch Tools

**Toolchain reverse-engineering untuk menyuntikkan teks dan UI bahasa Inggris ke *Boku wa Tomodachi ga Sukunai Portable* (PSP, `ULJS00459`).**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-PSP%20%2F%20PPSSPP-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-selesai%20(final)-brightgreen)

[Arsitektur](#arsitektur) · [Status](#status) · [Mulai cepat](#mulai-cepat) · [Alat](#alat) · [Format CSV](#format-csv) · [Pemecahan masalah](#pemecahan-masalah) · [Lisensi](#lisensi-dan-disclaimer)

</div>

---

> **English summary:** Reverse-engineered tooling that rebuilds the PSP game *Haganai Portable* with an English script and UI by editing `RES.DAT` directly. It includes a GPDA container parser/rebuilder, a seekmap and CRC-32 rebuilder, an EBOOT text-box patcher (3-line dialogue), and menu/minigame sprite patchers. The project is **complete**. No game assets or original text are included; you need your own legally obtained copy of the game.

> **Repo ini tidak berisi file game.** Tidak ada ISO, `RES.DAT`, `first.dat`, `EBOOT.BIN`, aset hasil ekstrak, maupun CSV terjemahan (yang memuat teks asli game). Untuk memakai alat di sini kamu perlu salinan game milikmu sendiri.

## Ringkasan

Proyek ini menerjemahkan dialog, narasi, pilihan, sprite menu, dan nama pembicara dengan mengedit `RES.DAT` secara langsung, tanpa mengubah ISO secara manual.

| Komponen | Peran |
|---|---|
| **Parser dan rebuilder GPDA** (`gpda_v2.py`) | Membaca dan menyusun ulang container. Semua entri dipad 2048 byte, dan *identity rebuild* lolos pada `RES.DAT` asli. |
| **Rebuilder seekmap** (`seekmap_rebuild.py`) | Menghitung ulang offset, ukuran, dan checksum CRC-32/MPEG-2 di `first.dat`. Tanpa langkah ini game crash karena data yang dipatch tidak cocok dengan indeksnya. |
| **Patcher EBOOT** (`patch_eboot.py`) | Menggeser posisi Y teks di EBOOT terdekripsi sehingga kotak teks muat 3 baris. |
| **Pengaman build** | File yang gagal parse atau verifikasi tidak dipatch (teks Jepang asli tetap utuh), dan alasannya dicatat di laporan skip. |

## Arsitektur

Alur kerja dari salinan game sampai siap dites. `RES.DAT` yang dipatch selalu harus dibangun ulang indeksnya lewat `seekmap_rebuild.py`; `EBOOT.BIN` dan `envpsp.dat` dipatch terpisah.

```text
                ┌──────────────────────────┐
                │ Salinan game milikmu     │
                │ (ISO PSP, ULJS00459)     │
                └─────────────┬────────────┘
        ┌─────────────────────┼─────────────────────┐
        │ RES.DAT             │ EBOOT.BIN           │ envpsp.dat
        ▼                     ▼                     ▼
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ Teks + sprite  │    │ Kotak 3 baris  │    │ Dialog         │
│ pipeline.py    │    │ patch_eboot.py │    │ konfirmasi     │
│ patch_names.py │    │                │    │ patch_envpsp.py│
│ patch_menu.py  │    │                │    │                │
│ patch_block.py │    │                │    │                │
└───────┬────────┘    └───────┬────────┘    └───────┬────────┘
        ▼                     │                     │
┌────────────────┐            │                     │
│ seekmap_rebuild│            │                     │
│ first_new.dat  │            │                     │
└───────┬────────┘            │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                ┌──────────────────────────┐
                │ Tes di PPSSPP            │
                └──────────────────────────┘
```

## Status

**Proyek ini dinyatakan selesai (14 November 2026).** Hasil patch sudah memuaskan untuk dimainkan, sehingga pengembangan dihentikan di titik ini. Kode tetap terbuka untuk dipelajari atau dilanjutkan siapa saja.

| Bidang | Status |
|---|---|
| Terjemahan dialog (15.257 baris) | Selesai (CSV tidak dipublikasikan) |
| Terjemahan sisa (7.436 baris) | Selesai (CSV tidak dipublikasikan) |
| Injeksi ke game | 93,1% (21.128 dari 22.693 instruksi) |
| Kotak teks 3 baris | Selesai, lewat geser Y di EBOOT (`patch_eboot.py`, varian Y13) |
| Menu judul | Selesai (Inggris) |
| Dialog konfirmasi (`envpsp.dat`) | Selesai (Inggris di PPSSPP) |
| Nama pembicara | Selesai (Inggris di plat dialog, `patch_names.py`) |
| Menu sistem, Backlog, Options, Extras | Sebagian (sekitar 75%, sisa kosmetik) |
| Judul scene (673) dan banter (610) | Belum (masih Jepang) |
| Minigame Block Kuzushi | Sprite dibuat, belum dipasang resmi |

### Keterbatasan yang diketahui

Hal-hal berikut tidak akan dikerjakan lagi kecuali ada yang melanjutkan proyek ini:

- Pilihan (choice) belum sejajar dengan balon setelah geser Y.
- Pemenggalan kata di dialog masih belum sempurna.
- Judul scene dan banter belum didukung oleh pipeline.
- Beberapa label menu masih Jepang atau terpotong.

## Kebutuhan

- Python 3.11 atau lebih baru (hanya pustaka standar, tanpa dependensi pihak ketiga)
- Salinan game milikmu sendiri (ISO PSP, `ULJS00459`)
- [PPSSPP](https://www.ppsspp.org/) untuk mengetes

## Mulai cepat

Semua perintah dijalankan dari folder `scripts`.

```text
extract.py          ->  CSV terjemahan (isi kolom english_text)
pipeline.py         ->  RES_patched.DAT   (wrap + padding)
seekmap_rebuild.py  ->  first_new.dat
tes di PPSSPP       ->  RES.DAT dan first.dat harus dari build yang sama
```

**1. Siapkan CSV.** Ekstrak `RES.DAT` dari salinan game milikmu, lalu buat CSV dengan `extract.py` dan isi kolom `english_text`.

**2. Build teks.**

```powershell
python pipeline.py RES.DAT dialogue.csv remaining.csv OUT.DAT --max-lines 3 --report skip.csv --overflow overflow.csv
python seekmap_rebuild.py build OUT.DAT first.dat first_new.dat
```

Opsi lebar kolom (`--width`, `--nwidth`, `--apos-w`) dan nilai yang terbukti di game dijelaskan di [`scripts/README.md`](scripts/README.md).

**3. Tes.** Timpa juga salinan di memstick (`SAVEDATA/ULJS00459DAT/RES.DAT`), karena game membaca dari sana.

## Struktur repo

```text
scripts/              pipeline, alat CSV, patcher menu/EBOOT/nama pembicara
  core/               parser GPDA (gpda_v2.py), pipeline versi awal, validator
  envpsp_variants/    patcher envpsp.dat dan EBOOT
  block_patch/        patcher sprite minigame
  ui_menu/            patcher sprite menu
docs/                 catatan teknis dan laporan investigasi
new_script/           gpda.bms (skrip QuickBMS untuk container GPDA)
```

File besar, aset game, dan hasil build tidak disertakan (lihat `.gitignore`).

## Alat

| Skrip | Fungsi |
|---|---|
| `scripts/pipeline.py` | Build penuh teks: dialog, narasi, pilihan, wrap dan padding |
| `scripts/seekmap_rebuild.py` | Bangun ulang seekmap dan `first.dat` setelah `RES.DAT` berubah |
| `scripts/patch_names.py` | Ganti nama pembicara di RES yang sudah dipatch (`--check` dulu, aman diulang) |
| `scripts/envpsp_variants/patch_eboot.py` | Geser posisi Y teks di EBOOT terdekripsi agar 3 baris muat |
| `scripts/patch_envpsp.py` | Ganti string dialog konfirmasi di `envpsp.dat` |
| `scripts/ui_menu/menu_patch/patch_menu.py` | Pasang sprite menu Inggris (ulangi tiap build RES baru) |
| `scripts/block_patch/patch_block.py` | Pasang sprite minigame |
| `scripts/csv_tools.py` | Cek dan perbaiki CSV (panjang, pilihan, encoding) |
| `scripts/dump.py`, `cut_gpda.py`, `cari_string.py` | Bongkar dan periksa isi game (baca-saja) |

## Format CSV

CSV tidak didistribusikan karena memuat teks asli game. Formatnya didokumentasikan agar bisa dibuat sendiri lewat `extract.py`.

| File | Kolom | Kunci |
|---|---|---|
| Dialog | `file, offset, speaker, text, clean_text, english_text` | `file` + `offset` |
| Sisa | `scene, inst_index, opcode, str_index, kind, jp_text, jp_clean, english_text` | `scene` + `inst_index` (+ `str_index`) |

Nilai `kind` yang dipatch: `narration/dialog` dan `choice/menu`. Scene title dan banter belum didukung.

## Catatan teknis

- **Struktur data:** `RES.DAT` (GPDA) → `script.dat` (674 entri) → `_<stem>.dat` → entri 0 → `*.obj.gz` → `.obj.bin`.
- **Nama pembicara:** teks dialog berisi awalan nama sebelum tanda kurung `「`, sehingga nama diganti langsung di string, bukan di tabel ID.
- **Kutip ganda:** karakter ASCII `"` tampil sebagai ♠ di game. Gunakan pengganti seperti `’`.

## Pemecahan masalah

| Gejala | Penyebab dan solusi |
|---|---|
| Game crash saat dimuat | `RES.DAT` dan `first.dat` berasal dari build berbeda, atau `seekmap_rebuild.py` belum dijalankan. Bangun ulang keduanya dari build yang sama. |
| Perubahan tidak muncul di game | Game membaca `RES.DAT` dari memstick. Timpa juga `SAVEDATA/ULJS00459DAT/RES.DAT`. |
| Sebagian teks tetap Jepang | File tersebut gagal parse atau verifikasi dan sengaja dilewati. Periksa laporan skip (`--report`). |
| Teks tampil ♠ | Ada tanda kutip ganda ASCII di terjemahan. Ganti dengan `’`. |
| Menu masih Jepang setelah build baru | Jalankan ulang `patch_menu.py` pada tiap build `RES.DAT` baru. |

## Dokumentasi

- [`scripts/README.md`](scripts/README.md): dokumentasi teknis utama (status lengkap, aturan kerja, temuan engine, format data, jebakan)
- [`docs/NOTES.md`](docs/NOTES.md): catatan reverse engineering singkat
- [`docs/Laporan_Investigasi_Crash_Haganai_Portable.txt`](docs/Laporan_Investigasi_Crash_Haganai_Portable.txt) dan [`docs/Laporan_Perbaikan_seekmap.md`](docs/Laporan_Perbaikan_seekmap.md): investigasi crash dan perbaikan seekmap

## Melanjutkan proyek

Proyek ini sudah selesai dari sisi pemiliknya, tetapi terbuka untuk dilanjutkan. Titik awal yang paling berguna adalah daftar [keterbatasan](#keterbatasan-yang-diketahui) di atas, terutama dukungan judul scene dan banter, serta penyelarasan pilihan dengan balon.

## Lisensi dan disclaimer

Kode alat di repo ini dirilis di bawah lisensi MIT (lihat [`LICENSE`](LICENSE)). Lisensi ini **tidak** mencakup game, aset, maupun teks aslinya.

Proyek penggemar, tidak berafiliasi dengan pemegang hak cipta game. Hak atas game dan teks aslinya milik pemegang aslinya. Gunakan hanya dengan salinan game yang kamu miliki secara sah.
