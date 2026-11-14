"""cut_gpda.py  -  by: KangJiho
Memotong container GPDA tingkat atas dari RES.DAT (atau first.dat) menjadi file terpisah,
supaya kecil dan bisa diunggah ke chat. Hanya membaca, file input tidak diubah.

Pemakaian:
  python cut_gpda.py RES.DAT list
  python cut_gpda.py RES.DAT cut out_menu image_main.dat main_resource.dat image_title.dat omake.dat
  python cut_gpda.py RES.DAT cut out_menu --small        (semua entri <= 2 MB, kecuali dummy.dat)
"""
import os, struct, sys

def read_gpda(f, base=0):
    f.seek(base)
    head = f.read(16)
    if head[:4] != b"GPDA":
        raise SystemExit("bukan GPDA di offset %d" % base)
    n = struct.unpack_from("<I", head, 12)[0]
    tab = f.read(16 * n)
    out = []
    for i in range(n):
        off, size, noff = struct.unpack_from("<QII", tab, 16 * i)
        f.seek(base + noff)
        ln = struct.unpack("<I", f.read(4))[0]
        name = f.read(ln).decode("utf-8", "replace").strip()
        out.append((name, base + off, size))
    return out

def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    path, cmd = sys.argv[1], sys.argv[2]
    with open(path, "rb") as f:
        ents = read_gpda(f)
        if cmd == "list":
            for name, off, size in ents:
                print("%-28s offset=0x%08x  ukuran=%d" % (name, off, size))
            return
        if cmd != "cut" or len(sys.argv) < 5:
            print(__doc__); return
        outdir = sys.argv[3]
        want = sys.argv[4:]
        os.makedirs(outdir, exist_ok=True)
        for name, off, size in ents:
            take = (("--small" in want) and size <= 2 * 1024 * 1024 and name != "dummy.dat") or name in want
            if not take:
                continue
            f.seek(off)
            with open(os.path.join(outdir, name), "wb") as o:
                o.write(f.read(size))
            print("ditulis %-24s %d byte" % (name, size))

if __name__ == "__main__":
    main()
