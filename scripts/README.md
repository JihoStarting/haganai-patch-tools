# Haganai Portable: Patch Teks Inggris

by: KangJiho · Terakhir diperbarui: 2026-10-24 (versi ringkas; rilis teks tetap v30)

Proyek menerjemahkan **Boku wa Tomodachi ga Sukunai Portable (PSP, ULJS00459)** ke bahasa Inggris dengan mengedit `RES.DAT` langsung. Dokumen ini adalah versi **ringkas tapi lengkap** dari README panjang: status, roadmap, panduan kerja, temuan engine, dan format data asli. Urutan: dari yang paling sering dibaca ke yang paling jarang. Tanggal tertera = sumber kebenaran; yang terbaru menang.

> **ARAH PROYEK (keputusan pemilik, 2026-10-19):** terjemahan **tidak lagi dipotong/dipendekkan** batch demi batch (makna berkorban). Target: **kotak teks muat 3 baris** (geser teks naik), lalu pakai terjemahan penuh. Pemendekan (`fixes_batch*`) **dibekukan**; jangan tulis batch pemendekan baru kecuali pemilik meminta. Satu-satunya pemendekan yang diizinkan: teks yang masih **> 3 baris** (seri `fix_batch*_v27` s.d. v30).

## Ringkasan perkembangan (kronologis)

| Tanggal | Peristiwa |
|---|---|
| 2026-10-19 | Keputusan arah (3 baris). EBOOT dan `envpsp.dat` dibongkar |
| 2026-10-20 | **Geser Y `EBOOT_Y13.BIN` BERHASIL** (teks naik 13 px, 3 baris muat). Menu judul Inggris selesai (sprite). Build v14 (terjemahan penuh) dites: 3 masalah (kutip ganda ♠, huruf nyelip, baris ke-4 terpotong) |
| 2026-10-21 | Injeksi 93,1% (21.128/22.693 instruksi). Pemolesan narasi v25_clean (286 baris) |
| 2026-10-22 | Overflow v27 (1.644 teks) selesai ditulis ulang; sisa 131 teks selesai (v28-v30). CSV pindah ke `scripts tools\csv`. 16 sprite menu sistem Inggris dibuat |
| 2026-10-23 | Menu sistem v2 dites (Inggris di game); sprite Extras (20) dipasang; 18 sprite minigame Block Kuzushi dibuat (belum dipasang); **dialog konfirmasi System Menu tampil Inggris di game** lewat `envpsp.dat` |
| 2026-10-24 | **Nama pembicara tampil Inggris di game** (`Yozora` di plat nama, scene `0011ess0`, PPSSPP v1.20.4). Nama ternyata ada di awal string dialog (`夜空「…」`), bukan di tabel ID; `patch_names.py` mengganti 15.014 awalan nama di `RES_v30_flow_test.DAT` → `RES_v31_names.DAT` + `first_new_v31_names.dat` (15.698/15.698 cocok). Folder game, salinan memstick, dan EBOOT terbaru dicatat (4.8) |

## Daftar isi

1. Gambaran proyek · 2. Status · 3. Roadmap · 4. Folder, skrip, data · 5. Cara menjalankan · 6. Aturan kerja · 7. Temuan engine · 8. Format data game · 9. Opsi untuk teks > 2 baris · 10. Gerbang build · 11. Jebakan · 12. Riwayat · 13. Lampiran

---

## 1. Gambaran proyek

### Alur kerja

```
extract.py → CSV terjemahan (kolom english_text)
   → pipeline.py (wrap + padding otomatis) → RES_patched_vN.DAT
   → seekmap_rebuild.py (first.dat asli sebagai dasar) → first_new_vN.dat
   → tes di PPSSPP (RES + first.dat harus dari build yang sama)
```

### Masalah utama

Kotak teks asli hanya muat **2 baris**; terjemahan Inggris sering 3-4 baris sehingga baris ke-3 terpotong. Cara lama: memendekkan (1.429 baris, dibekukan). Cara sekarang: **geser teks naik 13 px (Y13)** sehingga 3 baris muat. Cadangan: pecah dialog jadi dua kotak (bagian 9).

### Folder kerja

| Folder | Isi |
|---|---|
| `D:\Reverse engginering\project haganai\scripts tools` | semua skrip `.py`, hasil build, subfolder kerja. **Semua perintah dijalankan dari sini** |
| `...\scripts tools\csv` | semua CSV kerja (117-118 item) |
| `...\scripts tools\Ui menu` | semua berkas menu/UI (lihat 4.7) |
| `...\script_output\translate dialogue` | CSV sumber terjemahan |
| `...\data ekstrak` | game asli (`RES.DAT`, `first.dat`, `EBOOT.BIN`, `envpsp.dat`, `font.dat`). **Jangan diedit** |

---

## 2. Status sekarang

| Bidang | Status |
|---|---|
| Arah proyek | Pemendekan dibekukan; terjemahan penuh dipakai; 3 baris **terbukti** (Y13) |
| Injeksi teks (patch v14) | **93,1%** (21.128/22.693 instruksi). Sisa: scene title 673 + banter 610 (tetap Jepang, butuh reverse opcode) |
| Terjemahan dialog (15.257 baris) | 100% (`haganai_dialogue_EN_v30.csv`) |
| Terjemahan remaining (7.436 baris) | 100% (`haganai_remaining_EN_full_v30.csv`) |
| Pemolesan narasi | 286/5.817 baris (4,92%); `changelog_v25_clean.csv` 576 entri. Angka lama "814 baris (13,99%)" **salah** (512 entri no-op) |
| Teks > 3 baris (v27) | 1.644 ditulis ulang (dialog 970, narasi 674). Narasi sudah masuk CSV; dialog masuk lewat `apply_dialog_v27.py` (**922 dari 1.005 cocok, 83 tidak**; 5 di antaranya tidak overflow dan tetap teks lama) |
| Sisa overflow setelah v27 (131 teks) | Ditulis ulang (batch v28-v30) dan masuk `*_v30.csv`; **belum dicek di pipeline, belum dites di game** |
| Geser Y EBOOT | **100%** (`EBOOT_Y13.BIN`, PPSSPP v1.20.4) |
| Menu judul (sprite) | **100%**; sisa kosmetik: label terpotong tepi kanan (`NEW GAM`, `CONTINU`) |
| Menu sistem/Backlog/Options/Extras | **~75%**: judul System Menu, Backlog, Keyword List, header Options, tombol, menu Extras Inggris di game. **Belum:** info chapter `プロローグ`, tab Options & judul Keyword List terpotong, `戻る` di Keyword List |
| Nama pembicara (plat dialog) | **Tampil Inggris di game** (build `v31_names`; `Yozora` terkonfirmasi lewat screenshot 2026-10-24). 15.014 awalan diganti; 243 awalan tak dikenal tidak diubah (belum diperiksa). Belum dites di game: nama lain, terutama `Yukimura` (8 huruf, muat di plat?) |
| Dialog konfirmasi (`envpsp.dat`) | **Tampil Inggris di game** (kembali ke judul, simpan data sistem, `Yes/No/Back`). Belum dites: Save/Load/Quick Load, Backjump, reset Options, Scene Replay, Extra Scenarios |
| Minigame Block Kuzushi | 18 sprite Inggris dibuat (`block_patch_v1.zip`), **belum dipasang/dites**. Belum dikerjakan: `bd_help1-3`, `bd_thelp01`, `bd_sel*_name`, logo karakter, `bd_tmenu` |
| Teks pilihan (choice) | 365 baris terisi (di CSV penuh 336), 0 kosong |
| Seekmap (`first.dat`) | 15.698/15.698 node cocok, 0 mismatch |

**Penghalang terbesar:** (1) choice tidak sejajar balon setelah geser Y; (2) pemenggalan kata dan jarak antar-huruf dialog (R-A8); (3) aturan lebar kolom belum terbukti di game.

---

## 3. Roadmap

```
Fase 0 Verifikasi → Fase 1 Kalibrasi lebar → Fase A Kotak 3 baris (prioritas) → Pakai terjemahan penuh → Fase 5 Rilis
Fase 2 Pemendekan (DIBEKUKAN, cadangan) → Fase 3 Sisa tak muat
Fase 4 Konten belum dipatch (paralel)
```

### Fase 0: Verifikasi
- [ ] R0.1 Pasang `pipeline.py` versi `--width2` (cek `findstr /C:"--width2" pipeline.py`; file unduhan harus *menimpa*, bukan `pipeline (1).py`). Tanpa ini build v13 hanya mencetak bantuan lalu `seekmap_rebuild.py` gagal `FileNotFoundError`.
- [ ] R0.2 Tes build di PPSSPP (game baru, tanpa save state). Cek: huruf nyelip, kata terbelah, baris ke-3, baris 2 menjorok.
- [ ] R0.3 Periksa `skip_v12.csv` (37 baris: 10 `0000Index` aman diabaikan; 27 "english_text kosong" seharusnya sudah hilang).
- [ ] R0.4 Uji skrip hasil perapian pada data asli: `tests.py identity RES.DAT`, `dump.py opcodes RES.DAT`, `csv_tools.py short`.

### Fase 1: Kalibrasi lebar
- [ ] R1.1 Tes `ruler2` (`calibrate.py ruler2 ...`, build `--width 0`). Teori benar bila `.`, `’`, `…` patah di ~24-25 dan `i` di ~39.
- [ ] R1.2 Build dan tes v13 (`--width 36 --width2 38 --nwidth 38`).
- [ ] R1.3 Samakan `csv_tools.py` dengan `pipeline.py` (lebar baris 2+, metrik 7/10 bila R1.1 cocok).
- [ ] R1.4 Hitung ulang sisa overflow; R1.5 tetapkan lebar standar dan perbarui bagian 6.

| Hasil | Tindakan |
|---|---|
| R1.1 cocok | Ganti `cw`, `wrap_lines`, `wrap_pad` ke metrik 7/10 (huruf, angka, spasi, `:` = 7; lainnya = 10; kapasitas ≈ 39 x 7) |
| R1.1 tidak cocok | Buang teori; pakai hasil v13 |
| v13 kata terbelah | Fallback `--width 35 --width2 37 --nwidth 37` |
| Apostrof bermasalah | `--apos-w 1` atau `2` |
| Baris 2 menjorok | Selidiki spasi pad melewati kapasitas |

### Fase A: Kotak 3 baris (prioritas sejak 2026-10-19)
- [x] R-A3/R-A4 Eksperimen dan cara patch: patch instruksi di EBOOT terdekripsi (`patch_eboot.py`, Y13).
- [~] R-A1 Ambil `envpsp.dat` (selesai, tapi jalur ini tidak dibutuhkan lagi untuk geser Y).
- [ ] R-A2 Pemanggil kotak dialog (tidak lagi kritis).
- [ ] R-A5 Pakai terjemahan penuh (build v14 sudah dites; v30 belum).
- [ ] R-A6 Samakan alat: `pipeline.py` dan `csv_tools.py` ke `--max-lines 3` + lebar baru; hitung teks penuh yang masih > 3 baris.
- [ ] **R-A7 Choice sejajar balon.** Geser Y global menaikkan teks choice 13 px, balon (sprite terpisah) tidak ikut. Opsi: (a) patch bersyarat hanya bila Y awal `$a3` di rentang dialog/narasi; (b) cari pemanggil glyph khusus choice; (c) geser balon 13 px lewat data UI.
- [ ] **R-A8 Pemenggalan kata** (`N / eighbors`, `fro / m`): pecah di spasi, lebar ~35-37; juga jarak antar-huruf lebar di dialog.

Aturan: bila Fase A buntu, **tanya pemilik** sebelum kembali memotong teks.

### Fase 2: Pemendekan (DIBEKUKAN)
Hanya dilanjutkan bila pemilik meminta. Loop: worklist baru → tulis batch → terapkan (`ditolak: 0 | tidak ketemu: 0`) → backup `FULL_*_fixed.csv` dan `fixes_batch*.csv`. Baseline lama: 5.341 teks > 2 baris (~54 batch @100).

### Fase 3: Sisa yang tidak muat
Jalur: pendekkan yang bisa + perlakuan khusus yang tidak bisa (hybrid). Geser teks sudah berhasil; pecah dua kotak masih terblokir (opcode goto belum ketemu; `jumpscan2` rencana subcommand `dump.py`).

### Fase 4: Konten belum dipatch
- [ ] R4.1 Batas panjang choice (22/30/38 kolom; tes awal: 22 muat, lebih panjang keluar balon tapi terbaca).
- [ ] R4.2 Scene title (673; op700 ada 674, kemungkinan `0000Index` "INDEX" tak terekstrak) · R4.3 Banter (610; op 1012/1013/1014: 445/245/210) · R4.4 Karakter berisiko ♠ (`é`, `①`, `…`, `π`, ~17 baris) · R4.5 Hal terbuka: selisih 22 baris dialog, 19 instruksi choice belum terurai, checksum seekmap.
- [x] R4.6 Menu judul Inggris.
- [~] R4.7 Menu pause/backlog: sprite v2 terpasang dan tampil Inggris; sisa kosmetik (tab Options, judul Keyword List, `戻る`).
- [ ] R4.8 Judul scene di Backlog (`プロローグ`, op700).
- [x] R4.9 Menu Extras (20 sprite v3 dipasang; pemilik: "bisa"; label ikon ±8 px belum diperiksa lewat screenshot).
- [x] R4.10 Dialog konfirmasi (di `envpsp.dat`, tampil Inggris 2026-10-23 malam).
- [x] R4.11 Nama pembicara (2026-10-24): nama ada di **awal string dialog** (`speaker_field`, sebelum `「`), bukan di tabel ID (EBOOT dan `zz*.tmp` dicari: tidak ada). Diganti lewat `patch_names.py` (5.8); `Yozora` tampil di game. Sisa: [ ] tes nama lain dan lebar plat (`Yukimura`) · [ ] periksa 243 awalan "speaker tak dikenal" (`python patch_names.py RES.DAT --check`).
- [ ] R4.12 Info chapter di menu pause (`プロローグ` / `テラス` / `ゆるやかな昼`); bukan di `envpsp.dat`, kemungkinan terkait op700.

### Fase 5: Rilis
- [ ] Semua gerbang bagian 10 tercentang · [ ] screenshot 3-5 sampel terparah · [ ] build final dengan `first.dat` sepasang · [ ] catat nama build + MD5 pasangan final · [ ] arsipkan file tes/build lama (pertahankan pasangan final dan semua CSV kerja).

### Langkah terdekat
1. Cek ulang overflow v30 di pipeline, build baru (`--max-lines 3`), tes scene yang diubah (`0083mar0`, `a483ess0`, `rb071b_mar6`, `omake_kob`).
2. Pasang `block_patch_v1.zip`, tes minigame (cek tabrakan dengan teks engine `Select`/`Back`).
3. R-A7 (choice sejajar) dan R-A8 (pemenggalan kata).
4. Sprite kecil sisa: tab Options, judul Keyword List, `戻る`.
5. Tes dialog `envpsp.dat` lain; selidiki huruf pertama dialog tampak lebih besar (`Re`, `Sav`; mungkin animasi muncul teks).
6. R4.12 dan teks `envpsp.dat` lain (judul chapter, pesan instalasi, nama BG, komentar musik).
7. Tes nama pembicara lain di game (terutama `Yukimura`, lebar plat) dan periksa 243 awalan tak dikenal.

---

## 4. Folder, skrip, dan data

### 4.1 Skrip

| File | Fungsi / perintah |
|---|---|
| `pipeline.py` | Membangun `RES.DAT` baru: injeksi teks, wrap + padding. File gagal parse/verify tidak dipatch (alasan di laporan skip). `python pipeline.py RES.DAT dialogue.csv remaining.csv OUT.DAT [--max-lines --width --width2 --nwidth --report --overflow --apos-w]` |
| `seekmap_rebuild.py` | Membuat `first.dat` yang cocok dengan RES baru; berisi `parse_seekmap` (dipakai `dump.py`, `extract.py`). `python seekmap_rebuild.py build RES.DAT first.dat first_new.dat` |
| `csv_tools.py` | Alat CSV: `fix`, `short`, `choice-fixes`, `choice-short`, `choice-gaps`, `choice-missing`, `fill-todo`, `long-choices`, `encoding`, `verify-length`. Mengimpor `pipeline.py` → harus berdampingan |
| `apply_dialog_v27.py` | Menerapkan `fixes_dialog_v27_all.csv` ke CSV dialog (cocok `file`+`offset`; teks lama harus sama, kalau tidak dilewati kecuali `--force`; mismatch → `apply_dialog_v27_mismatch.csv`). `python apply_dialog_v27.py csv\haganai_dialogue_EN_v6.csv csv\fixes_dialog_v27_all.csv csv\haganai_dialogue_EN_v27.csv [--force]` |
| `patch_names.py` | Ganti nama pembicara di RES yang **sudah dipatch** (tanpa CSV): awalan sebelum `「` di op100 → nama Inggris; header `+11` dan ukuran instruksi dihitung ulang. `python patch_names.py RES_in.DAT --check`, lalu `python patch_names.py RES_in.DAT RES_out.DAT`; butuh `pipeline.py` di folder yang sama; aman diulang (baris yang sudah Inggris dilewati). Lanjutkan dengan `seekmap_rebuild.py` |
| `pipeline_names.py` | `pipeline.py` + penggantian nama saat build dari RES asli (`--keep-jp-names` mematikan). **Belum dipakai**; build terbaru memakai `patch_names.py` di atas RES `flow_test` |
| `dump.py` | Bongkar isi game: `obj inst hex tree entry scan find text gpda-entry seekmap-pos opcodes` |
| `calibrate.py` | Build uji lebar: `ruler ruler2 apos apos-test lines` |
| `tests.py` | `identity`, `crosscheck`, `seekmap` |
| `extract.py` | Ekstraksi awal teks ke CSV |
| `patch_eboot.py` | Geser Y glyph (Y13 berhasil): `python patch_eboot.py ULJS00459_EBOOT.BIN KELUARAN.bin [geser_px]` |
| `patch_menu.py` (`menu_patch\`) | Ganti sprite menu: cocokkan MD5 GIM asli (`originals.txt`), gzip ulang di slot sama, perbarui ukuran GPDA. Hasil `NAMA.DAT.patched`, input tak diubah. **Harus diulang tiap build RES baru** |
| `menu_check.py` | Baca-saja: status JEPANG/INGGRIS 12 sprite lama (belum diperluas ke 28/48) |
| `tambah_extras.py` | Menambah 20 baris Extras ke `originals.txt` (cadangan `.bak`) |
| `cut_gpda.py` | Baca-saja: potong container GPDA. `python cut_gpda.py RES.DAT list` / `cut out_menu --small` / `cut out_block image_block.dat` |
| `patch_envpsp.py` | **Versi dialog** (baru): ganti 21 jenis string dialog di `envpsp.dat`; cocok record persis; punya `--check` |
| `patch_envpsp lama.py` | Skrip lama (label menu, rentang `0x1E00`-`0xAB00`); **sudah terpakai, jangan jalankan ulang** |
| `patch_block.py` (`block_patch\`) | Pasang 18 sprite minigame; punya `--check` |
| `cari_string.py` | Baca-saja: cari string Jepang (UTF-16LE, Shift-JIS, UTF-8, termasuk gzip tertanam). Harus disalin ke `scripts tools` dulu |
| `envpsp_variants*.py` | Varian uji skala float (jalur lama, tidak dipakai) |
| `jumpscan2.py` | Rencana cari opcode goto; belum ada/jalan (jadikan subcommand `dump.py`) |

Skrip lepas lama (`apply_short.py`, `fill_todo.py`, `choice_gaps.py`, `shorten_pass.py`, `make_choice_fixes.py`) sudah tercakup `csv_tools.py`; boleh diarsipkan.

### 4.2 CSV utama (di `scripts tools\csv`)

| File | Isi |
|---|---|
| `haganai_dialogue_EN_v30.csv` (terbaru; juga v2, v3_fixed, v6, v27-v29) | 15.257 dialog ber-speaker. Kolom: `file, offset, speaker, text, clean_text, english_text`. Kunci: `file`+`offset` (posisi 「) |
| `haganai_remaining_EN_full_v30.csv` (terbaru; juga v2, v6, v25_clean, v26_clean, v27) | 7.436 baris: narasi/dialog 5.817, scene title 673, banter 610, choice 336. Kolom: `scene, inst_index, opcode, str_index, kind, jp_text, jp_clean, english_text`. Kunci: `scene`+`inst_index` (+`str_index`) |
| `FULL_dialogue_wrap_fixed.csv`, `FULL_remaining_wrap_fixed.csv` | Versi lama (di-wrap, sudah dipendekkan 1.429 baris). **Jangan dihapus** |

Sebaran speaker: Kodaka 4.697, Yozora 2.646, Sena 2.207, Rika 1.775, Kobato 1.241, Maria 1.193, Yukimura 1.135, Tenma 120. Status patch `kind`: narasi/dialog dan choice dipatch; scene title dan banter dilewati.

**Rekomendasi pasangan terbaru:** `haganai_dialogue_EN_v30.csv` + `haganai_remaining_EN_full_v30.csv` (+ `changelog_v25_clean.csv`, `changelog_v27.csv`).

| Rilis | Catatan |
|---|---|
| v6 | Paket lengkap (260 revisi dialog) |
| v15 / v19 / v25 | Update parsial remaining; v25 memuat "—" dan "…" berisiko ♠; angka changelog v19/v25 menyesatkan |
| **v25_clean** | v25 dengan "—"→"--", "…"→"..." (13 baris), 286 baris narasi beda dari v6 |
| v27 | + 674 narasi overflow diganti; dialog via `apply_dialog_v27.py` |
| **v30** | + 130 dialog dan 1 narasi dari sisa overflow (v28-v30) |

Peringatan: teks hasil poles lebih panjang (rata-rata ~85→97 karakter pada baris yang berubah); baris > 140 karakter naik 2→12.

### 4.3 Tambalan pemendekan lama (`fixes_*.csv`)
Semua diterapkan, total **1.429 baris** (batch awal sampai `fixes_batch16`, diterapkan 2026-10-17; sisa 5.341). Format batch ≥ 10: `type,scene,ref,speaker,jp,english_new,lines,cut`. Dibekukan; simpan sebagai catatan.

### 4.4 Choice dan hasil build
- Choice (semua sudah diterapkan, jangan dijalankan ulang): `choice_full` (818), `choice_todo` (29), `choice_todo_terisi` (29, sudah `fill-todo`), `choice_fixes (1)` (209/209), `choice_fixes_todo` (20/20).
- Hasil build: `RES_patched_vN.DAT` + `first_new_vN.dat` (**selalu satu pasang**), `skip_vN.csv`, `overflow_vN.csv`, dump `dump_choice/fail/scene.txt`, `index_preview.txt` (isi `0000Index`), `jumpscan.txt`.
- Skip v14: 37 baris (10 `0000Index` "jumlah pilihan beda", aman diabaikan; 27 "english_text kosong").

### 4.5 Yang boleh diarsipkan
Pindah ke `arsip`, hapus setelah v30 dites: sisa tes `*_0011ess0.obj`, hasil kalibrasi (`TEST_*`, `dlg_ruler*`, `rem_*`, `first_ruler*`, `RES_lines.DAT`), build lama `v3-v11` (simpan pasangan terbaru), backup `.bak`/timestamp, `haganai_dialogue_EN_v28/v29`, `overflow_after_v28/v29`. **Jangan dihapus:** `FULL_*_fixed.csv`, `fixes_batch*.csv`, `choice_*` berstatus diterapkan, `index_preview.txt`, `jumpscan.txt`.

### 4.6 Lokasi CSV (sejak 2026-10-22)
Semua CSV kerja dipindah ke `scripts tools\csv`; skrip, build, backup `FULL_*.bak`, dan `envpsp.dat` tetap di `scripts tools`. Akibat:
- Beri awalan `csv\` pada argumen CSV. Tidak ada path CSV tertanam di `csv_tools.py` / `apply_dialog_v27.py`.
- `csv_tools.py fix`, `choice-fixes`, `choice-short` menulis hasil + `.bak` **di folder masukan**.
- Keluaran tanpa path ditulis di folder perintah dijalankan: `index_preview.txt`, `choice_terlalu_panjang.csv`, `fixed_output.csv`, `verify_report.csv`, `apply_dialog_v27_mismatch.csv`. Beri `csv\` pada `--out/--output/--worklist` bila perlu.
- `README.md` ada di dua tempat; jadikan satu induk (di `scripts tools`) dan arsipkan salinan lain.

### 4.7 Folder `Ui menu` (2026-10-22/23)
`out_menu` (hasil `cut_gpda --small`), `out_v14_menu`, `out_v27`, **`out_v30`** (pasangan RES+first dengan menu Inggris; masukan `patch_block.py`), `menu_patch.zip` (12 GIM), `menu_patch_v2.zip` (+16 sprite sistem), `menu_patch_v3.zip` (+20 sprite Extras; **ekstrak ke `scripts tools`**, bukan `Ui menu`), `block_patch_v1.zip` + folder `block_patch\`, `preview_menu_ui_english.png`, `out_menu.rar`. Perintah lama yang menyebut `.\out_v30` dst. kini perlu awalan `"Ui menu\"`. `scripts tools\out_v30` adalah versi lama (13 sprite); pakai `Ui menu\out_v30`.

### 4.8 Lokasi `envpsp.dat`, minigame, dan skrip baru (2026-10-23)

| Item | Path (dasar `D:\Reverse engginering\project haganai`) | Catatan |
|---|---|---|
| `envpsp.dat` **asli** | `data ekstrak\envpsp.dat` | 45.711 byte, MD5 `3962d0e9b9534f9590eb8d7e7360b569`, semua Jepang (tanggal ubah 2026-10-20: cek MD5) |
| Salinan asli kerja | `scripts tools\envpsp.dat` | **jangan jadi masukan skrip dialog** |
| **`envpsp.dat` kena skrip lama** | `scripts tools\envpsp_variants\envpsp.dat` | **47.775 byte, masukan benar skrip dialog** (MD5 file unggahan `712ca8eb...`) |
| Salinan 47.775 lain | `script_output\file final\...\patch final v1\envpsp.dat` | MD5 belum dicek |
| Hasil uji pada file asli | `scripts tools\envpsp_en.dat` | 46.257 byte, **jangan dipasang** (menu lain masih Jepang) |
| EBOOT terdekripsi | `scripts tools\ULJS00459_EBOOT.BIN` | 4.953.616 byte, ELF; tanpa teks dialog |
| Varian EBOOT geser Y | `scripts tools\envpsp_variants\EBOOT_Y13.BIN` (juga Y8, Y18, Y34, S66, S72, S80, ...) | **Y13 berhasil** |
| Potongan minigame | `scripts tools\out_block\image_block.dat` | 16.134.144 byte |
| Build menu terbaru | `scripts tools\Ui menu\out_v30\RES.DAT` + `first.dat` | |
| Build terbaru (basis) | `scripts tools\RES_v30_flow_test.DAT` + `first_new_v30_flow_test.dat` | Pasangan terbaru menurut pemilik (2026-10-24); isi "flow_test" belum dijelaskan di README |
| Build + nama Inggris | `scripts tools\RES_v31_names.DAT` + `first_new_v31_names.dat` | Hasil `patch_names.py` dari basis di atas; **dikonfirmasi Yozora di game** |
| EBOOT terbaru | `scripts tools\envpsp_variants\EBOOT_S72_W72_CHOICE72.BIN` | Menurut pemilik EBOOT terbaru (bukan lagi Y13); semua `EBOOT.BIN` di `scripts tools` berstempel 20 Okt 1:56:18, 4.953.616 byte |
| **Folder game (set pasang aktif)** | `script_output\file final\file final masalah injek gamenya 00006 error bosok\patch final v1\` | `RES.DAT`, `first.dat` (v31_names), `EBOOT.BIN` (20 Okt; ukuran sama dengan S72; hash belum dicocokkan), `envpsp.dat` (48 KB, 23 Okt 19:00 = **terbaru**), `cadang v14\` |
| Salinan data di memstick | `D:\Reverse engginering\tools\ppsspp_win\memstick\PSP\SAVEDATA\ULJS00459DAT\` | `RES.DAT` + `PARAM.SFO`, `ICON0.PNG`, `PIC1.PNG`. **Game menyalin RES ke sini; `RES.DAT` di sini ikut ditimpa tiap pasang** |

File asli di `data ekstrak` (jangan ditimpa): `EBOOT.BIN` (4.838 KB; terenkripsi atau tidak belum dicek), `envpsp.dat` (45 KB), `first.dat` (1.028 KB), `font.dat` (466 KB, 477.184 byte), `RES.DAT` (402.360.320 byte), `script_dat_extracted.dat` (166.508.544 byte). Cek MD5: `Get-FileHash "<path>" -Algorithm MD5`. **Folder game** kini tercatat di tabel di atas (`patch final v1` + salinan memstick).

---

## 5. Cara menjalankan

```
cd "D:\Reverse engginering\project haganai\scripts tools"
```
CSV kini di `csv\` → awali nama CSV dengan `csv\`.

### 5.1 Memendekkan (dibekukan; untuk referensi)
```
python csv_tools.py fix --worklist next_all.csv --limit 0 --max-lines 2 --width 35 --nwidth 37 FULL_dialogue_wrap_fixed.csv FULL_remaining_wrap_fixed.csv
python csv_tools.py fix --max-lines 2 --width 35 --nwidth 37 fixes_batchN.csv FULL_dialogue_wrap_fixed.csv FULL_remaining_wrap_fixed.csv
```
Yang kedua harus `ditolak: 0 | tidak ketemu: 0`. Batch berurutan, jangan dua kali. Selalu sertakan `--width 35 --nwidth 37`.

### 5.2 Build
Build terjemahan penuh (pola v14/v30; `pipeline.py` belum punya `--width2` per 2026-10-22):
```
python pipeline.py "D:\Reverse engginering\project haganai\data ekstrak\RES.DAT" csv\haganai_dialogue_EN_v30.csv csv\haganai_remaining_EN_full_v30.csv RES_patched_v30.DAT --max-lines 3 --width 35 --nwidth 37 --report skip_v30.csv --overflow overflow_v30.csv
python seekmap_rebuild.py build RES_patched_v30.DAT "D:\Reverse engginering\project haganai\data ekstrak\first.dat" first_new_v30.dat
```
Build v13 (hanya bila `--width2` terpasang): `--max-lines 2 --width 36 --width2 38 --nwidth 38`. Keluaran benar mencetak langkah `[1/5]`-`[5/5]`. Pasang RES + first.dat **sebagai pasangan**; jangan tes lewat save state.

### 5.3 Pasang patch menu/sprite (harus diulang tiap build RES baru)
```
Expand-Archive ".\Ui menu\menu_patch_v3.zip" -DestinationPath "." -Force
python menu_patch\tambah_extras.py menu_patch "Ui menu\out_menu"      # +20 baris (total 48)
cd menu_patch
python patch_menu.py "..\RES_patched_v30.DAT"                          # 62 sprites patched, 0 too big
cd ..
python seekmap_rebuild.py build "RES_patched_v30.DAT.patched" "<first.dat asli>" "first_new_v30_menu.dat"
Copy-Item "RES_patched_v30.DAT.patched" ".\Ui menu\out_v30\RES.DAT" -Force
Copy-Item "first_new_v30_menu.dat" ".\Ui menu\out_v30\first.dat" -Force
```
Gagal? `0 sprites patched` = MD5 tidak ketemu; `!! too big` = gz baru tak muat slot; game blank = `first.dat` belum di-rebuild dari `.patched`.

### 5.4 Pasang sprite minigame (pakai RES yang sudah kena patch menu)
```
Expand-Archive "Ui menu\block_patch_v1.zip" -DestinationPath "." -Force
cd block_patch
python patch_block.py "..\Ui menu\out_v30\RES.DAT" --check          # harapan 18 JEPANG
python patch_block.py "..\Ui menu\out_v30\RES.DAT"                  # 18 dipatch, 0 too big
python patch_block.py "..\Ui menu\out_v30\RES.DAT.patched" --check  # 18 INGGRIS
cd ..
python seekmap_rebuild.py build "Ui menu\out_v30\RES.DAT.patched" "<first.dat asli>" "first_new_v30_block.dat"
Copy-Item "Ui menu\out_v30\RES.DAT.patched" "Ui menu\out_v30\RES.DAT" -Force
Copy-Item "first_new_v30_block.dat" "Ui menu\out_v30\first.dat" -Force
```
Bila folder `block_patch` sudah di `Ui menu`, sesuaikan path.

### 5.5 Pasang `envpsp.dat` dialog (urutan benar)
```
Copy-Item "envpsp_variants\envpsp.dat" "envpsp_menu.dat"
python patch_envpsp.py envpsp_menu.dat --check           # harapan JEPANG 31
python patch_envpsp.py envpsp_menu.dat envpsp_final.dat
python patch_envpsp.py envpsp_final.dat --check          # harapan JEPANG 0
```
Ganti nama `envpsp_final.dat` → `envpsp.dat`, **cadangkan** yang lama di folder game, timpa, tes tanpa save state. Crash/layar hitam: kembalikan cadangan (dugaan batas buffer loader; perpendek teks).

### 5.6 Patch EBOOT geser Y
`python patch_eboot.py ULJS00459_EBOOT.BIN EBOOT_Y13.BIN 13` (pasang bersama RES+first).

### 5.7 Choice (sudah dijalankan 2026-10-16; catatan, jangan ulang)
`csv_tools.py fill-todo` dulu, lalu dua `choice-fixes` (29 terisi, 209/209 dan 20/20).

---

### 5.8 Ganti nama pembicara (2026-10-24; berhasil, `Yozora` tampil di game)
Dari `scripts tools`, di atas RES yang sudah dipatch (`patch_names.py` dan `pipeline.py` harus ada di folder ini):
```
python patch_names.py RES_v30_flow_test.DAT --check                 # harapan: 15.014 diganti, 0 scene error
python patch_names.py RES_v30_flow_test.DAT RES_v31_names.DAT
python seekmap_rebuild.py build RES_v31_names.DAT "D:\Reverse engginering\project haganai\data ekstrak\first.dat" first_new_v31_names.dat   # harapan 15.698/15.698
```
Pasang (setelah kedua file keluaran ada; periksa prompt PowerShell ada di folder yang benar):
```
$src = "D:\Reverse engginering\project haganai\scripts tools"
$pf  = "D:\Reverse engginering\project haganai\script_output\file final\file final masalah injek gamenya 00006 error bosok\patch final v1"
$sv  = "D:\Reverse engginering\tools\ppsspp_win\memstick\PSP\SAVEDATA\ULJS00459DAT"
Copy-Item "$src\RES_v31_names.DAT" "$pf\RES.DAT" -Force
Copy-Item "$src\first_new_v31_names.dat" "$pf\first.dat" -Force
Copy-Item "$src\RES_v31_names.DAT" "$sv\RES.DAT" -Force
```
`EBOOT.BIN` dan `envpsp.dat` tidak diubah. Tes: scene `0011ess0` (teras), tanpa save state. Cadangkan RES/first lama dulu bila perlu (`cadang v14`, `cadang flow_test`). Pemetaan: 夜空 Yozora, 星奈 Sena, 幸村 Yukimura, 理科 Rika, 小鳩 Kobato, マリア Maria, 天馬 Tenma, 小鷹 Kodaka.

---

## 6. Aturan kerja

| Jenis | Lebar | Tinggi | Target |
|---|---|---|---|
| Dialog | 35 kolom (ketat) | maks 2 baris | ~58 karakter |
| Narasi | 37 kolom | maks 2 baris | ~66 karakter |
| Choice | 22 kolom (sementara) | 1 baris | 36 batas keras |

Tabel berlaku untuk kotak 2 baris dan akan diganti setelah Fase A; **jangan memendekkan hanya demi tabel ini**. Untuk 3 baris, simulasi menunjukkan v27 aman pada lebar 38 (narasi 0, dialog 0 > 3 baris); pada 36: 2 dan 8; pada 37: 1 dan 2.

1. Hitung dulu, baru tulis (`csv_tools.py fix`). 2. Pendekkan hanya yang tembus 3 baris. 3. Makna utuh: boleh buang pengulangan; tidak boleh buang nama, angka, inti. 4. Hanya kolom `english_text` yang diubah. 5. Choice bersebelahan tetap beda. 6. Pakai `’` (U+2019) di file batch, bukan `'` (dialog v30 pakai `'` ASCII mengikuti mayoritas CSV dialog; narasi pakai `’`). 7. Istilah tetap: Meat, Onii-chan, Aniki, senpai, nama karakter. 8. Hindari karakter ♠: `'`, `"`, `\n`, `é`, `①`, `…`, `—`, `π`.

---

## 7. Temuan tentang engine game

### 7.1 Kalibrasi PPSSPP v1.20.4 (scene 0011ess0)
- Kotak asli **2 baris**; baris ke-3 jatuh di tepi bawah. Teks Jepang asli tak pernah > 2 baris (~27-28 karakter/baris; terpanjang 51; 0 baris > 56).
- Lebar huruf Inggris ≈ 37 kolom (narasi), dialog ≈ 35; lebar 39 membuat `shoul / d`. Kapasitas engine ≈ **38 kolom**.
- Metrik `pipeline.py`: ASCII = 1, `’` = 1,5, non-ASCII lain = 2. `'` ASCII, `"` ASCII, `\n` tampil ♠; engine melipat baris sendiri.
- Choice: gelembung ≈ 19 karakter; teks lebih panjang keluar gelembung tapi terbaca; batas layar ≈ 41.
- Geometri kasar (layar PSP tinggi 272): jarak baris ≈ 21 px; pusat baris 1 ≈ y230, 2 ≈ y251, 3 ≈ y272 (terpotong); pita kotak mulai ≈ y204. Geser naik 12-14 px cukup.

### 7.2 "Huruf nyelip"
Huruf pertama kata berikutnya muncul di ujung baris atas (`the N / eighbors`). Penyebab: `wrap_pad` mengisi baris dengan spasi sampai `--width` lalu menyambung tanpa pemisah; kapasitas engine ≈ 38 sehingga sisa 1-3 kolom ditempati huruf berikutnya. Perbaikan: `--width2` (lebar baris 2+) dan pad ke 38 (`--width 36 --width2 38 --nwidth 38`). Menurunkan lebar tidak membantu. Baris 1 dialog kehilangan ~2 kolom karena `「`.

### 7.3 Aturan lebar karakter di EBOOT (belum dibuktikan di game)
Penggambar string `0x1ad8d4` memakai dua kelas: `a-z A-Z 0-9 spasi :` = **0,7** x lebar sel; semua lainnya (tanda baca, `’`, `…`, kana, kanji) = **1,0**. Cocok dengan rasio Jepang:Inggris 1,42 dan `’` ≈ 1,5. Bila tes `ruler2` cocok, `cw()` di `pipeline.py` harus diganti ke metrik 7/10. Belum diketahui: posisi Y dan jarak baris (loader `0x2c2024`), apakah lebar sel sama untuk dialog dan narasi.

### 7.4 EBOOT terdekripsi
PPSSPP v1.20.4: **Settings → Tools → Developer tools → Dump files → "Dump decrypted EBOOT.BIN on game boot"**, buka ulang game; hasil `ULJS00459.BIN` di `memstick\PSP\SYSTEM\DUMP\` (ELF PRX MIPS). Offset file = vaddr + `0xc0`. Alternatif: `pspdecrypt` (John-K) → ELF 4.953.277 byte.

### 7.5 Temuan lain EBOOT dan font
- Glyph: ASCII 33-125 → fullwidth Unicode (`+0xFEE0`), spasi → spasi ideografis; pencari glyph `0x1ad430`, penggambar `0x1ad77c`. Tabel glyph **bukan** `font.dat`.
- `font.dat`: GPDA 6 gambar `01-06.gim.gz` (atlas bitmap, bukan tabel lebar).
- `envpsp.dat` (45.711 byte): string sistem UTF-16 + stream biner campuran (lihat 7.7).
- Tabel perintah script (~80 nama): `ScriptMessage`, `ScriptNextPage`, `ScriptSelect`, `ScriptGotoLabel`, `ScriptGotoFile`, dll.; pemetaan nama→opcode belum diketahui.
- Urutan file boot: `RES.DAT` (bertahap), `font.dat`, `envpsp.dat` (utuh), `first.dat` (1.052.672), lalu audio/video. `envpsp.dat` dan `font.dat` ada di ISO `PSP_GAME\USRDIR`.
- PPSSPP: matikan **Log to file** / **debug logging** (log ±72 MB per boot, lambat).

### 7.6 Hasil bongkar EBOOT (2026-10-19)
ELF PRX tipe `0xffa0`. Segmen 0: file `0xc0`, vaddr 0, `0x305468`; segmen 1: file `0x381580`, vaddr `0x381488`. Penggambar string `0x1ad8d4`: `a0` font, `a1` string, `a2` perataan, `a3` posisi, `f12/f13` skala H/V. Pemanggil hanya 4 (`0x1fc5dc`, `0x1fc720`, `0x230074`, `0x233590`). Parameter dibaca dari global bss segmen 1 (x `+0x1955c`, y `+0x19560`, skala `+0x19568`) yang diisi loader `0x2c2024` dari stream (`0x295b74` float, `0x295bc4` int). Jangan anggap `+0x19568` = skala dialog sebelum dites.

### 7.7 Hasil bongkar `envpsp.dat` (2026-10-19)
MD5 `3962d0e9...`. Format stream (semua baca lewat `0x15fcfc`): `0x295e8c` u8; `0x295bc4` int32; `0x295b9c` u32 warna ARGB; `0x295b74` float32; `0x2d80fc` string = u32 jumlah karakter + UTF-16LE. File diawali `01 00` lalu string `ULJS00459`. Kandidat skala (`0x24b6`, `0x2c70`: float 0,8 di (170,14)/(472,14)) adalah posisi atas layar, bukan dialog. Emulasi Unicorn berhenti di byte 789 (vektor global null); jalur ini ditinggalkan karena Y13 berhasil.

### 7.8 Geser Y EBOOT dan varian `envpsp.dat` (2026-10-20)
`patch_eboot.py` mengubah **satu instruksi** di vaddr `0x1ad7b8` (file `0x1ad878`, di penggambar glyph `0x1ad77c`): `0x00e09025` (`move $s2,$a3`) → `addiu $s2,$a3,-geser`. EBOOT sumber MD5 `2056ae231e9bf9e07649092e408974fb`. Y8/Y18 dibuat (hasil tak dilaporkan); **Y13 berhasil**. Efek samping: semua teks lewat jalur itu naik, termasuk choice (R-A7); pemenggalan berbasis karakter (R-A8); ±35-36 kolom/baris. Varian `envpsp.dat` A-E (skala x0,6) tidak dipakai lagi (D hang).

### 7.9 Sprite menu judul (selesai)
Menu judul = sprite GIM (`MIG.00.1PSP`, 8 bpp palet 256, swizzle): 6 sprite diam 64x56 (tutorial 128x56) + 6 sheet 256x56; pasangan 124/125, 126/127, 132/133, 134/135, 139/140, 141/142 (pemetaan nama→nomor perkiraan). `patch_menu.py` menimpa di slot sama; `first.dat` harus di-rebuild dari `.patched`. Dikonfirmasi Inggris di game (v30). Sisa: label terpotong tepi kanan.

### 7.10 Backlog
Backlog menampilkan judul sprite, label tombol, judul scene (`プロローグ`, op700), dan isi log (teks script). Kejanggalan di satu screenshot: `this isa` (spasi pad terbuang saat sambung baris?) dan ukuran huruf berbeda (`hallucina`+`tion.`); belum diselidiki. Ulangi dengan beberapa kalimat sebelum menyimpulkan.

### 7.11 Inventaris sprite UI
`out_menu` berisi `image_main.dat` (109), `image_title.dat` (145; dibungkus, banyak kembar MD5 dengan `image_main`), `omake.dat` (89 thumbnail CG, tidak perlu diubah), `image_cutin.dat`, `image_rinzin_icon.dat` (6), `main_resource.dat` (bukan GIM). GIM: blok gambar (tipe 4) dan palet (tipe 5), data mulai di `+0x1C` isi blok; `fmt 5` = 8 bpp, `fmt 4` = 4 bpp; urutan 1 = swizzle 16x8; 4 bpp nibble bawah dulu.

16 sprite Inggris v2 (kembar ditimpa sekaligus): System Menu (`image_main` 89), Backlog (4), Details (16), Flowchart (30), Keyword List (42), Load (45), Save (100), Quick Load (66), Options (63), Text/Music/Other Settings merah+putih (61/62, 57/58, 55/56), Auto/Skip (75). Dibuat dari templat dengan font FreeSans Bold Oblique (**bentuk huruf beda dari font game**). Belum dikerjakan: `image_main` 73 (`操作説明` panduan tombol). Label di grid System Menu dan layar Options (`Save`, `Load`, `Message Speed`, ...) berasal dari **teks font** (envpsp), bukan sprite.

### 7.12 Sprite Extras dan hasil tes menu v2 (2026-10-23)
Tes v2: Inggris untuk System Menu, Backlog, Keyword List, header Options, tombol (`Backjump`, `Toggle View`, `Play`, `Back`, `Select`). Cacat: tab Options terpotong (`Text Settin`, `Music Set`, `Other Setting`), judul Keyword List terpotong kanan, `戻る` Keyword List Jepang, dialog Backlog jarak huruf lebar dan kata terpotong, serpihan kecil di label Extras Jepang (belum diketahui ada di game asli atau tidak), kotak putih kosong di Options/System Menu (belum dibandingkan dengan game asli). 13 sprite `image_title` gagal dibaca (`*_bg` dll.) dan tulisan latar raksasa tetap Jepang.

20 sprite Extras (v3): banner `Extras` (`image_main` 64 / `image_title` 107), judul layar `Event CG` (0_3/0_6), `Movies` (0_49), `Music` (0_52), `Bonus Story` (0_86), `Scene Replay` (0_111), 14 label ikon (0_87-0_100: `Block Break`, `Event CG`, `Music`, `Movies`, `Scene Replay`, `Flowchart`, `Bonus Story`). Label ±8 px (`Scene Replay` terkecil). `Bonus Story` untuk `おまけシナリオ` adalah keputusan terjemahan yang bisa diubah. `originals.txt`: MD5 = MD5 GIM yang sudah di-gunzip (28→48 baris). Hasil pasang: 62 sprite (40 lama + 20 baru + 2 kembar), seekmap 14.071 baris berubah, gz 180.623 byte (slot 182.272), 15.698/15.698 cocok.

### 7.13 Minigame Block Kuzushi dan dialog konfirmasi (2026-10-23)
**A. Minigame.** `image_block.dat` (RES offset `0x0a59e000`, 16.134.144 byte, 7 anak, 366 sprite terbaca). Jepang: `title.dat` (menu judul), `game_sharing.dat` (banner, pause). 18 sprite Inggris: menu judul **Start / Gallery / Controls / Quit** (8 sprite diam+sheet); banner **STAGE CLEAR!! / ALL CLEAR!!! / GAME OVER! / GAME START!**; pause **Back to Game / Character Select / Return to Title**; akhir **Next Stage / Retry**; tombol kuas **Continue / Character Select / Title / Next / Retry** (`bd_pmenu`). Uji `patch_block.py` pada container: 18 JEPANG → 18 INGGRIS, 0 too big; **belum diuji pada RES.DAT penuh dan PPSSPP**. Risiko: teks engine `Select`/`Back` menimpa label (sudah bertabrakan dengan `ギャラリー` dan `そうさせつめい`); bila terjadi, buat v2 dengan label digeser 6-8 px naik. Container RES lain (offset/ukuran): `image_bg` `0x09e98000`/7.364.608, `image_cutin` `0x0b501000`/10.240, `image_event` `0x0b503800`/8.255.488, `image_main` `0x0bce3000`/387.072, `image_map` `0x0bd41800`/3.684.352, `image_rinzin_icon` `0x0c0c5000`/43.008, `image_title` `0x0c0cf800`/712.704, `live2d` `0x0c17d800`/21.401.600, `main_resource` `0x0d5e6800`/71.680, `omake` `0x0d5f8000`/1.146.880, `script` `0x0d710000`/166.508.544, `system_voices` `0x175db800`/10.342.400.

**B. Dialog konfirmasi.** EBOOT terdekripsi **tidak** memuat teks dialog (hanya string debug `はい`/`いいえ` di `0x306f0b`, `0x307418`, `0x30741e`). Teksnya ada di **`envpsp.dat`**: record u32 jumlah karakter + UTF-16LE. **Penanda:** `_` (ASCII) = pindah baris; `＿` (U+FF3F) = pemisah pilihan. Contoh offset di file 47.775 byte: `0x3592` kembali ke judul; `0x35bc` `はい＿いいえ`; `0x35cc` kembali ke Scene Replay; `0x35f8` Extra Scenarios; `0x362c` simpan data sistem; `0x365c` `はい＿いいえ＿戻る`; `0x3a86` save; `0x3a9a` load; `0x3aae` quick load; `0x4d1c` backjump; `0x4f84` simpan perubahan; `0x65ac` reset pengaturan; `0x661c` perubahan tak tersimpan; `0x773a`-`0x781e` simpan/timpa/muat.

**Dua versi file:** asli 45.711 byte; 47.775 byte = asli + skrip lama (rentang `0x1E00`-`0xAB00`, +2.064 byte; menjalankan skrip lama pada 47.775 byte → 0 diganti). Dua `戻る` di luar rentang lama (`0x1a3b`, `0xb614`) tetap Jepang; skrip dialog menggantinya. Skrip dialog: 21 jenis string, cocok persis, `--check`; uji pada 47.775 byte: 31 JEPANG → 0 (→ 48.149 byte); uji pemilik pada file asli: 74 → 0 (→ 46.257 byte, **jangan dipasang**). Terjemahan: `Return to the title screen._Are you sure?`; `Save system data. Is this OK?`; `Yes＿No＿Back`; `Return to Scene Replay._Are you sure?`; `Return to Extra Scenarios._Are you sure?`; `Quick Load. Is this OK?＿*All Quick Saves made after this_point will be deleted.` dst. (daftar penuh `TABLE` di `patch_envpsp.py`).

**C. Sisa Jepang di `envpsp.dat`** (±355 dari 645 record): nama keyword (`0x16xx`-`0x19xx`), judul extras/ending (`0x266c`-`0x2a86`), `コンプリート率：`, nama BG/lokasi (`0x3c0a`-`0x4938`: `ビーチ`, `テラス`, `別荘外観`, `部室A`), judul chapter (`0x4954`-`0x4ac4`, `0x7bd4`-`0x7d44`), pesan instalasi/media (`0x6714`-`0x7b68`), `１曲リピート`, komentar musik (`0x973a`-`0xaa20`), judul extras (`0xac32`-`0xaee6`), `キャラ１`-`７`, item minigame (`0xb800`-`0xb872`: `爆弾ボール`, `巨大ボール`, `バリアー`, `ワイドパドル`). Daftar lengkap: `envpsp_strings.txt`.

**D. Kesalahan dugaan.** (1) `cari_string.py` sempat dikira jalan; file tidak ada di folder sehingga `hasil_res.txt`/`hasil_first.txt` kosong tidak membuktikan apa pun. (2) Dialog bukan di EBOOT. (3) Skrip dialog sempat dijalankan pada file asli, bukan yang 47.775.

**E. Hasil tes (2026-10-23 malam, PPSSPP v1.20.4).** Kembali ke judul: `Return to the title screen. / Are you sure? / Yes / No`; simpan data sistem: `Save system data. Is this OK? / Yes / No / Back`; label menu (`Save`, `Load`, `Quick Save`, `Quick Load`, `Quit`, `Flowchart`, `Keyword List`, `Controls`, `Options`) dan tombol `Select`/`Back` Inggris; tanpa crash. Masih: `プロローグ` Jepang (R4.12); dua-tiga huruf pertama (`Re`, `Sav`) tampak lebih besar (mungkin animasi; bandingkan dengan dialog Jepang asli); jarak antar-huruf lebar (R-A8). Ukuran file terpasang dan `--check` tidak dilaporkan.

---

## 8. Format data game

Hasil membaca langsung `RES.DAT` (`RES_1.DAT`) dan `first.dat` dengan parser GPDA terpisah.

### 8.1 Identitas
| Berkas | Ukuran | MD5 |
|---|---|---|
| `RES_1.DAT` (Jepang belum dipatch) | 402.360.320 | `eb970327b53649525ab4ee5d013f303f` |
| `first.dat` | 1.052.672 | `e9b87cec00e5c81057225b61ed3b1e13` |

Seekmap `first.dat` cocok di semua 15.698 node dengan `RES_1.DAT`.

### 8.2 Container GPDA
Diverifikasi pada 4.817 container, 0 pelanggaran.
```
+0 "GPDA" | +4 u64 ukuran total | +12 u32 jumlah entri N
+16 N x 16 byte: u64 offset (relatif container), u32 ukuran, u32 offset nama
tabel nama: u32 panjang + UTF-8 (panjang termasuk 1 spasi akhir, "dummy.dat ")
```
Offset entri selalu kelipatan 2048; ukuran tidak dibulatkan. Nama di GPDA berspasi akhir; di seekmap tidak. Struktur: `RES.DAT` (14 entri) → `script.dat` (674 scene) → `_<stem>.dat` (5 entri/scene; entri 0 = GPDA 3 entri `.obj.gz`, `.dat.gz`, `.dat`; entri 1-4 = aset, mis. `BG*.gim`).

### 8.3 Isi `RES.DAT` (14 entri)
`dummy.dat` (`0x800`, 166.295.488, semua 0x00), `image_bg` (114 anak), `image_block` (7), `image_cutin` (1), `image_event` (119), `image_main` (109), `image_map` (25), `image_rinzin_icon` (6), `image_title` (2), `live2d` (3), `main_resource` (1), `omake` (2), `script` (674 scene), `system_voices` (14). Offset/ukuran: lihat 7.13-A. `dummy.dat` 41,3% file; `script.dat` 41,4%. Contoh `0011ess0`: scene 1.208.320 byte, `obj.gz` 4.324 → 14.304 byte.

### 8.4 Isi `first.dat` (9 entri)
`font_location.dat` (29.704), `image_sharing.dat` (GPDA 18: `ef_light`, `ef_rain`, `heart`, `load_0..2`, ...), `logo.dat` (6), `save.dat` (`ICON0.PNG`, `ICON1.PNG`, `PIC1.PNG`), `script.dat` (`zz1.tmp`, `zz2.tmp`, `zz3.tmp`; bukan script 674 scene, isi belum diperiksa), `seekmap.dat` (gzip, 180.830), `systemse.dat` (26 `SE*.hca`), `text.dat` (`scriptname.txt` 674 baris, `loadscriptimage.csv` 300 baris, `selist.txt` 221, `vl_flg.txt` 225 baris Shift-JIS `#define VL_KEYWORD_xxx`), `voice.dat` (kosong).

### 8.5 `seekmap.dat`
gzip berisi teks UTF-8 CRLF, 764.037 byte terdekompresi, **15.698 baris**; kedalaman = jumlah tab (per kedalaman 0-5: 1, 14, 1.077, 4.363, 10.167, 76). Berkas: `nama offset_absolut ukuran checksum`; container: + `0 jumlah_anak`. Akar: `resource.dat 0 402360320 984644159 0 14`. Container 4.817, berkas 10.881. `first.dat` **harus di-rebuild** tiap ukuran `script.dat` berubah. **Checksum belum teridentifikasi** (bukan CRC32/Adler32); tak memengaruhi verifikasi.

### 8.6 Script `.obj` dan opcode
**674 scene, 0 gagal parse, 99.708 instruksi** (min 7, maks 875 di `0090ess0`). Format: `u32 jumlah_instruksi`, `u32 offset pertama` (selalu `0x30`), stempel UTF-16, lalu instruksi: `u32 ukuran`, `u16 opcode`, field khusus. `0011ess0` = 356 instruksi. **Target pilihan (op103) = nomor instruksi**, jadi mengubah ukuran instruksi aman. Opcode goto belum teridentifikasi (op1 berisi angka mirip ID flag; op104 hanya di `zModelTest`).

Statistik (58 opcode): **1500** 47.451; **100** 21.096 (dialog/narasi; ukuran 64: 4.942, 80: 4.404, 48: 4.372, 96: 3.550, 112: 2.307, ≥128: 1.521); 202 3.802; 227 2.726; 204 2.350; 703 1.717; 212 1.447; 601 1.400; 229/226 1.337/1.313; 106 1.309; 201/600/301 ±1.190; 1800/300/200 799/761/694; **700** 674 (judul scene); 701 674; 702 515; 1012/1013/1014 445/245/210 (kandidat banter); **103** 95 (choice); 104 32. 33 opcode lain lebih jarang.

### 8.7 Dialog dan narasi (op100)
| Posisi | Isi |
|---|---|
| `+0` | u32 ukuran |
| `+4` | u16 opcode (100) |
| `+7` | u16 (kemungkinan penghitung pesan) |
| `+9` | u16 **ID speaker** (`0xFFFF` = tanpa ID) |
| `+11` | u16 jumlah karakter n (**termasuk** tag ruby) |
| `+15` | teks UTF-16LE (alamat ganjil) |
| akhir | nol sampai ukuran = kelipatan 16 terkecil ≥ `15 + 2n + 4` (0 selisih dari 21.096) |

Speaker: 0 夜空 (2.584), 1 星奈 (2.146), 2 幸村 (1.077), 3 理科 (1.757), 4 小鳩 (1.157), 5 マリア (1.185), 6 天馬 (116), 7 小鷹 (4.441). `0xFFFF` ada di 6.633 baris (888 tetap berawalan nama; 5.745 narasi murni). Menurut awalan nama: 15.351 dialog + 5.745 narasi; 98 label speaker. **Tag ruby:** `≪RUBY≫dasar≪RT COLOR=#FFFFFF≫bacaan≪/RUBY≫` (`≪`=U+226A, `≫`=U+226B; 88 baris; n terbesar 814 di `a291sen0` inst#17). Teks Jepang: 520.059 karakter (rata-rata 24,7), maks 51, > 28: dialog 4.375 + narasi 2.611, > 56: 0.

**Nama pembicara (dikonfirmasi 2026-10-24):** `speaker_field` (dari `+15` sampai tepat sebelum `「`) berisi nama Jepang dalam UTF-16LE (`夜空「…」`). Plat nama di game menampilkan **teks ini**; menggantinya jadi `Yozora` mengubah plat, ID di `+9` tidak perlu disentuh. Header `+11` = panjang seluruh string termasuk nama. EBOOT tidak memuat nama (SJIS, UTF-16 LE/BE, UTF-8, kana, romaji: 0 hasil) dan `zz1-3.tmp` tidak berisi nama. Pada `0011ess0.obj.bin` terdeteksi 8 nama (25 dialog); di RES `flow_test`: 15.014 baris ber-awalan nama, 5.839 tanpa `「` di awal (narasi), 243 awalan tak dikenal.

### 8.8 Choice (op103)
95 instruksi di 71 scene, 1.118 opsi (`0000Index`: 13 instruksi, 794 opsi; sisanya 82 instruksi, 324 opsi). Format: `+6` u16 jumlah opsi; entri mulai `+10`: `u32 target`, `u32 panjang`, teks UTF-16LE, `u32 flag`. `flag = 1` (31 entri) diikuti ekstensi ≥ 6 byte (u32 1/2/5 + u16 0x31-0x3f); 76 dari 95 instruksi terurai bersih, 19 belum (mis. `0046rcs2` inst#22, `a076ess0` inst#166).

### 8.9 Yang belum diketahui
Opcode goto; checksum seekmap; isi `zz*.tmp` (tidak berisi nama pembicara), kolom `loadscriptimage.csv`, `vl_flg.txt`; format penuh ekstensi `flag=1`; pemetaan 1012/1013/1014 ke banter; selisih 22 baris (21.096 vs 21.074); `0000Index` tak terekstrak (belum dikonfirmasi).

---

## 9. Opsi untuk teks > 2 baris

| Opsi | Status |
|---|---|
| Memendekkan | **Dibekukan** |
| Geser teks naik 12-14 px | **Berhasil (Y13)**; sisa choice sejajar |
| Pecah dialog jadi dua kotak | Terblokir (opcode goto) |
| Ukuran font (skala float) | Tidak dikejar (Y13 cukup) |

**Pecah dua kotak:** dialog panjang dipecah jadi dua instruksi berurutan (speaker sama). Kendala: menyisipkan instruksi menggeser nomor instruksi; target op103 bisa digeser otomatis, tapi opcode pembawa target lain belum ketemu. Risiko: voice hanya di kotak pertama; apakah dua dialog menunggu tombol; animasi/ekspresi terulang; byte `+7` perlu diurutkan ulang. Langkah: `jumpscan2` (opcode tepat sebelum awal cabang pilihan ke-2+), tes 1-2 dialog.

---

## 10. Gerbang sebelum build dianggap beres

- [ ] Dialog dan narasi > 3 baris pada terjemahan penuh: 0 (hitung ulang dengan v30)
- [x] Choice kosong: 0 · [x] Choice > 22 kolom: 0 (belum diverifikasi ulang `long-choices --max 22`)
- [ ] Fase A: 3 baris terbaca penuh di game (tidak menabrak tepi atas, tidak terpotong bawah)
- [ ] Tes v12/v13: tidak ada huruf nyelip dan kata terbelah
- [ ] `csv_tools.py` disamakan dengan lebar baris 2+ bila v13 dipakai
- [ ] Screenshot 3-5 sampel terparah · [ ] `first.dat` sepasang dengan RES build sama
- [ ] Tes `ruler2` (`.`, `’`, `…` ≈ 24-25; `i` ≈ 39)
- [x] Menu judul Inggris di game · [ ] Menu pause dan Backlog Inggris penuh (judul scene, info chapter, nama pembicara)
- [ ] Skrip perapian dites pada data asli (R0.4)

---

## 11. Jebakan dan pelajaran

**Perintah dan file**
- Jalankan dari `scripts tools`; `FileNotFoundError` pada CSV = file tidak ada di folder itu (**CSV kini di `csv\`**).
- Placeholder `<...>`, `vN`, `path\ke\...` di contoh bukan nama file; **jangan jalankan blok template**. Mengetik path di PowerShell tidak membuka/menyalin file; pakai `Copy-Item`.
- File unduhan harus **menimpa** file lama (Replace), bukan `pipeline (1).py`. Berkas dari chat (`cari_string.py`, zip) harus disimpan di folder kerja dulu (`can't open file` = belum ada).
- Pasangan RES + `first.dat` harus dari build yang sama; setelah `patch_menu.py`, `first.dat` di-rebuild dari `.patched`. `patch_menu.py` tidak menimpa input; PPSSPP yang masih memuat RES biasa tetap Jepang.
- Pipeline selalu mulai dari RES asli → **patch menu/sprite hilang tiap build baru**; ulangi.
- `menu_patch_v3.zip` ke `scripts tools`; `out_v30` yang benar ada di `Ui menu`.
- Opsi baru tak dikenal (`--width2`) → pipeline mencetak bantuan dan berhenti tanpa file; error `seekmap_rebuild.py` hanya akibatnya.
- Jalankan `cut_gpda.py` dari `scripts tools`, bukan dari `C:\Users\...`.
- Jangan jalankan ulang 5.7 (choice) dan `patch_envpsp lama.py`. README lama bisa terkirim ulang; versi bertanggal terbaru yang benar.
- Pasang hanya **setelah** file keluaran ada, dan lihat prompt: menjalankan blok `Copy-Item` di folder yang salah menimpa file kerja (2026-10-24: `scripts tools\EBOOT.BIN` tertimpa, `cadang flow_test` tertimpa dua kali; tanpa dampak karena asli di `data ekstrak`). Jalankan blok cadangan sekali saja.
- Game membaca salinan di memstick (`SAVEDATA\ULJS00459DAT\RES.DAT`); timpa juga file itu, bukan hanya folder game.
- File skrip dari chat (`patch_names.py`) harus disimpan dulu ke `scripts tools` (`can't open file` = belum ada); lewat Notepad: Save as type **All files**, encoding UTF-8.

**Batch pemendekan:** terapkan berurutan (`tidak ketemu` > 0 = batch sebelumnya belum diterapkan); teks sama di banyak baris memakai satu terjemahan; `fix` tanpa `--width 35 --nwidth 37` menyesatkan; kutip ganda yatim dan salah arti (`0083mar0 0x5D73`, `a490ed11` inst#499, `omake_sen` inst#13) sudah dibersihkan batch 14/16.

**Tampilan di game:** kata terbelah (`shoul / d`) = lebar wrap > kapasitas; huruf nyelip = masalah lain (7.2); jangan menebak batas dari satu screenshot non-16:9; jangan tes lewat save state.

---

## 12. Riwayat

### 12.1 Overflow > 2 baris (cara lama)
5.636 (2026-10-15) → 5.453 (batch 8) → 5.303 (b9) → 5.103 (b11, lebar 37/39) → 5.841 (b11, **ketat 35/37**) → 5.741 (b12) → 5.641 → 5.541 → 5.441 → **5.341** (b16; dialog 3.359, narasi 1.982). Sejak batch 12 diukur dengan lebar ketat (angka sebelumnya tak sebanding).

### 12.2 Build
v10: apostrof, wrap, pilihan benar; baris ke-3 hilang. v12: `--max-lines 2 --width 35 --nwidth 37`, 15.698/15.698 cocok, tes belum dilaporkan. v13: belum jalan (pipeline lama). v14: terjemahan penuh (12.7). v25/v27/v30: lihat 12.10-12.14.

### 12.3 Perapian skrip (2026-10-19)
`jumpscan.py` → `dump.py opcodes`; parser seekmap tunggal (lebih ketat: baris tak dikenali = error); helper CSV tunggal; `tests.py fixsizes` dibuang; `make_choice_fixes.py` dihapus. Belum diuji pada data asli (R0.4).

### 12.4-12.6 Tes lama dan keputusan
Tes build lama: choice muat, `’` benar, huruf nyelip muncul. 2026-10-19: berhenti memendekkan, kejar 3 baris. 2026-10-20: Y13 berhasil; terjemahan penuh dipilih. Hitungan awal narasi > 3 baris: 767 (lebar 35), 587 (37). Choice di file penuh 336 vs 365 di catatan lama (selisih 29 belum dijelaskan); 209 dari 336 > 22 kolom.

### 12.7 Build v14 (2026-10-20)
Perintah: `pipeline.py ... haganai_dialogue_EN_v2.csv haganai_remaining_EN_full_v2.csv RES_patched_v14.DAT --max-lines 3 --width 35 --nwidth 37 --report skip_v14.csv --overflow overflow_v14.csv`. Hasil: dialog 15.257, narasi 5.817, choice 336 (67 scene); dilewati scene title 673 + banter 610; dipatch 602 file, 21.128 instruksi, 37 skip; RES 402.360.320 → 402.567.168; seekmap 14.004 baris berubah, 15.698/15.698 cocok; **1.649 teks > 3 baris** (dialog 1.034, narasi 615). Tes pertama: (1) 3 baris tampil penuh; (2) `"` ASCII tampil ♠ (213 baris: 1 dialog + 212 remaining; kandidat pengganti `“ ” 「 」 ’`, tes varian dulu); (3) huruf nyelip (pad 37 < kapasitas ≈ 38 → `--nwidth 38`, dialog perlu `--width2`); (4) teks 4 baris terpotong di baris ke-4. Sisa > 3 baris per lebar (dialog/narasi): 35/37 = 1.034/615; 36/38 = 880/525; 37/39 = 747/450. Choice: 211 dari 336 > 22 kolom. Keputusan terbuka: nasib teks > 3 baris, pengganti kutip ganda, pemendekan choice.

### 12.8-12.9 Menu judul dan pause (2026-10-20)
Sprite menu judul diperiksa, `menu_check.py` dibuat, patch berhasil (Inggris di game). Screenshot Backlog menunjukkan judul, tombol, judul scene Jepang plus dua kejanggalan teks; `cut_gpda.py` dibuat. Bahan yang dibutuhkan saat itu: screenshot semua layar pause, container `out_menu`, `first.dat` asli, `envpsp.dat`, EBOOT terdekripsi, satu scene asli (untuk op700).

### 12.10 Batch overflow v27 (2026-10-22)
Sumber `overflow_v27.csv` (kolom `sumber,kunci,jumlah_baris,english_text`): **1.644** teks (dialog 970, narasi 674; 4 baris: 1.537, 5 baris: 107). `fix_batch2`-`fix_batch17` = 1.679 baris, kunci unik, semua 1.644 tertutup (35 sisa daftar lama, dialog 5 baris dari batch 2). Batch: 2 (35 dialog), 3 (260: 194 dialog + 66 narasi), 4-8 (100 dialog), 9 (95), 10 (100), 11 (100: 76+24), 12-16 (100 narasi), 17 (89: 84 narasi + 5 dialog). Format: `sumber,kunci,jumlah_baris_lama,english_text_lama,english_text`; kunci dialog `file.dat 0xOFFSET`, narasi `scene instN`. Teks baru memakai `’`, maks 99 karakter; nama dan istilah tetap. Diterapkan: `haganai_remaining_EN_full_v27.csv` (674 berubah, 0 selisih makna setelah apostrof disamakan) + `changelog_v27.csv`. Dialog: 1.005 fix (`fixes_dialog_v27_all.csv`) → **922 masuk, 83 tidak cocok** (76 teks 4 baris, 7 teks 5 baris; 78 masuk daftar overflow dan ditulis ulang di v28-v30; **5 tidak overflow dan tetap lama**: `0081rcs0.dat 0x4E3`, `a072ess0.dat 0x4E3`, `a281ess0.dat 0x463`, `b089ess5.dat 0x1F13`, `b094ed11.dat 0x1D73`). Simulasi per kata (`’` = 1,5): lebar 38 aman (0/0); 37: narasi 1, dialog 2; 36: 2 dan 8.

### 12.11 Sisa overflow: v28-v30 (2026-10-22)
`overflow_after_v27.csv`: **131 teks** (dialog 130, narasi 1; 4 baris 95, 5 baris 34, 6 baris 2), semua ditulis ulang (0 kunci hilang/ganda). Batch: v28 (36; dialog 5-6 baris; maks 97 karakter), v29 (49; 4 baris terpanjang 111-130 karakter; maks 92), v30 (46; sisa 45 dialog + 1 narasi `a484ess0` inst 81; maks 88). `haganai_dialogue_EN_v30.csv`: 130 baris berubah dari v27; `remaining_v30`: 1 baris. Dialog baru memakai `'` ASCII, narasi `’`. Gaya tokoh dijaga (Kobato "kukuku", Yukimura "Aniki", Meat, senpai). Aturan lebar pipeline tak tersedia saat ditulis → **belum diverifikasi**.

### 12.12 Menu sistem dan build v30 (2026-10-22)
`first.dat` original/v14/v30 sama 1.052.672 byte, 29 blok gzip, hanya seekmap yang beda; `resource.dat` original 402.360.320, v14 402.567.168, v30 402.548.736 (CRC32 3282657181). Menu judul Jepang lagi di v30 karena `patch_menu.py` belum dijalankan; setelah dijalankan (13 sprite, bukan 12: `8_0_125_gz` kembar), 15.698/15.698 cocok, `first_new_v30_menu.dat` seekmap 764.143 byte, gz 180.626 byte; dikonfirmasi Inggris. Sisa Jepang tes v30: System Menu, info chapter, Auto, dialog konfirmasi, nama pembicara, Extras, header+tab Options. Dialog v30: jarak huruf lebar, kata terpotong (`ou / t`, `som / ething`, `w / aste`). Decoder GIM dibuat; 349 sprite dirender; 16 sprite v2 dibuat.

### 12.13 Menu Extras dan `menu_patch_v3` (2026-10-23)
Tes v2 (7 screenshot) → daftar cacat 7.12. `cari_string.py` dijalankan tanpa file/dengan path contoh → tanpa hasil. `out_menu.rar` dibongkar ulang, 20 sprite Extras dibuat, dipasang (62 sprite, 0 too big, 15.698/15.698). Baris contoh placeholder (`vN`, `<first.dat asli>`) sempat gagal tanpa efek. Pemilik: Extras Inggris "bisa".

### 12.14 Minigame dan teks dialog konfirmasi (2026-10-23 malam)
`out_menu.rar` ulang tidak berisi minigame; `image_block.dat` dipotong (`cut_gpda.py` dari `scripts tools`); 18 sprite dibuat (`block_patch_v1.zip`, 331 KB; belum dipasang). EBOOT tak berisi dialog; `envpsp.dat` berisi. Dua `patch_envpsp.py` dibedakan (lama diganti nama). Uji pemilik pada file asli: 74 → 0 (salah file). Tes game: dialog Inggris, tanpa crash.

**Langkah berikutnya:** [x] urutan 7.13-B pada `envpsp_variants\envpsp.dat` · [x] timpa `envpsp.dat` + screenshot · [ ] catat lokasi folder game (4.8) · [ ] pasang `block_patch_v1` dan tes · [ ] sprite minigame sisa (butuh screenshot pilih karakter, galeri, kontrol, game over, clear) · [ ] tes dialog `envpsp.dat` lain dan huruf besar · [ ] teks `envpsp.dat` lain (7.13-C) · [ ] bila crash: kembalikan cadangan, perpendek teks.


### 12.15 Nama pembicara (2026-10-24)
Screenshot teras (`0011ess0`): plat masih `夜空`. Pencarian: EBOOT terdekripsi tidak memuat nama (hanya string debug `chara_index`), `zz1-3.tmp` tidak berisi nama. `0011ess0.obj.bin` menunjukkan nama ada di dalam string dialog (`夜空「…」`); `pipeline.py` mempertahankan awalan itu karena kunci CSV adalah posisi `「`. Dibuat `pipeline_names.py` dan `patch_names.py`. `patch_names.py --check` pada `RES_v30_flow_test.DAT`: 15.014 diganti (Kodaka 4.697, Yozora 2.646, Sena 2.207, Rika 1.775, Kobato 1.241, Maria 1.193, Yukimura 1.135, Tenma 120; cocok dengan sebaran speaker 8.7), tidak diganti 5.839 (narasi) + 243 (awalan tak dikenal), 0 scene error. Keluaran: 600 scene diubah, RES 402.550.784 byte (sama), `first_new_v31_names.dat` 15.698/15.698 cocok. Dipasang ke `patch final v1` (RES + first) dan `SAVEDATA\ULJS00459DAT\RES.DAT`; `EBOOT.BIN` dan `envpsp.dat` tidak diubah. **Hasil: plat menampilkan `Yozora`.** Kesalahan proses sebelumnya dicatat di bagian 11.

**Langkah berikutnya:** [x] nama Inggris di plat · [ ] tes nama lain dan lebar plat (`Yukimura`) · [ ] periksa 243 awalan tak dikenal · [ ] cocokkan hash `patch final v1\EBOOT.BIN` dengan `EBOOT_S72_W72_CHOICE72.BIN` · [ ] dokumentasikan isi build `flow_test`
---

## 13. Lampiran: pencocokan klaim dengan data asli (2026-10-19)

| Klaim | Hasil |
|---|---|
| `script.dat` 674 entri; semua entri dipad 2048 | **Cocok** (0 pelanggaran dari 4.817 container) |
| `0011ess0` 356 instruksi; choice inst#86 di `0xbf0`, target 87 dan 94 | **Cocok** |
| Statistik `jumpscan` (1500: 47.451; 100: 21.096; 103: 95; 104: 32 di `zModelTest`, dst.) | **Cocok** semua |
| Opcode 100 berukuran 64/80/48/96 | **Dilengkapi**: juga 112 (2.307) dan 1.521 baris ≥ 128 |
| Header dialog `+11` jumlah karakter, `+15` isi | **Cocok**; `+7` u16, `+9` u16 = ID speaker |
| Jepang maks 49-51, tak pernah > 2 baris | **Cocok** (51 dengan 「」; 0 baris > 56) |
| Scene title 673 | op700 = 674; `0000Index` ("INDEX") kemungkinan tak diekstrak (belum dikonfirmasi) |
| 15.257 + 5.817 = 21.074 | op100 asli 21.096: **selisih 22 belum dijelaskan** (awalan nama: 15.351 / 5.745) |
| `first_new_v12.dat` 15.698 baris, 1.052.672 byte | **Cocok** dengan seekmap asli |
