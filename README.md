# Haganai Portable: Patch Teks Inggris (JP → EN)

by **KangJiho**

Proyek menerjemahkan **Boku wa Tomodachi ga Sukunai Portable** (PSP, ULJS00459) ke bahasa Inggris dengan mengedit `RES.DAT` secara langsung: teks dialog, narasi, pilihan, sprite menu, dan nama pembicara.

> **Repo ini tidak berisi file game.** Tidak ada ISO, `RES.DAT`, `first.dat`, `EBOOT.BIN`, atau aset hasil ekstrak. Untuk menjalankan alat di sini kamu perlu salinan game milikmu sendiri.

## Status

Per catatan progres terakhir (2026-10-24). Detail lengkap ada di [`scripts/README.md`](scripts/README.md).

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

Masalah terbuka: pilihan (choice) belum sejajar dengan balon setelah geser Y, pemenggalan kata di dialog, dan build v30 belum dites penuh di game.

## Struktur repo

```
translation/     (tidak dipublikasikan; berisi teks asli game)
scripts/         pipeline, alat CSV, patcher menu/EBOOT/nama pembicara
  core/          parser GPDA (gpda_v2.py), pipeline versi awal, validator
  envpsp_variants/  patcher envpsp.dat dan EBOOT
  block_patch/   patcher sprite minigame
  ui_menu/       patcher sprite menu
docs/            catatan teknis dan laporan investigasi
new_script/      gpda.bms (skrip QuickBMS untuk container GPDA)
```

File besar dan hasil build tidak di-push (lihat `.gitignore`).

## Kebutuhan

- Python 3.11 atau lebih baru
- Tidak ada dependensi pihak ketiga (hanya pustaka standar)
- Salinan game milikmu sendiri (ISO PSP, ULJS00459) dan emulator PPSSPP untuk mengetes

## Alur kerja

```
extract.py → CSV terjemahan (kolom english_text)
   → pipeline.py (wrap + padding)  → RES_patched.DAT
   → seekmap_rebuild.py            → first_new.dat
   → tes di PPSSPP (RES.DAT dan first.dat harus dari build yang sama)
```

Semua perintah dijalankan dari folder `scripts`.

### Build teks

```powershell
python pipeline.py RES.DAT dialogue.csv remaining.csv OUT.DAT --max-lines 3 --report skip.csv --overflow overflow.csv
python seekmap_rebuild.py build OUT.DAT first.dat first_new.dat
```

Opsi lebar kolom (`--width`, `--nwidth`, `--apos-w`) dan nilai yang terbukti di game dijelaskan di [`scripts/README.md`](scripts/README.md). Tanpa `seekmap_rebuild.py`, game crash karena offset, ukuran, dan CRC tidak cocok dengan data yang sudah dipatch.

### Alat lain

| Skrip | Fungsi |
|---|---|
| `patch_names.py` | Ganti nama pembicara di RES yang sudah dipatch (`--check` dulu, aman diulang) |
| `patch_eboot.py` | Geser posisi Y teks di EBOOT terdekripsi agar 3 baris muat |
| `patch_envpsp.py` | Ganti string dialog konfirmasi di `envpsp.dat` |
| `ui_menu/menu_patch/patch_menu.py` | Pasang sprite menu Inggris (ulangi tiap build RES baru) |
| `block_patch/patch_block.py` | Pasang sprite minigame |
| `csv_tools.py` | Cek dan perbaiki CSV (panjang, pilihan, encoding) |
| `dump.py`, `cut_gpda.py`, `cari_string.py` | Bongkar dan periksa isi game (baca-saja) |

## Format CSV

| File | Kolom | Kunci |
|---|---|---|
| Dialog (`haganai_dialogue_EN_v30.csv`) | `file, offset, speaker, text, clean_text, english_text` | `file` + `offset` |
| Sisa (`haganai_remaining_EN_full_v30.csv`) | `scene, inst_index, opcode, str_index, kind, jp_text, jp_clean, english_text` | `scene` + `inst_index` (+ `str_index`) |

Nilai `kind`: `narration/dialog` dan `choice/menu` dipatch; scene title dan banter belum didukung.

## Catatan teknis

- `gpda_v2.py` adalah parser dan rebuilder container GPDA. Semua entri dipad 2048 byte, dan identity rebuild lolos pada `RES.DAT` asli.
- `seekmap_rebuild.py` membangun ulang `seekmap` dan `first.dat` (checksum CRC-32/MPEG-2) setelah `RES.DAT` berubah.
- Teks dialog berisi awalan nama pembicara sebelum tanda kurung `「`, sehingga nama diganti langsung di string, bukan di tabel ID.
- Game membaca salinan di memstick (`SAVEDATA/ULJS00459DAT/RES.DAT`). Timpa file itu juga saat mengetes.
- Kutip ganda ASCII (`"`) tampil sebagai ♠ di game; pakai pengganti seperti `’`.

## Dokumentasi

- [`scripts/README.md`](scripts/README.md): status lengkap, roadmap, aturan kerja, temuan engine, format data, jebakan
- [`docs/NOTES.md`](docs/NOTES.md): catatan reverse engineering singkat
- [`docs/Laporan_Investigasi_Crash_Haganai_Portable.txt`](docs/Laporan_Investigasi_Crash_Haganai_Portable.txt) dan [`docs/Laporan_Perbaikan_seekmap.md`](docs/Laporan_Perbaikan_seekmap.md): investigasi crash dan perbaikan seekmap

## Catatan

Proyek penggemar, tidak berafiliasi dengan pemegang hak cipta game. Hak atas game dan teks aslinya milik pemegang aslinya.




