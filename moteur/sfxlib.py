import numpy as np, soundfile as sf, json
from scipy.signal import fftconvolve, butter, sosfilt
SR=48000; rng=np.random.default_rng(7)
voice,_=sf.read("voix_fx.wav"); voice=voice if voice.ndim==1 else voice.mean(1)
DUR=len(voice)/SR+1.0; N=int(DUR*SR)
W=json.load(open("words.json"))
import re
def nz(s): return re.sub(r"[^\w'\-]","",s.lower())
def T(word,occ=1,after=0):
    c=0
    for x in W:
        if x["t"]>=after and nz(word)==nz(x["w"]):
            c+=1
            if c==occ: return x["t"]
    raise Exception(word)
def t_(n): return np.arange(int(n*SR))/SR
def lp(x,f,o=4): return sosfilt(butter(o,f,'low',fs=SR,output='sos'),x)
def hp(x,f,o=4): return sosfilt(butter(o,f,'high',fs=SR,output='sos'),x)
def bp(x,a,b,o=2): return sosfilt(butter(o,[a,b],'band',fs=SR,output='sos'),x)
def ir(sec=3.0,damp=2.5):
    n=int(sec*SR); e=np.exp(-damp*np.arange(n)/SR*3/sec)
    L=rng.standard_normal(n)*e; R=rng.standard_normal(n)*e
    L=lp(L,6000); R=lp(R,6000); L[:200]*=np.linspace(0,1,200); R[:200]*=np.linspace(0,1,200)
    return np.stack([L,R],1)/np.sqrt(n)*6
IR=ir(3.5); IRs=ir(1.5)
def verb(x,wet=0.35,I=None):
    I=IR if I is None else I
    if x.ndim==1: x=np.stack([x,x],1)
    y=np.stack([fftconvolve(x[:,0],I[:,0]),fftconvolve(x[:,1],I[:,1])],1)
    out=np.zeros_like(y); out[:len(x)]+=x*(1-wet); out+=y*wet; return out
def st(x,pan=0.0):
    if x.ndim==2: return x
    return np.stack([x*np.sqrt((1-pan)/2),x*np.sqrt((1+pan)/2)],1)*1.41
mix_sfx=np.zeros((N+SR*8,2)); mix_mus=np.zeros((N+SR*8,2))
def put(buf,x,t,g=1.0):
    x=st(x); i=int(t*SR)
    if i<0: x=x[-i:]; i=0
    n=min(len(x),len(buf)-i); buf[i:i+n]+=x[:n]*g
def norm(x,p=1.0): return x/(np.abs(x).max()+1e-9)*p
# ---------- SFX ----------
def boom(d=2.5,f0=110,f1=32):
    t=t_(d); f=f1+(f0-f1)*np.exp(-t*6); ph=2*np.pi*np.cumsum(f)/SR
    x=np.sin(ph)*np.exp(-t*1.6); x+=lp(rng.standard_normal(len(t)),300)*np.exp(-t*12)*0.6
    return norm(np.tanh(x*1.5))
def hit(d=3.0,bright=0.5):
    b=boom(d); t=t_(d); n=hp(rng.standard_normal(len(t)),1500)*np.exp(-t*25)*bright
    return norm(verb(b+n,0.4))
def whoosh(d=0.9,up=True):
    t=t_(d); n=rng.standard_normal(len(t)); env=np.sin(np.pi*(t/d))**2
    out=np.zeros(len(t)); seg=1024
    for i in range(0,len(t),seg):
        p=i/len(t); fc=(300+3000*p) if up else (3300-3000*p)
        out[i:i+seg]=bp(n[i:i+seg+0],fc*0.6,min(fc*1.6,20000))[:len(out[i:i+seg])]
    x=lp(out,8000)*env
    pan=np.linspace(-0.7,0.7,len(t))
    return norm(np.stack([x*np.sqrt((1-pan)/2),x*np.sqrt((1+pan)/2)],1))
def riser(d=4.0):
    t=t_(d); env=(t/d)**2.5; n=rng.standard_normal(len(t))
    f=200+1800*(t/d)**2; tone=np.sin(2*np.pi*np.cumsum(f)/SR)*0.25+np.sin(2*np.pi*np.cumsum(f*1.5)/SR)*0.15
    x=(hp(n,800)*0.5+tone)*env
    return norm(verb(x,0.3,IRs))
def revswell(d=2.0):
    h=hit(d)[::-1]; h=h[-int(d*SR):]; return norm(h*np.linspace(0,1,len(h))[:,None]**2)
def gong(d=8.0,f0=98):
    t=t_(d); x=np.zeros(len(t))
    for r,a,dc in [(1,1,0.5),(1.48,0.6,0.7),(2.09,0.5,0.9),(2.56,0.35,1.1),(3.18,0.3,1.4),(4.1,0.2,1.8),(5.3,0.12,2.4)]:
        f=f0*r*(1+0.01*np.exp(-t*2)); x+=a*np.sin(2*np.pi*np.cumsum(f)/SR+rng.random()*6)*np.exp(-t*dc)
    x*=np.minimum(1,t/0.01); x+=lp(rng.standard_normal(len(t)),2000)*np.exp(-t*30)*0.3
    return norm(verb(x,0.4))
def taiko(f0=75):
    d=1.2; t=t_(d); f=f0*(1+0.6*np.exp(-t*30)); x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*5)
    x+=lp(rng.standard_normal(len(t)),900)*np.exp(-t*40)*0.5
    return norm(np.tanh(x*2))
def heart():
    d=1.0; out=np.zeros(int(d*SR))
    for off,a in [(0,1),(0.28,0.7)]:
        t=t_(0.3); f=55*(1+0.5*np.exp(-t*40)); b=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*18)*a
        i=int(off*SR); out[i:i+len(b)]+=b
    return norm(lp(out,200))
def pluck(f,d=3.0):
    n=int(SR/f); buf=rng.uniform(-1,1,n); out=np.zeros(int(d*SR))
    for i in range(len(out)):
        out[i]=buf[i%n]; buf[i%n]=0.996*0.5*(buf[i%n]+buf[(i+1)%n])
    return lp(out,4000)
def tick():
    t=t_(0.05); return hp(rng.standard_normal(len(t)),2500)*np.exp(-t*200)
def stone():
    t=t_(1.5); x=boom(1.5,90,30)*0.8+lp(hp(rng.standard_normal(len(t)),200),3000)*np.exp(-t*8)*0.7
    return norm(verb(x,0.25,IRs))
def gate():
    d=2.5; t=t_(d); f=70+20*np.sin(2*np.pi*3*t)+30*np.sin(2*np.pi*0.7*t)
    saw=((np.cumsum(f)/SR)%1)*2-1; x=bp(saw*(1+0.8*rng.standard_normal(len(t))*0.3),80,900)*np.minimum(1,t/0.2)*np.exp(-t*0.6)
    x=x/np.abs(x).max()*0.7; x[-int(0.9*SR):]+=boom(0.9,80,35)*0.9
    return norm(verb(x,0.3))
def shing():
    t=t_(1.8); x=np.zeros(len(t))
    for f,a in [(2400,1),(3550,0.7),(4890,0.5),(6200,0.4),(7900,0.25)]: x+=a*np.sin(2*np.pi*f*t)*np.exp(-t*3)
    x+=hp(rng.standard_normal(len(t)),3000)*np.exp(-t*25)*0.6
    return norm(verb(x,0.35,IRs))
def sting(d=3.0):
    t=t_(d); x=np.zeros(len(t))
    for f in [146.8,155.6,220,233.1]:
        for dt in (-0.3,0.3): x+=((np.cumsum(np.full(len(t),f+dt))/SR)%1*2-1)
    x=lp(x,1800)*(1+0.3*np.sin(2*np.pi*7*t))*np.minimum(1,t/0.05)*np.exp(-t*0.9)
    return norm(verb(x,0.4))
def shimmer(d=3.0):
    out=np.zeros(int(d*SR))
    for k,f in enumerate([1174.7,1480,1760,2349.3]):
        t=t_(d-k*0.12); s=np.sin(2*np.pi*f*t)*np.exp(-t*1.5)*np.minimum(1,t/0.01)
        i=int(k*0.12*SR); out[i:i+len(s)]+=s
    return norm(verb(out,0.6))
def rumble(d=4.0):
    t=t_(d); x=lp(rng.standard_normal(len(t)),120)*np.sin(np.pi*t/d)**0.5
    x+=lp(hp(rng.standard_normal(len(t)),300),1500)*np.exp(-t*1.2)*0.4*(rng.random(len(t))<0.02)
    return norm(verb(x,0.3))

def pad(freqs,d,cut=900,detune=0.25,vib=0.0):
    t=t_(d); x=np.zeros(len(t))
    for f in freqs:
        for dt in (-detune,0,detune):
            ph=np.cumsum(np.full(len(t),f+dt)*(1+vib*np.sin(2*np.pi*0.2*t)))/SR
            x+=(ph%1)*2-1
    x=lp(x,cut,2)/len(freqs)/3
    a=min(1.5,d/3); env=np.minimum(1,np.minimum(t/a,(d-t)/a)); return x*env
def drone(d,f=36.71):
    t=t_(d); x=np.sin(2*np.pi*f*t)+0.5*np.sin(2*np.pi*2*f*t)+0.2*np.sin(2*np.pi*3*f*t)
    a=min(2,d/3); return x*np.minimum(1,np.minimum(t/a,(d-t)/a))*0.5
