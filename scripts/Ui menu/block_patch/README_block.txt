block_patch_v1 - sprite Inggris minigame Cosplay Block Kuzushi (image_block.dat)
Dibuat 2026-10-23. BELUM dites di game.

Isi: 18 sprite (block_gims\), originals_block.txt (MD5 GIM Jepang asli), patch_block.py, preview_block_english.png
  title.dat      : Start / Gallery / Controls / Quit (8 sprite: versi diam + sheet animasi)
  game_sharing   : STAGE CLEAR!! / ALL CLEAR!!! / GAME OVER! / GAME START!, Next Stage, Retry,
                   Character Select, Return to Title, Back to Game, menu pause (Continue / Character Select / Title / Next / Retry)

PASANG (dari folder scripts tools; pakai RES yang SUDAH kena patch menu, mis. Ui menu\out_v30\RES.DAT):
  Expand-Archive "block_patch_v1.zip" -DestinationPath "." -Force
  cd block_patch
  python patch_block.py "..\Ui menu\out_v30\RES.DAT" --check     # harapan: 18 JEPANG
  python patch_block.py "..\Ui menu\out_v30\RES.DAT"             # harapan: 18 sprite dipatch, 0 too big
  python patch_block.py "..\Ui menu\out_v30\RES.DAT.patched" --check   # harapan: 18 INGGRIS
  cd ..
  python seekmap_rebuild.py build "Ui menu\out_v30\RES.DAT.patched" "D:\Reverse engginering\project haganai\data ekstrak\first.dat" "first_new_v30_block.dat"
  Copy-Item "Ui menu\out_v30\RES.DAT.patched" "Ui menu\out_v30\RES.DAT" -Force
  Copy-Item "first_new_v30_block.dat" "Ui menu\out_v30\first.dat" -Force
Lalu timpa RES.DAT dan first.dat di folder game, tutup PPSSPP, mulai tanpa save state.

Catatan: posisi teks Inggris dipusatkan di titik tengah teks Jepang asli (supaya posisi di layar tetap).
Belum diterjemahkan: halaman bantuan (bd_help1-3, bd_thelp01), nama karakter (bd_sel*_name), logo karakter, bd_tmenu.
