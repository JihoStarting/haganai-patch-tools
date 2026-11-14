#!/usr/bin/env python3
"""Patch English main-menu sprites into RES.DAT / first.dat (in place, on a copy).
usage: python3 patch_menu.py <file.dat> [more.dat ...]   (reads ./menu_gims/*.gim)
Each sprite is found by matching the ORIGINAL (Japanese) GIM, gzip'd back in the
same slot, and the entry size in the GPDA table is updated."""
import sys,struct,gzip,zlib,glob,os,hashlib,shutil
HERE=os.path.dirname(os.path.abspath(__file__))
# md5 of original decompressed Japanese GIM  ->  new GIM file
ORIG=dict(l.split() for l in open(os.path.join(HERE,'originals.txt')))
NEW={os.path.basename(f)[:-4]:open(f,'rb').read() for f in glob.glob(os.path.join(HERE,'menu_gims','*.gim'))}
def mkgz(raw,hdr):
    c=zlib.compressobj(9,zlib.DEFLATED,-15,9)
    body=c.compress(raw)+c.flush()
    return hdr+body+struct.pack('<II',zlib.crc32(raw)&0xffffffff,len(raw))
def walk(buf,base,end,depth,log):
    if buf[base:base+4]!=b'GPDA' or depth>6: return
    n=struct.unpack_from('<I',buf,base+12)[0]
    if n>20000: return
    ents=[struct.unpack_from('<IIII',buf,base+16+16*i) for i in range(n)]
    offs=sorted(set(e[0] for e in ents))
    for i,(o,hi,sz,t) in enumerate(ents):
        if sz==0 or base+o+sz>end: continue
        nxt=min([x for x in offs if x>o]+[end-base])
        a=base+o; chunk=bytes(buf[a:a+sz])
        if chunk[:4]==b'GPDA': walk(buf,a,a+sz,depth+1,log)
        elif chunk[:2]==b'\x1f\x8b':
            try: raw=gzip.decompress(chunk)
            except Exception: continue
            if raw[:3]==b'MIG':
                key=hashlib.md5(raw).hexdigest()
                if key in ORIG and ORIG[key] in NEW:
                    ng=mkgz(NEW[ORIG[key]],chunk[:10])
                    cap=nxt-o
                    if len(ng)>cap: print('  !! too big',ORIG[key],len(ng),cap); continue
                    buf[a:a+cap]=ng+b'\0'*(cap-len(ng))
                    struct.pack_into('<I',buf,base+16+16*i+8,len(ng))
                    log.append((ORIG[key],a,len(chunk),len(ng)))
        elif chunk[:3]==b'MIG':
            pass
for fn in sys.argv[1:]:
    out=fn+'.patched'; shutil.copyfile(fn,out)
    with open(out,'r+b') as f: buf=bytearray(f.read())
    log=[]; walk(buf,0,len(buf),0,log)
    open(out,'wb').write(buf)
    print(fn,'->',out,len(log),'sprites patched')
    for l in log: print('  ',l)
