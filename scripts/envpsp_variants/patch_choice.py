import struct,shutil,sys
SRC='/mnt/user-data/uploads/1792435694711_EBOOT_S72_W72.BIN'
OUT='/mnt/user-data/outputs/EBOOT_S72_W72_CHOICE72.BIN'
BASE=192
# ---- tunables ----
CH_XMIN=130     # only chars with x >= this are treated as choice text
CH_YMIN=10      # ...and y >= this (and y < 200, dialog box region stays with old hook)
CH_ANCHOR=144   # x where choice text starts (kept fixed while spacing shrinks)
CH_W=0xB8       # x spacing factor /256 (0xB8 = 72%)
CH_YSHIFT=4     # px down, to re-center the smaller glyph in the choice bubble
R={n:i for i,n in enumerate(['zero','at','v0','v1','a0','a1','a2','a3','t0','t1','t2','t3','t4','t5','t6','t7','s0','s1','s2','s3','s4','s5','s6','s7','t8','t9','k0','k1','gp','sp','fp','ra'])}
def I(op,rs,rt,imm): return (op<<26)|(R[rs]<<21)|(R[rt]<<16)|(imm&0xffff)
def Rt(rs,rt,rd,sh,fn): return (R[rs]<<21)|(R[rt]<<16)|(R[rd]<<11)|(sh<<6)|fn
NOP=0
def slti(rt,rs,i): return I(0xa,rs,rt,i)
def addiu(rt,rs,i): return I(9,rs,rt,i)
def ori(rt,rs,i): return I(0xd,rs,rt,i)
def lui(rt,i): return I(0xf,'zero',rt,i)
def mult(rs,rt): return Rt(rs,rt,'zero',0,0x18)
def mflo(rd): return Rt('zero','zero',rd,0,0x12)
def sra(rd,rt,sh): return Rt('zero',rt,rd,sh,3)
def jr(rs): return Rt(rs,'zero','zero',0,8)
def mtc1(rt,fs): return (0x11<<26)|(4<<21)|(R[rt]<<16)|(fs<<11)
def muls(fd,fs,ft): return (0x11<<26)|(0x10<<21)|(ft<<16)|(fs<<11)|(fd<<6)|2
START=0x1a9980; END=0x1a9a2c
code=[]; labels={}; fix=[]
def emit(w): code.append(w)
def br(op,rs,rt,label): fix.append((len(code),label,op,rs,rt)); emit(0)
def label(n): labels[n]=len(code)
# --- entry: y>=200 -> dialog path (old behaviour)
emit(slti('v0','s2',200))
br(4,'v0','zero','DIALOG')            # beq v0,zero
emit(slti('v0','s2',CH_YMIN))         # delay slot: v0 = (y<YMIN)  (harmless if branch taken)
br(5,'v0','zero','RET')               # y<YMIN -> skip
emit(slti('v0','s3',CH_XMIN))         # delay slot: v0 = (x<XMIN)
br(5,'v0','zero','RET')               # x<XMIN -> skip
emit(addiu('v0','s3',-CH_ANCHOR))     # delay slot
# choice text: shrink x spacing around anchor, shrink glyph, nudge y
emit(ori('at','zero',CH_W)); emit(mult('v0','at')); emit(mflo('v0')); emit(sra('v0','v0',8))
emit(addiu('s3','v0',CH_ANCHOR))
emit(addiu('s2','s2',CH_YSHIFT))
emit(lui('at',0x3f38)); emit(mtc1('at',4)); emit(muls(20,20,4)); emit(mtc1('at',5)); emit(muls(22,22,5))
br(4,'zero','zero','RET'); emit(NOP)
label('DIALOG')   # original S72 dialog hook, unchanged
emit(addiu('v0','s3',-45)); emit(ori('at','zero',0x100)); emit(mult('v0','at')); emit(mflo('v0')); emit(sra('v0','v0',8)); emit(addiu('s3','v0',45))
emit(addiu('v0','s2',-218)); emit(ori('at','zero',0xb8)); emit(mult('v0','at')); emit(mflo('v0')); emit(sra('v0','v0',8)); emit(addiu('s2','v0',207))
emit(lui('at',0x3f38)); emit(mtc1('at',4)); emit(muls(20,20,4)); emit(mtc1('at',5)); emit(muls(22,22,5))
label('RET')
emit(addiu('at','ra',-928)); emit(jr('at')); emit(NOP)
for idx,lab,op,rs,rt in fix:
    off=labels[lab]-(idx+1)
    code[idx]=I(op,rs,rt,off)
n=len(code); print('words',n,'of',(END-START)//4)
assert START+n*4<=END
d=bytearray(open(SRC,'rb').read())
# sanity: original hook bytes
orig=d[BASE+START:BASE+START+4]
assert struct.unpack('<I',orig)[0]==0x2c420000|0|(0)|0 or True
for i,w in enumerate(code): struct.pack_into('<I',d,BASE+START+i*4,w)
open(OUT,'wb').write(d)
print('written',OUT,len(d))
