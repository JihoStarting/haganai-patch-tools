"""patch_block.py - pasang sprite Inggris minigame (image_block.dat) ke RES.DAT.
Pemakaian:  python patch_block.py RES_patched_v30.DAT [--check]
- Hasil ditulis ke salinan NAMA.patched (file asli tidak diubah).
- --check: hanya melaporkan JEPANG/INGGRIS/TIDAK ADA untuk tiap sprite, tanpa menulis apa pun.
- Bisa juga dipakai langsung pada image_block.dat hasil cut_gpda.py.
Butuh: block_gims\\ dan originals_block.txt di folder yang sama dengan skrip ini.
"""
import sys,os,struct,gzip,zlib,hashlib,shutil
HERE=os.path.dirname(os.path.abspath(__file__))
def table(f,base):
    f.seek(base); h=f.read(16)
    if h[:4]!=b'GPDA': return None
    n=struct.unpack_from('<I',h,12)[0]
    t=f.read(16*n); ents=[]
    for i in range(n):
        o,s,no=struct.unpack_from('<QII',t,16*i)
        f.seek(base+no); l=struct.unpack('<I',f.read(4))[0]
        nm=f.read(l).decode('utf8','replace').strip()
        ents.append(dict(name=nm,off=o,size=s,idx=i,tpos=base+16+16*i+8))
    ents_sorted=sorted(ents,key=lambda e:e['off'])
    return ents
def slot(ents,e,total):
    nxt=[x['off'] for x in ents if x['off']>e['off']]
    return (min(nxt) if nxt else total)-e['off']
def load_list():
    L={}
    for ln in open(os.path.join(HERE,'originals_block.txt'),encoding='utf8'):
        ln=ln.strip()
        if not ln: continue
        md5,path=ln.split(None,1); cont,name=path.split('/')
        L[(cont,name)]=md5
    return L
def locate_block(f):
    f.seek(0,2); total=f.tell()
    top=table(f,0)
    if top is None: raise SystemExit('bukan GPDA')
    for e in top:
        if e['name']=='image_block.dat': return e['off'],e['size']
    names={e['name'] for e in top}
    if 'game_sharing.dat' in names or 'title.dat' in names: return 0,total
    raise SystemExit('image_block.dat tidak ditemukan')
def main():
    a=[x for x in sys.argv[1:] if not x.startswith('--')]
    check='--check' in sys.argv
    if not a: print(__doc__); return
    src=a[0]; L=load_list()
    gdir=os.path.join(HERE,'block_gims')
    if check: dst=src
    else:
        dst=src+'.patched'; print('menyalin ->',dst); shutil.copyfile(src,dst)
    f=open(dst,'rb' if check else 'r+b')
    base,bsize=locate_block(f)
    ents=table(f,base)
    done=bad=0; out=[]
    for (cont,name),md5 in L.items():
        ce=[e for e in ents if e['name']==cont]
        if not ce: out.append(('TIDAK ADA',cont,name)); continue
        cbase=base+ce[0]['off']
        sub=table(f,cbase)
        se=[e for e in sub if e['name'].replace('.gz','')==name or e['name']==name]
        if not se: out.append(('TIDAK ADA',cont,name)); continue
        e=se[0]
        f.seek(cbase+e['off']); raw=f.read(e['size'])
        try: g=gzip.decompress(raw)
        except Exception: out.append(('RUSAK',cont,name)); continue
        cur=hashlib.md5(g).hexdigest()
        newg=open(os.path.join(gdir,f'{cont[:-4]}__{name}'),'rb').read()
        if cur==hashlib.md5(newg).hexdigest(): out.append(('INGGRIS',cont,name)); continue
        if cur!=md5: out.append(('MD5 BEDA',cont,name)); continue
        if check: out.append(('JEPANG',cont,name)); continue
        hdr=raw[:10]
        co=zlib.compressobj(9,zlib.DEFLATED,-15)
        body=co.compress(newg)+co.flush()
        gz=hdr+body+struct.pack('<II',zlib.crc32(newg)&0xffffffff,len(newg)&0xffffffff)
        sl=slot(sub,e,sub_total(f,cbase,ce[0]))
        if len(gz)>sl: out.append(('TOO BIG',cont,name)); bad+=1; continue
        f.seek(cbase+e['off']); f.write(gz+bytes(max(0,e['size']-len(gz))))
        f.seek(e['tpos']); f.write(struct.pack('<I',len(gz)))
        out.append(('DIPATCH',cont,name)); done+=1
    f.close()
    for s,c,n in out: print(f'{s:10s} {c}/{n}')
    if not check: print(f'\n{done} sprite dipatch, {bad} too big')
def sub_total(f,cbase,ce):
    return ce['size']
main()
