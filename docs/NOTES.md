# Haganai Translation & Reverse Engineering Notes

1. Haganai Portable translation project: /mnt/d/Reverse engginering/project haganai/ — 3 ISOs (JP original, English v1, English v2). English v2 has text overflow (80-124 chars over Japanese per overflow_report.csv). Root cause: objbin_patch_fixed_v2.py patches text but doesn't insert line-break opcodes; game text box fixed-width for Japanese.

2. binwalk broken on Python 3.14 — Docker wrapper at ~/.local/bin/binwalk using cincan/binwalk image (mounts $(pwd) to /data). Verified working.

3. gpda_v2.py is authoritative GPDA parser/rebuilder — fixed 2048-byte padding for ALL entries including last. Passes identity rebuild on original RES.DAT (402,360,320 bytes) and RES_patched_v6.DAT (402,569,216 bytes). Delta: +208,896 bytes in script.dat only.

4. seekmap_rebuild.py rebuilds seekmap.dat (CRC-32/MPEG-2 checksums) and first.dat after RES.DAT patch. Without it, game crashes — offsets/sizes/CRCs won't match patched data.
