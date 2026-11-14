#!/usr/bin/env python3
"""Cek isi sprite menu judul di sebuah RES.DAT (tanpa mengubah apa pun).
usage: python menu_check.py RES_patched_v14.DAT [first_new_v14.dat]
Laporan per sprite: JEPANG (md5 asli) / INGGRIS (md5 = gim di menu_gims) / lain.
Kalau first.dat diberikan, ukuran GPDA dibandingkan dengan ukuran di seekmap."""
import sys,struct,gzip,glob,os,hashlib
HERE=os.path.dirname(os.path.abspath(__file__))
ORIG=dict(l.split() for l in open(os.path.join(HERE,'originals.txt')))   # md5 -> nama
NEWMD5={hashlib.md5(open(f,'rb').read()).hexdigest():os.path.basename(f)[:-4]
        for f in glob.glob(os.path.join(HERE,'menu_gims','*.gim'))}
found={}
def walk(buf,base,end,depth,path):
    if buf[base:base+4]!=b'GPDA' or depth>6: return
    n=struct.unpack_from('<I',buf,base+12)[0]
    if n>20000: return
    for i in range(n):
        o,hi,sz,t=struct.unpack_from('<IIII',buf,base+16+16*i)
        if sz==0 or base+o+sz>end: continue
        a=base+o; chunk=bytes(buf[a:a+sz])
        if chunk[:4]==b'GPDA': walk(buf,a,a+sz,depth+1,path+[i])
        elif chunk[:2]==b'\x1f\x8b':
            flg=chunk[3]
            try: raw=gzip.decompress(chunk)
            except Exception as e:
                continue
            if raw[:3]!=b'MIG': continue
            k=hashlib.md5(raw).hexdigest()
            if k in ORIG: found.setdefault(ORIG[k],[]).append(('JEPANG',a,sz,flg))
            elif k in NEWMD5: found.setdefault(NEWMD5[k],[]).append(('INGGRIS',a,sz,flg))
buf=open(sys.argv[1],'rb').read()
walk(buf,0,len(buf),0,[])
names=sorted(set(ORIG.values()))
jp=en=0
for nm in names:
    r=found.get(nm)
    if not r: print(f'{nm}: TIDAK DITEMUKAN (jepang maupun inggris)'); continue
    for st,a,sz,flg in r:
        print(f'{nm}: {st}  offset=0x{a:x} ukuran_gz={sz} gzip_flag={flg:#04x}')
        jp+=st=='JEPANG'; en+=st=='INGGRIS'
print(f'\nRINGKASAN: {en} inggris, {jp} jepang, dari {len(names)} sprite')
