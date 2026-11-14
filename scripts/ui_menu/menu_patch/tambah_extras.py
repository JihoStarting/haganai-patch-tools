# tambah_extras.py -- menambahkan 20 sprite Extras ke originals.txt (format mengikuti isi file yang ada)
# Pakai:  python tambah_extras.py <folder menu_patch> <folder out_menu>
#   contoh: python menu_patch\tambah_extras.py menu_patch "Ui menu\out_menu"
# Aman: originals.txt dicadangkan ke originals.txt.bak, baris yang sudah ada tidak ditambah dua kali.
import sys, re, zlib, struct, hashlib, shutil, os

def parse(buf):
    n = struct.unpack_from('<I', buf, 12)[0]; out = []
    for i in range(n):
        off, size, noff = struct.unpack_from('<QII', buf, 16 + i * 16)
        out.append((off, size))
    return out

def md5_sets(outmenu):
    dec, raw = set(), set()
    def add(b):
        raw.add(hashlib.md5(b).hexdigest())
        try: dec.add(hashlib.md5(zlib.decompress(b, 31)).hexdigest())
        except Exception: pass
    mb = open(os.path.join(outmenu, 'image_main.dat'), 'rb').read()
    for off, size in parse(mb): add(mb[off:off + size])
    tb = open(os.path.join(outmenu, 'image_title.dat'), 'rb').read()[2048:2048 + 708608]
    for off, size in parse(tb): add(tb[off:off + size])
    return dec, raw

def main():
    mp, om = sys.argv[1], sys.argv[2]
    orig = os.path.join(mp, 'originals.txt')
    lines = [l.rstrip('\r\n') for l in open(orig, encoding='utf-8') if l.strip()]
    first = lines[0]
    sep = '\t' if '\t' in first else (',' if ',' in first else None)
    toks = first.split(sep) if sep else first.split()
    hexi = [i for i, t in enumerate(toks) if re.fullmatch(r'[0-9a-fA-F]{32}', t.strip())]
    if not hexi:
        print('Tidak bisa membaca format originals.txt. Baris pertama:', repr(first)); sys.exit(1)
    hi = hexi[0]; ni = 1 - hi if len(toks) == 2 else (0 if hi != 0 else 1)
    ext = ''
    m = re.search(r'\.\w+$', toks[ni].strip())
    if m: ext = m.group(0)
    joiner = sep if sep else ' '
    dec, raw = md5_sets(om)
    have = [t.strip() for l in lines for t in (l.split(sep) if sep else l.split()) if re.fullmatch(r'[0-9a-fA-F]{32}', t.strip())]
    nd = sum(h in dec for h in have); nr = sum(h in raw for h in have)
    mode = 'dec' if nd >= nr else 'raw'
    print(f'originals.txt: {len(lines)} baris; MD5 cocok GIM-terurai={nd}, entri-mentah={nr} -> pakai {mode}')
    if max(nd, nr) == 0: print('PERINGATAN: tidak ada MD5 lama yang cocok dengan out_menu; periksa folder out_menu'); sys.exit(1)
    new = []
    for l in open(os.path.join(mp, 'extras_md5.txt'), encoding='utf-8'):
        name, d, r = l.split()
        h = d if mode == 'dec' else r
        if h in have: continue
        cols = [None, None]; cols[hi] = h; cols[ni] = name + ext
        new.append(joiner.join(cols)); have.append(h)
    if not os.path.exists(orig + '.bak'): shutil.copyfile(orig, orig + '.bak')
    with open(orig, 'a', encoding='utf-8', newline='') as f:
        if open(orig, 'rb').read()[-1:] not in (b'\n',): f.write('\n')
        for n in new: f.write(n + '\n')
    print(f'ditambah {len(new)} baris (total {len(lines)+len(new)}). Cadangan: originals.txt.bak')
main()
