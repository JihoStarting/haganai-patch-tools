# Laporan Perbaikan Crash Haganai Portable

## Akar Masalah (terkonfirmasi)

Hipotesis di laporan investigasi awal **benar**: `RES_patched.DAT` sudah valid, tapi `seekmap.dat` di dalam `first.dat` masih menyimpan metadata (offset/size/checksum) dari `RES.DAT` versi **sebelum** dipatch. Engine membaca metadata basi ini, mendapat offset/size yang salah untuk resource yang sudah bergeser posisinya → pointer/struct rusak → crash di PC=0x00000006.

## Yang ditemukan saat analisis

1. **Algoritma checksum berhasil diidentifikasi**: bukan CRC32 biasa, tapi **CRC-32/MPEG-2** (poly `0x04C11DB7`, init `0xFFFFFFFF`, tanpa refleksi, tanpa XOR akhir). Ini dites dan cocok 100% terhadap seluruh entry di `seekmap.dat`, baik file kecil (misal `_0083yoz0.obj.gz`) maupun container besar (`script.dat` 166 MB) dan bahkan `resource.dat` (seluruh RES.DAT).

2. **`RES.DAT` dan `RES_patched.DAT` sendiri sebenarnya sudah GPDA container berlapis** (root → `script.dat` → sub-folder cerita → file individual), dan setiap levelnya punya header GPDA sendiri yang **sudah otomatis diperbarui dengan benar** oleh tool patch (offset/size internalnya konsisten). Jadi struktur internal RES_patched.DAT itu sendiri **tidak rusak**.

3. Masalahnya murni ada di **`seekmap.dat`** — file metadata eksternal ini **tidak ikut diperbarui** oleh tool patch, padahal:
   - `script.dat` bertambah ukuran (166.508.544 → 166.686.720 byte, +178.176 byte) karena skrip Inggris lebih panjang dari Jepang.
   - Pertambahan ini menggeser offset ratusan file `.hca`/`.gim`/skrip lain di dalam subtree `script.dat` (674 anak → total 14.001 baris metadata berubah).
   - File-file di luar `script.dat` (mis. `system_voices.dat` dst.) juga ikut geser offset-nya (ukuran tetap, checksum tetap, hanya posisi berubah).

## Perbaikan yang dilakukan

Saya membangun ulang `seekmap.dat` **langsung dari struktur GPDA yang sudah benar di dalam `RES_patched.DAT`** (bukan dengan menebak-nebak), lalu:

1. Menelusuri seluruh pohon GPDA (4.817 container, termasuk root) secara rekursif untuk mendapatkan offset & size yang benar untuk **setiap** entry.
2. Menghitung ulang checksum CRC-32/MPEG-2 untuk setiap entry langsung dari `RES_patched.DAT`.
3. Memvalidasi: struktur nama/urutan/kedalaman pohon **identik 100%** dengan `seekmap.dat` original (0 mismatch topologi) — hanya nilai offset/size/checksum yang berubah, persis di area yang memang berubah (root + subtree `script.dat` + pergeseran entry sesudahnya).
4. Mengompres ulang hasilnya (gzip) dan mem-*pack* ulang ke dalam `first.dat`, termasuk memperbarui header GPDA `first.dat` sendiri dan menggeser posisi `systemse.dat`, `text.dat`, `voice.dat` yang mengikuti `seekmap.dat` (karena ukuran hasil kompresi baru sedikit lebih kecil).
5. Memvalidasi ulang: `first.dat` hasil rebuild valid secara struktur, entry `seekmap.dat` di dalamnya bila didekompresi menghasilkan persis teks yang sudah dihitung, dan seluruh entry lain (`font_location.dat`, `image_sharing.dat`, `logo.dat`, `save.dat`, `script.dat` [container patch], `systemse.dat`, `text.dat`, `voice.dat`) byte-per-byte identik dengan aslinya, hanya posisinya yang disesuaikan.

## File yang dihasilkan

**`first.dat`** — versi baru yang seekmap.dat di dalamnya sudah sinkron dengan `RES_patched.DAT`.

### Cara pakai
Ganti file `first.dat` di folder game dengan file hasil ini (dampingkan dengan `RES_patched.DAT` yang sudah Anda buat). Tidak perlu mengubah `RES_patched.DAT` sama sekali — masalahnya memang ada di `first.dat`.

## Catatan verifikasi lanjutan (opsional)

Jika crash masih terjadi setelah mengganti `first.dat`, kemungkinan besar penyebabnya bukan lagi di metadata seekmap, dan langkah 4–5 di rencana investigasi awal (reverse engineering EBOOT.BIN, cek instruksi di RA=0x08834ACC) baru relevan untuk dijalankan.
