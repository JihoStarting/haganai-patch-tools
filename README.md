# Haganai Portable: English Text Patch Tools

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-PSP%20%2F%20PPSSPP-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-selesai%20(final)-brightgreen)

**Status: selesai.** Toolchain untuk menerjemahkan **Boku wa Tomodachi ga Sukunai Portable** (PSP, `ULJS00459`) dari Jepang ke Inggris dengan mengedit `RES.DAT` secara langsung: dialog, narasi, pilihan, sprite menu, dan nama pembicara.

*English summary: reverse-engineered tooling to inject an English script and UI into the PSP game "Haganai Portable" (GPDA container parser, seekmap/CRC rebuilder, EBOOT text-box patcher, menu sprite patcher). No game assets are included.*

> **Repo ini tidak berisi file game.** Tidak ada ISO, `RES.DAT`, `first.dat`, `EBOOT.BIN`, aset hasil ekstrak, maupun CSV terjemahan (yang memuat teks asli game). Untuk memakai alat di sini kamu perlu salinan game milikmu sendiri.

## Daftar isi

- [Sorotan teknis](#sorotan-teknis)
- [Status](#status)
- [Keterbatasan yang diketahui](#keterbatasan-yang-diketahui)
- [Kebutuhan](#kebutuhan)
- [Mulai cepat](#mulai-cepat)
- [Struktur repo](#struktur-repo)
- [Alat](#alat)
- [Format CSV](#format-csv)
- [Catatan teknis](#catatan-teknis)
- [Dokumentasi](#dokumentasi)
- [Lisensi dan disclaimer](#lisensi-dan-disclaimer)

## Sorotan teknis

- **Parser dan rebuilder container GPDA** (`gpda_v2.py`): seluruh entri dipad 2048 byte dan *identity rebuild* lolos pada `RES.DAT` asli.
- **Rebuild seekmap dan `first.dat`** (`seekmap_rebuild.py`): menghitung ulang offset, ukuran, dan checksum CRC-32/MPEG-2. Tanpa langkah ini game crash karena data yang dipatch tidak cocok dengan indeksnya.
- **Kotak teks 3 baris** lewat pergeseran posisi Y di EBOOT terdekripsi (`patch_eboot.py`).
- **Pengaman build**: file yang gagal parse atau verifikasi tidak dipatch (teks Jepang asli tetap utuh) dan alasannya dicatat di laporan skip.

## Status

**Proyek ini dinyatakan selesai** (14 November 2026). Hasil patch sudah memuaskan untuk dimainkan, jadi pengembangan dihentikan di titik ini. Kode tetap dibuka untuk dipelajari atau dilanjutkan siapa saja. Detail lengkap ada di [`scripts/README.md`](scripts/README.md).

| Bidang | Status |
|---|---|
| Terjemahan dialog (15.257 baris) | 100% (CSV tidak dipublikasikan) |
| Terjemahan sisa (7.436 baris) | 100% (CSV tidak dipublikasikan) |
| Injeksi ke game | 93,1% (21.128 dari 22.693 instruksi). Judul scene (673) dan banter (610) masih Jepang |
| Kotak teks 3 baris | Berhasil lewat geser Y di EBOOT (`patch_eboot.py`, Y13) |
| Menu judul | Inggris |
| Menu sistem, Backlog, Options, Extras | Sekitar 75%, sisa kosmetik |
| Dialog konfirmasi (`envpsp.dat`) | Inggris di PPSSPP |
| Nama pembicara | Inggris di plat dialog (`patch_names.py`) |
| Minigame Block Kuzushi | Sprite dibuat, belum dipasang |

## Keterbatasan yang diketahui

Hal-hal berikut tidak akan dikerjakan lagi kecuali ada yang melanjutkan proyek ini:

- Pilihan (choice) belum sejajar dengan balon setelah geser Y.
- Pemenggalan kata di dialog masih belum sempurna.
- Judul scene (673) dan banter (610) masih berbahasa Jepang.
- Menu sistem, Backlog, Options, dan Extras baru sekitar 75% Inggris (sisa kosmetik).
- Sprite minigame Block Kuzushi sudah dibuat tetapi belum dipasang secara resmi.

## Kebutuhan

- Python 3.11 atau lebih baru
- Tanpa dependensi pihak ketiga (hanya pustaka standar)
- Salinan game milikmu sendiri (ISO PSP, `ULJS00459`)
- [PPSSPP](https://www.ppsspp.org/) untuk mengetes

## Mulai cepat

Semua perintah dijalankan dari folder `scripts`.

```
extract.py -> CSV terjemahan (kolom english_text)
   -> pipeline.py (wrap + padding)  -> RES_patched.DAT
   -> seekmap_rebuild.py            -> first_new.dat
   -> tes di PPSSPP (RES.DAT dan first.dat harus dari build yang sama)
```

1. Ekstrak `RES.DAT` dari salinan game milikmu, lalu buat CSV sendiri dengan `extract.py` dan isi kolom `english_text`.
2. Build teks:

```powershell
python pipeline.py RES.DAT dialogue.csv remaining.csv OUT.DAT --max-lines 3 --report skip.csv --overflow overflow.csv
python seekmap_rebuild.py build OUT.DAT first.dat first_new.dat
```

Opsi lebar kolom (`--width`, `--nwidth`, `--apos-w`) dan nilai yang terbukti di game dijelaskan di [`scripts/README.md`](scripts/README.md).

3. Saat mengetes, timpa juga salinan di memstick (`SAVEDATA/ULJS00459DAT/RES.DAT`), karena game membaca dari sana.

## Struktur repo

```
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

Nilai `kind`: `narration/dialog` dan `choice/menu` dipatch; scene title dan banter belum didukung.

## Catatan teknis

- Teks dialog berisi awalan nama pembicara sebelum tanda kurung `「`, sehingga nama diganti langsung di string, bukan di tabel ID.
- Kutip ganda ASCII (`"`) tampil sebagai ♠ di game; pakai pengganti seperti `’`.
- Struktur data: `RES.DAT` (GPDA) → `script.dat` (674 entri) → `_<stem>.dat` → entri 0 → `*.obj.gz` → `.obj.bin`.

## Dokumentasi

- [`scripts/README.md`](scripts/README.md): **dokumentasi teknis utama**: status lengkap, roadmap, aturan kerja, temuan engine, format data, jebakan
- [`docs/NOTES.md`](docs/NOTES.md): catatan reverse engineering singkat
- [`docs/Laporan_Investigasi_Crash_Haganai_Portable.txt`](docs/Laporan_Investigasi_Crash_Haganai_Portable.txt) dan [`docs/Laporan_Perbaikan_seekmap.md`](docs/Laporan_Perbaikan_seekmap.md): investigasi crash dan perbaikan seekmap

## Lisensi dan disclaimer

Kode alat di repo ini dirilis di bawah lisensi MIT (lihat `LICENSE`). Lisensi ini **tidak** mencakup game, aset, maupun teks aslinya.

Proyek penggemar, tidak berafiliasi dengan pemegang hak cipta game. Hak atas game dan teks aslinya milik pemegang aslinya. Gunakan hanya dengan salinan game yang kamu miliki secara sah.
