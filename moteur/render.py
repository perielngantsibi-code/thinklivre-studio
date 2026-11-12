import json, sys, os, math, re, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
W,H,FPS=1920,1080,30
HERE=os.path.dirname(os.path.abspath(__file__))
words=json.load(open(f"{HERE}/words.json"))
plan=json.load(open(f"{HERE}/plan.json"))
DUR=plan["duration"]
FB="/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FBI="/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"
GOLD=(242,194,48); RED=(215,38,61); GREEN=(80,190,90); WHITE=(245,240,230)
_font={}
def font(p,s):
    if (p,s) not in _font: _font[(p,s)]=ImageFont.truetype(p,s)
    return _font[(p,s)]
def clean(w): return re.sub(r"\s+"," ",re.sub(r"\s*[«»]\s*","",w)).strip().upper()
def key(w):
    import unicodedata
    s=unicodedata.normalize("NFD",w.upper()); return re.sub(r"[^A-Z0-9'\-]","","".join(c for c in s if unicodedata.category(c)!="Mn"))
EMPH={key(k):v for k,v in plan["emphasis"].items()}
_spr={}
PAD=24
def sprite(text,size,color,italic):
    k=(text,size,color,italic)
    if k in _spr: return _spr[k]
    f=font(FBI if italic else FB,size); sw=max(2,size//22)
    asc,desc=f.getmetrics(); bb=f.getbbox(text,stroke_width=sw)
    w=bb[2]-bb[0]+2*PAD; h=asc+desc+2*PAD
    im=Image.new("RGBA",(w,h)); d=ImageDraw.Draw(im)
    d.text((PAD-bb[0],PAD),text,font=f,fill=(0,0,0,255),stroke_width=sw+4,stroke_fill=(0,0,0,255))
    sh=im.filter(ImageFilter.GaussianBlur(8))
    out=Image.new("RGBA",(w,h)); out.alpha_composite(sh); out.alpha_composite(sh)
    d=ImageDraw.Draw(out); d.text((PAD-bb[0],PAD),text,font=f,fill=color+(255,),stroke_width=sw,stroke_fill=(10,8,6,255))
    _spr[k]=(out,asc,desc); return _spr[k]
# ---------- chunks (groups of words displayed together) ----------
chunks=[]
lines_=sorted(set(x["line"] for x in words))
for L in lines_:
    lw=[x for x in words if x["line"]==L]
    ph=[];cur=[]
    for x in lw:
        cur.append(x)
        if re.search(r"[.…?!:,;]$",x["w"].strip()): ph.append(cur); cur=[]
    if cur: ph.append(cur)
    m=[]
    for p in ph:
        if m and (len(p)<=1 or len(m[-1])<=1) and len(m[-1])+len(p)<=6: m[-1]=m[-1]+p
        else: m.append(p)
    for p in m:
        n=max(1,math.ceil(len(p)/6)); sz=math.ceil(len(p)/n)
        for i in range(0,len(p),sz): chunks.append(p[i:i+sz])
for k,c in enumerate(chunks):
    nxt=chunks[k+1][0]["t"] if k+1<len(chunks) else DUR
    c1=min(nxt, c[-1]["t"]+1.5)
    for x in c: x["c0"]=c[0]["t"]; x["c1"]=c1
def layout(c,k):
    # build lines: emphasis words alone on their line if big
    items=[]
    for x in c:
        t=clean(x["w"]); e=EMPH.get(key(x["w"]))
        if e: col=tuple(e[0]); it=e[1]; sc=e[2]
        else: col=WHITE; it=False; sc=1.0
        items.append((x,t,int(70*sc*(1.35 if c[0]['t']<9.9 else 1.0)),col,it))
    lines=[];line=[];lw=0
    for it in items:
        spr=sprite(it[1],it[2],it[3],it[4]); w=spr[0].width-2*PAD
        big=it[2]>95
        if line and (lw+w>660 or big or (lines and False)):
            lines.append(line); line=[];lw=0
        line.append((it,spr)); lw+=w+18
        if big: lines.append(line); line=[];lw=0
    if line: lines.append(line)
    region=plan["text_region"](k) if callable(plan.get("text_region")) else None
    return lines
REG=plan["regions"]
def chunk_pos(k,t):
    # find region for this chunk time
    for r in REG:
        if r[0]<=t<r[1]: return r[2]
    return "left"
# ---------- assets ----------
cache={}
def autocrop(im):
    a=np.asarray(im.resize((im.width//4,im.height//4))).astype(np.int16)
    corners=np.concatenate([a[:6,:6].reshape(-1,3),a[:6,-6:].reshape(-1,3),a[-6:,:6].reshape(-1,3),a[-6:,-6:].reshape(-1,3)])
    bgc=np.median(corners,0); diff=np.abs(a-bgc).sum(2)>45
    rows=np.where(diff.mean(1)>0.08)[0]; cols=np.where(diff.mean(0)>0.08)[0]
    if len(rows)<10 or len(cols)<10: return im
    y0,y1,x0,x1=rows[0]*4,rows[-1]*4,cols[0]*4,cols[-1]*4
    if (x1-x0)*(y1-y0)<0.25*im.width*im.height: return im
    m=int(0.01*min(im.size)); return im.crop((x0+m,y0+m,x1-m,y1-m))
def load_bg(name):
    if name in cache: return cache[name]
    p=f"{HERE}/raw/{name}"
    if not os.path.exists(p):
        alt=sorted(os.listdir(f"{HERE}/raw")); alt=[a for a in alt if a not in ("machiavel.jpg","zhuge.jpg")]
        p=f"{HERE}/raw/"+alt[sum(map(ord,name))%len(alt)]
    im=Image.open(p).convert("RGB")
    im=autocrop(im)
    s=max(W*1.25/im.width,H*1.25/im.height); im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
    # grade: contrast, darker, warm
    im=ImageOps.autocontrast(im,cutoff=1); im=ImageEnhance.Contrast(im).enhance(1.15); im=ImageEnhance.Color(im).enhance(0.85); im=ImageEnhance.Brightness(im).enhance(0.6)
    a=np.asarray(im).astype(np.float32); a*=np.array([1.04,0.98,0.88]); im=Image.fromarray(np.clip(a,0,255).astype(np.uint8))
    cache[name]=im; return im
def load_rgba(name,h):
    k=(name,h)
    if k in cache: return cache[k]
    im=Image.open(f"{HERE}/img/{name}").convert("RGBA"); s=h/im.height; im=im.resize((int(im.width*s),h),Image.LANCZOS)
    cache[k]=im; return im
vig=None
def vignette():
    global vig
    if vig is None:
        y,x=np.mgrid[0:H,0:W]; d=np.sqrt(((x-W/2)/(W/2))**2+((y-H/2)/(H/2))**2)
        a=np.clip((d-0.55)/0.85,0,1)**1.6*235
        vig=Image.fromarray(np.dstack([np.zeros((H,W,3)),a]).astype(np.uint8),"RGBA")
    return vig
rng=np.random.default_rng(1)
GRAIN=[Image.fromarray(np.dstack([np.full((H//2,W//2,3),128),np.zeros((H//2,W//2))]).astype(np.uint8),"RGBA") for _ in range(1)]
gr=[]
for i in range(8):
    n=rng.normal(128,40,(H//2,W//2)).clip(0,255).astype(np.uint8)
    g=Image.fromarray(n).resize((W,H),Image.BILINEAR).convert("RGB"); gr.append(g)
def ease(x): x=min(1,max(0,x)); return 1-(1-x)**3
# ---------- frame ----------
scenes=plan["scenes"]; events=plan["events"]; ctas=plan["ctas"]
def scene_at(t):
    for i in range(len(scenes)-1,-1,-1):
        if scenes[i]["t"]<=t: return i
    return 0
def bg_frame(i,t):
    s=scenes[i]; t0=s["t"]; t1=scenes[i+1]["t"] if i+1<len(scenes) else DUR
    if s.get("img") is None:
        return Image.new("RGB",(W,H),(0,0,0))
    im=load_bg(s["img"]); p=(t-t0)/max(0.1,t1-t0)
    z0,z1=s.get("z",(1.0,1.12)); z=z0+(z1-z0)*p
    dx,dy=s.get("pan",(0,0))
    cw,ch=W*1.25/z*im.width/(W*1.25),H*1.25/z*im.height/(H*1.25)
    cw=im.width/z/1.0; ch=cw*H/W
    if ch>im.height/z: ch=im.height/z; cw=ch*W/H
    cx=im.width/2+dx*(p-0.5)*(im.width-cw)*0.5; cy=im.height/2+dy*(p-0.5)*(im.height-ch)*0.5
    fx,fy=s.get("focus",(0.5,0.5)); cx+= (fx-0.5)*(im.width-cw); cy+=(fy-0.5)*(im.height-ch)
    cx=min(max(cx,cw/2),im.width-cw/2); cy=min(max(cy,ch/2),im.height-ch/2)
    return im.transform((W,H),Image.EXTENT,(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2),Image.BILINEAR)
# ---------- v2 extras ----------
prng=np.random.default_rng(11)
NP=80
PX=prng.uniform(0,W,NP); PY=prng.uniform(0,H,NP); PS=prng.uniform(0.6,2.2,NP); PV=prng.uniform(25,80,NP); PD=prng.uniform(0,6.28,NP)
def particles(fr,t):
    lay=Image.new("RGBA",(W,H)); d=ImageDraw.Draw(lay)
    for i in range(NP):
        x=(PX[i]+30*math.sin(t*0.7+PD[i]))%W; y=(PY[i]-PV[i]*t)%H; s=PS[i]*1.6
        a=int(150*(0.55+0.45*math.sin(t*3+PD[i])))
        d.ellipse((x-s,y-s,x+s,y+s),fill=(255,170,80,a))
    lay=lay.filter(ImageFilter.GaussianBlur(1.2)); fr.alpha_composite(lay)
SMOKE=None
def smoke(t):
    global SMOKE
    if SMOKE is None:
        n=np.random.default_rng(5).random((40,70)); im=Image.fromarray((n*255).astype(np.uint8)).resize((W+600,H+300),Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))
        a=np.asarray(im).astype(np.float32)/255; a=(a-a.min())/(a.max()-a.min())
        SMOKE=Image.fromarray(np.dstack([a*70+8,a*22+6,a*18+6]).astype(np.uint8))
    ox=int(300+250*math.sin(t*0.15)); oy=int(150+120*math.cos(t*0.11))
    return SMOKE.crop((ox,oy,ox+W,oy+H)).convert("RGBA")
_glow={}
def glow(spr,col):
    k=id(spr)
    if k not in _glow:
        a=spr.getchannel("A").filter(ImageFilter.GaussianBlur(14)); g=Image.new("RGBA",spr.size,col+(0,)); g.putalpha(Image.eval(a,lambda v:int(v*0.75))); _glow[k]=g
    return _glow[k]
def zoomc(img,s):
    if abs(s-1)<1e-3: return img
    w,h=img.size; cw,ch=w/s,h/s
    return img.transform((w,h),Image.EXTENT,((w-cw)/2,(h-ch)/2,(w+cw)/2,(h+ch)/2),Image.BILINEAR)
def bgplus(i,t):
    if scenes[i].get("img") is None:
        sf_=plan.get("smoke_from",0)
        if t<sf_: return Image.new("RGBA",(W,H),(0,0,0,255))
        sm=smoke(t); a=ease((t-sf_)/1.2)
        return Image.blend(Image.new("RGBA",(W,H),(0,0,0,255)),sm,a) if a<1 else sm
    return bg_frame(i,t).convert("RGBA")
def char_layer(fr,i,t):
    s=scenes[i]; ch=s.get("char")
    if not ch: return
    j=i
    while j>0 and scenes[j-1].get("char"): j-=1
    since=t-scenes[j]["t"]
    first=next(k for k,sc in enumerate(scenes) if sc.get("char"))
    c=load_rgba(ch["img"],ch.get("h",900)); tx=ch.get("x",0.5)
    if plan.get("char_entree","sol")=="sol":
        if j==first:
            # 1re apparition : il sort du sol au centre, puis va se placer à droite
            rise=ease(since/0.9); move=ease((since-1.2)/0.7)
            cx=0.5+(tx-0.5)*move; dy=(1-rise)*c.height
        else:
            cx=tx; dy=(1-ease(since/0.7))*c.height
        x=int(W*cx-c.width/2+8*math.sin(t*0.35)); y=H-c.height+int(dy)+int(4*math.sin(t*0.8))
    else:
        slide=(1-ease(since/0.6))*W*0.35 if j>0 or since<0.6 else 0
        x=int(W*tx-c.width/2+slide+8*math.sin(t*0.35)); y=H-c.height+int(4*math.sin(t*0.8))
    fr.alpha_composite(c,(x,y))

# ---------- PRO extras: parallax 2.5D, light leak, specials ----------
_layers={}
def layers(name):
    if name in _layers: return _layers[name]
    import cv2
    base=load_bg(name)
    from rembg import remove, new_session
    global _rs
    try: _rs
    except NameError: _rs=new_session("isnet-general-use")
    small=base.copy(); small.thumbnail((900,900))
    m=remove(small,session=_rs,only_mask=True).resize(base.size,Image.BILINEAR)
    a=np.asarray(m).astype(np.float32)/255
    a=np.where(a>0.5,1.0,0.0)
    if a.mean()<0.03 or a.mean()>0.6: _layers[name]=None; return None
    k=np.ones((25,25),np.uint8); dil=cv2.dilate((a*255).astype(np.uint8),k)
    arr=np.asarray(base); sm=cv2.resize(arr,(arr.shape[1]//3,arr.shape[0]//3)); dm=cv2.resize(dil,(sm.shape[1],sm.shape[0]))
    inp=cv2.inpaint(sm,dm,9,cv2.INPAINT_TELEA); inp=cv2.resize(inp,(arr.shape[1],arr.shape[0]))
    bg=np.where(dil[...,None]>0,inp,arr).astype(np.uint8)
    soft=cv2.GaussianBlur(a,(0,0),2.0)
    fg=np.dstack([arr,(soft*255).astype(np.uint8)])
    _layers[name]=(Image.fromarray(bg),Image.fromarray(fg,"RGBA")); return _layers[name]
def extent(im,s,p,shift=0.0,extra=1.0):
    z0,z1=s.get("z",(1.0,1.12)); z=(z0+(z1-z0)*p)*extra
    dx,dy=s.get("pan",(0,0))
    cw=im.width/z; ch=cw*H/W
    if ch>im.height/z: ch=im.height/z; cw=ch*W/H
    cx=im.width/2+dx*(p-0.5)*(im.width-cw)*0.5; cy=im.height/2+dy*(p-0.5)*(im.height-ch)*0.5
    fx,fy=s.get("focus",(0.5,0.5)); cx+=(fx-0.5)*(im.width-cw); cy+=(fy-0.5)*(im.height-ch)
    cx=min(max(cx,cw/2),im.width-cw/2); cy=min(max(cy,ch/2),im.height-ch/2)
    cx+=shift*cw
    return (cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)
_framed={}
def framed(name):
    if name in _framed: return _framed[name]
    p=f"{HERE}/raw/{name}"
    im=autocrop(Image.open(p).convert("RGB"))
    if im.width/im.height>=1.25: _framed[name]=None; return None
    im=ImageOps.autocontrast(im,cutoff=1); im=ImageEnhance.Contrast(im).enhance(1.12); im=ImageEnhance.Color(im).enhance(0.88)
    CW,CH=int(W*1.12),int(H*1.12)
    s_=max(CW/im.width,CH/im.height); bgi=im.resize((int(im.width*s_)+1,int(im.height*s_)+1),Image.BILINEAR)
    bgi=bgi.crop(((bgi.width-CW)//2,(bgi.height-CH)//2,(bgi.width-CW)//2+CW,(bgi.height-CH)//2+CH)).filter(ImageFilter.GaussianBlur(28))
    bgi=ImageEnhance.Brightness(bgi).enhance(0.38).convert("RGBA")
    h=int(CH*0.9); fg=im.resize((int(im.width*h/im.height),h),Image.LANCZOS); fg=ImageEnhance.Brightness(fg).enhance(0.82).convert("RGBA")
    x=(CW-fg.width)//2; y=(CH-h)//2
    sh=Image.new("RGBA",(CW,CH)); ImageDraw.Draw(sh).rectangle((x+10,y+16,x+fg.width+10,y+h+16),fill=(0,0,0,190)); sh=sh.filter(ImageFilter.GaussianBlur(22))
    bgi.alpha_composite(sh); bgi.alpha_composite(fg,(x,y))
    a=np.asarray(bgi.convert("RGB")).astype(np.float32)*np.array([1.04,0.98,0.9]); out=Image.fromarray(np.clip(a,0,255).astype(np.uint8))
    _framed[name]=out; return out
_bg_frame_orig=bg_frame
def bg_frame(i,t):
    s=scenes[i]
    if s.get("img") and s["img"]!="bookworm.jpg":
        F=framed(s["img"])
        if F is not None:
            t0=s["t"]; t1=scenes[i+1]["t"] if i+1<len(scenes) else DUR; p=min(1,(t-t0)/max(0.1,t1-t0))
            z=1.0+0.06*p if s.get("z",[1,1.1])[0]<=s.get("z",[1,1.1])[1] else 1.06-0.06*p
            cw=F.width/z/1.12*1.0; ch=cw*H/W; cx=F.width/2; cy=F.height/2
            return F.transform((W,H),Image.EXTENT,(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2),Image.BILINEAR)
    if s.get("img") and s.get("parallax"):
        L=layers(s["img"])
        if L:
            t0=s["t"]; t1=scenes[i+1]["t"] if i+1<len(scenes) else DUR; p=(t-t0)/max(0.1,t1-t0)
            bg,fg=L
            out=bg.transform((W,H),Image.EXTENT,extent(bg,s,p,shift=0.02*(p-0.5)),Image.BILINEAR).convert("RGBA")
            f=fg.transform((W,H),Image.EXTENT,extent(fg,s,p,shift=-0.035*(p-0.5),extra=1.04),Image.BILINEAR)
            out.alpha_composite(f); return out.convert("RGB")
    return _bg_frame_orig(i,t)
_LEAK=None
def leak(fr,p):
    global _LEAK
    if _LEAK is None:
        y,x=np.mgrid[0:H,0:W*2]; g=np.exp(-((x-W)/(W*0.35))**2)*np.exp(-((y-H*0.45)/(H*0.9))**2)
        _LEAK=np.dstack([g*255,g*170,g*70]).astype(np.float32)
    off=int((1-p)*W); band=_LEAK[:,off:off+W]; a=np.sin(np.pi*p)
    arr=np.asarray(fr.convert("RGB")).astype(np.float32); arr=arr+band*a*0.9
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8)).convert("RGBA")
SPECIALS=plan.get("specials",[])
def sepia(name,w,h,fy=0.35):
    im=Image.open(f"{HERE}/raw/{name}").convert("L"); im=ImageOps.autocontrast(im,cutoff=1)
    s=max(w/im.width,h/im.height); im=im.resize((int(im.width*s)+1,int(im.height*s)+1),Image.LANCZOS)
    x=(im.width-w)//2; y=int((im.height-h)*fy); im=im.crop((x,y,x+w,y+h))
    a=np.asarray(im).astype(float)/255; return Image.fromarray(np.dstack([a*225+18,a*200+14,a*160+10]).astype(np.uint8)).convert("RGBA")
_sp_cache={}
def draw_special(fr,sp,t):
    d0=t-sp["t0"]; dur=sp["t1"]-sp["t0"]; out=1-ease((t-(sp["t1"]-0.25))/0.25)
    if sp["type"]=="vs":
        fr.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,int(235*min(1,d0/0.2)*out))))
        k=("vs",sp["a"],sp["b"])
        if k not in _sp_cache: _sp_cache[k]=(sepia(sp["a"],W//2,H),sepia(sp["b"],W//2,H))
        A,B=_sp_cache[k]
        pa=ease(d0/0.35); pb=ease((d0-0.15)/0.35)
        la=A.copy(); la.putalpha(int(255*out)); lb=B.copy(); lb.putalpha(int(255*out))
        fr.alpha_composite(la,(int(-W/2*(1-pa)),0)); fr.alpha_composite(lb,(int(W/2+W/2*(1-pb)),0))
        dd=ImageDraw.Draw(fr); dd.line((W//2,0,W//2,H),fill=(242,194,48,int(255*out)),width=6)
        for j,(nm,xx) in enumerate([(sp["la"],W*0.25),(sp["lb"],W*0.75)]):
            if d0>0.5+j*0.15:
                spr,_,_=sprite(nm,70,(242,194,48),False); c=spr.copy(); c.putalpha(c.getchannel("A").point(lambda v:int(v*out)))
                fr.alpha_composite(c,(int(xx-spr.width/2),int(H*0.13)))
        if d0>0.45:
            p=min(1,(d0-0.45)/0.2); sc=1+1.5*(1-p)**3
            spr,_,_=sprite("VS",260,(242,194,48),False); g=glow(spr,(242,194,48))
            sp2=spr.resize((int(spr.width*sc),int(spr.height*sc)),Image.BILINEAR); g2=g.resize(sp2.size,Image.BILINEAR)
            for L in (g2,sp2):
                c=L.copy(); c.putalpha(c.getchannel("A").point(lambda v:int(v*min(1,p*2)*out)))
                fr.alpha_composite(c,(int(W/2-c.width/2),int(H*0.42-c.height/2)))
    elif sp["type"]=="counter":
        fr.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,int(200*min(1,d0/0.2)*out))))
        n=int(round(1+(sp["n"]-1)*ease(min(1,d0/(dur*0.55)))))
        spr,_,_=sprite(str(n),340,(242,194,48),False); g=glow(spr,(242,194,48))
        pul=1+0.08*max(0,1-(d0-dur*0.55)/0.25) if d0>dur*0.55 else 1
        for L in (g,spr):
            c=L.resize((int(L.width*pul),int(L.height*pul)),Image.BILINEAR) if pul!=1 else L.copy()
            c.putalpha(c.getchannel("A").point(lambda v:int(v*out)))
            fr.alpha_composite(c,(int(W/2-c.width/2),int(H*0.40-c.height/2)))
        lab,_,_=sprite(sp["label"],78,(245,240,230),False); c=lab.copy(); c.putalpha(c.getchannel("A").point(lambda v:int(v*out)))
        fr.alpha_composite(c,(int(W/2-lab.width/2),int(H*0.66)))
    elif sp["type"]=="card":
        bgc=smoke(t); bgc.putalpha(int(255*min(1,d0/0.15)*out)); fr.alpha_composite(bgc)
        fr.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,int(110*out))))
        p=ease(d0/0.5); dd=ImageDraw.Draw(fr); half=int(380*p)
        dd.line((W//2-half,int(H*0.38),W//2+half,int(H*0.38)),fill=(242,194,48,int(255*out)),width=3)
        dd.line((W//2-half,int(H*0.66),W//2+half,int(H*0.66)),fill=(242,194,48,int(255*out)),width=3)
        sm,_,_=sprite(sp["kicker"],52,(242,194,48),False); c=sm.copy(); c.putalpha(c.getchannel("A").point(lambda v:int(v*min(1,d0/0.3)*out)))
        fr.alpha_composite(c,(int(W/2-sm.width/2),int(H*0.28)))
        if d0>0.2:
            q=min(1,(d0-0.2)/0.18); sc=1+0.6*(1-q)**3
            fs=150
            while True:
                big,_,_=sprite(sp["title"],fs,(245,240,230),False)
                if big.width<W*0.86 or fs<70: break
                fs-=8
            g=glow(big,(242,194,48))
            for L in (g,big):
                c=L.resize((int(L.width*sc),int(L.height*sc)),Image.BILINEAR); c.putalpha(c.getchannel("A").point(lambda v:int(v*min(1,q*2)*out)))
                fr.alpha_composite(c,(int(W/2-c.width/2),int(H*0.52-c.height/2)))
def special_at(t):
    for sp in SPECIALS:
        if sp["t0"]<=t<sp["t1"]: return sp

def render(fi):
    t=fi/FPS
    i=scene_at(t); fr=bgplus(i,t)
    st=scenes[i]["t"]; tr=scenes[i].get("tr","cut"); dt=t-st
    if i>0:
        if tr=="fade" and dt<0.4:
            fr=Image.blend(bgplus(i-1,t),fr,ease(dt/0.4))
        elif tr=="whip" and dt<0.25:
            p=ease(dt/0.25); prev=bgplus(i-1,t)
            lay=Image.new("RGBA",(W,H),(0,0,0,255)); off=int(p*W)
            lay.alpha_composite(prev,(-off,0)); lay.alpha_composite(fr,(W-off,0))
            # motion blur
            acc=np.zeros((H,W,4),np.float32); a=np.asarray(lay).astype(np.float32); sh=int(60*(1-abs(2*p-1)))+1
            for k in range(5): acc+=np.roll(a,int(k*sh/4)-sh//2,axis=1)
            fr=Image.fromarray((acc/5).astype(np.uint8),"RGBA")
        elif tr=="zoom" and dt<0.3:
            p=ease(dt/0.3); fr=zoomc(fr,1.3-0.3*p)
            if dt<0.12: fr=Image.blend(zoomc(bgplus(i-1,t),1+0.4*dt/0.12),fr,dt/0.12)
        elif tr=="leak" and dt<0.6:
            if dt<0.25: fr=Image.blend(bgplus(i-1,t),fr,ease(dt/0.25))
            fr=leak(fr,dt/0.6)
        elif tr=="punch" and dt<0.18:
            fr=zoomc(fr,1.1-0.1*ease(dt/0.18))
        elif tr=="glitch" and dt<0.22:
            a=np.asarray(fr).copy(); rr=np.random.default_rng(fi)
            for k in range(8):
                y0=rr.integers(0,H-40); hh=rr.integers(10,60); a[y0:y0+hh]=np.roll(a[y0:y0+hh],rr.integers(-80,80),axis=1)
            a[...,0]=np.roll(a[...,0],12,axis=1); a[...,2]=np.roll(a[...,2],-12,axis=1); fr=Image.fromarray(a,"RGBA")
    char_layer(fr,i,t)
    # bottom gradient to seat character/text
    fr.alpha_composite(vignette())
    particles(fr,t)
    SP=special_at(t)
    if SP: draw_special(fr,SP,t)
    # CTA
    for c in ctas:
        if c["t0"]<=t<c["t1"]:
            a=ease((t-c["t0"])/0.5)*(1-ease((t-(c["t1"]-0.4))/0.4))
            fr.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,int(120*a))))
            bk=load_rgba(plan["book"],c.get("h",500)); fl=math.sin(t*2.0)*8
            sc=0.7+0.3*ease((t-c["t0"])/0.45)+0.015*math.sin(t*3)
            b=bk.resize((int(bk.width*sc),int(bk.height*sc)),Image.LANCZOS)
            bx=int(W*c.get("x",0.5)-b.width/2); by=int(H*c.get("y",0.6)-b.height/2+fl)
            glowl=Image.new("RGBA",(W,H)); gd=ImageDraw.Draw(glowl); r=int(b.height*0.8)
            pulse=0.8+0.2*math.sin(t*4)
            gd.ellipse((bx+b.width//2-r,by+b.height//2-r,bx+b.width//2+r,by+b.height//2+r),fill=(255,190,80,int(90*a*pulse))); glowl=glowl.filter(ImageFilter.GaussianBlur(90))
            fr.alpha_composite(glowl)
            lay=Image.new("RGBA",(W,H))
            sh=Image.new("RGBA",(b.width+120,b.height+120)); ImageDraw.Draw(sh).rectangle((60,75,60+b.width,75+b.height),fill=(0,0,0,210)); sh=sh.filter(ImageFilter.GaussianBlur(26))
            lay.alpha_composite(sh,(bx-60,by-60)); lay.alpha_composite(b,(bx,by))
            # shine sweep
            sp=((t-c["t0"])%3.0)/0.8
            if sp<1:
                sw=Image.new("L",b.size,0); sd=ImageDraw.Draw(sw); xx=int(-b.width*0.5+sp*b.width*2)
                sd.polygon([(xx,0),(xx+60,0),(xx+60-b.height//3,b.height),(xx-b.height//3,b.height)],fill=90)
                white=Image.new("RGBA",b.size,(255,255,255,0)); white.putalpha(sw); lay.alpha_composite(white,(bx,by))
            txt=c.get("btn","LIEN EN BIO")
            if not txt:
                lay.putalpha(Image.eval(lay.getchannel("A"),lambda v:int(v*a))); fr.alpha_composite(lay); continue
            pul=1+0.06*math.sin(t*6); f=font(FB,int((46 if len(txt)<14 else 36)*pul)); tb=f.getbbox(txt)
            bw=tb[2]-tb[0]+70; bh=tb[3]-tb[1]+36; bx2=int(W*c.get("x",0.5))-bw//2; by2=by+b.height+30
            d=ImageDraw.Draw(lay); d.rounded_rectangle((bx2,by2,bx2+bw,by2+bh),radius=14,fill=(200,22,40,255),outline=(255,210,120,255),width=3)
            d.text((bx2+35-tb[0],by2+18-tb[1]),txt,font=f,fill=(255,255,255,255))
            # arrow bounce
            ay=by2+bh//2; ax=bx2-60-int(12*abs(math.sin(t*5)))
            d.polygon([(ax,ay-18),(ax+36,ay),(ax,ay+18)],fill=(255,210,120,255))
            lay.putalpha(Image.eval(lay.getchannel("A"),lambda v:int(v*a)))
            fr.alpha_composite(lay)
    # ---- hook écrit à l'écran (dès la 1re image) ----
    HK=plan.get("hook_text")
    if HK and t<plan.get("hook_t1",5):
        a=min(1,t/0.25)*(1-ease((t-(plan["hook_t1"]-0.5))/0.5))
        f=font(FB,72); words=HK.upper().split(); lines_=[];cur=""
        for w_ in words:
            if f.getlength((cur+" "+w_).strip())>1500: lines_.append(cur); cur=w_
            else: cur=(cur+" "+w_).strip()
        lines_.append(cur); lay=Image.new("RGBA",(W,H)); d=ImageDraw.Draw(lay)
        y=int(H*0.10)
        for ln in lines_:
            tb=f.getbbox(ln); x=(W-(tb[2]-tb[0]))//2
            d.text((x,y),ln,font=f,fill=GOLD+(255,),stroke_width=6,stroke_fill=(0,0,0,255)); y+=tb[3]-tb[1]+28
        lay.putalpha(Image.eval(lay.getchannel("A"),lambda v:int(v*a))); fr.alpha_composite(lay)
    # ---- branding ----
    EC=plan.get("endcard",1e9)
    if t>=EC:
        de=t-EC; a=ease(de/0.6)
        fr.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,int(235*a))))
        lg=load_rgba("logo_full.png",560); sc=0.82+0.18*ease(de/0.7)+0.01*math.sin(t*2)
        l2=lg.resize((int(lg.width*sc),int(lg.height*sc)),Image.LANCZOS)
        gl=Image.new("RGBA",(W,H)); gd=ImageDraw.Draw(gl); cxl,cyl=W//2,int(H*0.42); r_=int(l2.width*0.62)
        gd.ellipse((cxl-r_,cyl-r_,cxl+r_,cyl+r_),fill=(240,190,70,int(70*a*(0.8+0.2*math.sin(t*3))))); gl=gl.filter(ImageFilter.GaussianBlur(60)); fr.alpha_composite(gl)
        l3=l2.copy(); l3.putalpha(Image.eval(l2.getchannel("A"),lambda v:int(v*a))); fr.alpha_composite(l3,(cxl-l2.width//2,cyl-l2.height//2))
        for j,(txt,col,sz,dly) in enumerate([("ABONNE-TOI",(242,194,48),70,0.5),(plan.get("endtext","pour découvrir la loi n°6"),(240,235,225),44,0.8)]):
            if de>dly:
                spr,asc_,_=sprite(txt.upper() if j==0 else txt,sz,col,j==1); p=ease((de-dly)/0.3)
                sp=spr.copy(); sp.putalpha(Image.eval(spr.getchannel("A"),lambda v,p=p:int(v*p)))
                fr.alpha_composite(sp,(W//2-spr.width//2,int(H*0.42+l2.height/2+10+j*85+20*(1-p))))
        chunks_on=False
    else:
        chunks_on=True
        if t>=0.0:
            wm=load_rgba("logo_wm2.png",110); wa=Image.eval(wm.getchannel("A"),lambda v:int(v*0.8)); w2=wm.copy(); w2.putalpha(wa)
            fr.alpha_composite(w2,(36,30))
    # text
    for k,c in enumerate(chunks):
        if not chunks_on: break
        if not (c[0]["c0"]<=t<c[0]["c1"]+0.12): continue
        out=1-ease((t-c[0]["c1"])/0.12) if t>c[0]["c1"] else 1
        pos=chunk_pos(k,c[0]["t"])
        if SP and SP["type"] in ("counter","card"): continue
        if SP and SP["type"]=="vs": pos="low"
        lines=layout(c,k)
        asc=[max(a for _,(s_,a,d_) in ln) for ln in lines]; dsc=[max(d_ for _,(s_,a,d_) in ln) for ln in lines]
        lh=[asc[q]+int(dsc[q]*0.35) for q in range(len(lines))]; Ht=sum(lh)
        lw=[sum(s_.width-2*PAD for _,(s_,a,d_) in ln)+18*(len(ln)-1) for ln in lines]
        cx={"left":W*0.28,"right":W*0.72}.get(pos,W*0.5)
        cy={"top":H*0.06+Ht/2,"low":H*0.88}.get(pos,H*0.45)
        y=cy-Ht/2
        for li,ln in enumerate(lines):
            stair=(li-(len(lines)-1)/2)*36
            x=cx-lw[li]/2+stair; base=y+asc[li]
            for (it,(spr,a_,d_)) in ln:
                x0=it[0]["t"]; big=it[2]>95
                if t>=x0:
                    if big:
                        p=min(1,(t-x0)/0.2); sc=1+1.2*(1-p)**3 - 0.08*math.sin(p*math.pi)
                        al=min(1,p*3)*out; dy=0
                    else:
                        p=ease((t-x0)/0.16); sc=1.0; al=p*out; dy=int(22*(1-p))
                    sp=spr if abs(sc-1)<1e-3 else spr.resize((max(1,int(spr.width*sc)),max(1,int(spr.height*sc))),Image.BILINEAR)
                    ox=int(x-PAD-(sp.width-spr.width)/2); oy=int(base-a_-PAD-(sp.height-spr.height)/2)+dy
                    if big and it[3]!=WHITE:
                        g=glow(spr,it[3]); g=g if sp is spr else g.resize(sp.size,Image.BILINEAR)
                        gl=0.6+0.4*math.sin(t*5)
                        g2=g.copy(); g2.putalpha(Image.eval(g.getchannel("A"),lambda v,al=al*gl:int(v*al))); fr.alpha_composite(g2,(ox,oy))
                    if al<1: sp=sp.copy(); sp.putalpha(Image.eval(sp.getchannel("A"),lambda v,al=al:int(v*al)))
                    fr.alpha_composite(sp,(ox,oy))
                x+=spr.width-2*PAD+18
            y+=lh[li]
    # events: shake, flash, zoom punch, chromatic aberration
    sx=sy=0; fl=0; zp=0; ca=0
    for e in events:
        de=t-e["t"]
        if 0<=de<0.6:
            if e.get("shake"): a=e["shake"]*(1-de/0.6)**2; sx+=a*math.sin(de*90); sy+=a*math.cos(de*77); zp=max(zp,0.06*(1-de/0.45) if de<0.45 else 0); ca=max(ca,e["shake"]*(1-de/0.35) if de<0.35 else 0)
            if e.get("flash") and de<0.25: fl=max(fl,0.55*e["flash"]*(1-de/0.2)) if de<0.2 else fl
    rgb=fr.convert("RGB")
    s_=1.03+zp
    if sx or sy or zp: rgb=rgb.transform((W,H),Image.AFFINE,(1/s_,0,(W-W/s_)/2-sx,0,1/s_,(H-H/s_)/2-sy),Image.BILINEAR)
    a=np.asarray(rgb).astype(np.int16)
    if ca>1:
        o=int(ca*0.8); a=a.copy(); a[...,0]=np.roll(a[...,0],o,axis=1); a[...,2]=np.roll(a[...,2],-o,axis=1)
    if fl>0: a=(a*(1-min(1,fl))+np.array([255,240,220])*min(1,fl)).astype(np.int16)
    g=gr[fi%8]; a=a+(np.asarray(g)[:,:,:1].astype(np.int16)-128)//6
    return np.clip(a,0,255).astype(np.uint8)
if __name__=="__main__":
    a,b,out=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
    p=subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",out],stdin=subprocess.PIPE)
    for fi in range(a,b): p.stdin.write(render(fi).tobytes())
    p.stdin.close(); p.wait()
