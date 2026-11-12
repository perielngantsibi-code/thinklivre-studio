"""Sons de transition variés, calés sur chaque changement d'image (style pro, discret)."""
import numpy as np
from sfxlib import SR, lp, hp, bp, verb, norm, boom, IRs, put, t_
R=np.random.default_rng(2026)
def _env(n,a=0.3,b=0.7):
    x=np.linspace(0,1,n); return np.where(x<a,(x/a)**2,((1-x)/(1-a))**1.5)
def air_whoosh(d,up,c0,c1):
    n=int(d*SR); w=R.standard_normal(n); out=np.zeros(n); seg=512
    for i in range(0,n,seg):
        p=i/n; fc=c0+(c1-c0)*(p if up else 1-p)
        out[i:i+seg]=bp(w[max(0,i-256):i+seg],max(60,fc*0.6),min(fc*1.6,20000))[-len(out[i:i+seg]):]
    return out*_env(n,0.55 if up else 0.25)
def swipe(d): return hp(air_whoosh(d,True,1500,7000),900)
def soft_thump(): return lp(boom(0.6,120,45),400)*0.9
def tick():
    n=int(0.05*SR); return hp(R.standard_normal(n),3000)*np.exp(-np.arange(n)/SR*140)
def click_wood():
    n=int(0.12*SR); t=np.arange(n)/SR; return (np.sin(2*np.pi*R.uniform(700,1100)*t)*np.exp(-t*60)+hp(R.standard_normal(n),2000)*np.exp(-t*200)*0.4)
def shimmer_rev(d):
    n=int(d*SR); t=np.arange(n)/SR; x=np.zeros(n)
    for f in R.choice([1174.7,1318.5,1568,1760,2093],3,replace=False): x+=np.sin(2*np.pi*f*t)
    return (x*(t/d)**2)*0.4
def low_swell(d):
    n=int(d*SR); return lp(R.standard_normal(n),300)*_env(n,0.8)*1.4
def paper(d):
    n=int(d*SR); w=R.standard_normal(n)*(R.random(n)<0.25); return bp(w,1200,6000)*_env(n,0.4)
def mx(*xs):
    n=max(len(x) for x in xs); o=np.zeros(n)
    for x in xs: o[:len(x)]+=x
    return o
def pan(x,p):
    return np.stack([x*np.sqrt((1-p)/2),x*np.sqrt((1+p)/2)],1)*1.41
def make(kind):
    d=R.uniform(0.35,0.7)
    if kind=="burst":
        x=R.choice([0,1,2]); s=[tick(),click_wood(),swipe(0.12)][x]; g=0.5
    elif kind=="section":
        s=mx(low_swell(R.uniform(0.6,1.0)),soft_thump()*0.6); s=verb(s,0.3,IRs)[:,0]; g=0.9
    else:
        x=R.integers(0,6)
        s=[air_whoosh(d,True,R.uniform(300,700),R.uniform(1800,3500)),air_whoosh(d,False,R.uniform(2500,4000),R.uniform(400,800)),
           swipe(R.uniform(0.18,0.3)),paper(R.uniform(0.25,0.4)),mx(shimmer_rev(R.uniform(0.4,0.7)),air_whoosh(0.4,True,500,2500)*0.5),
           mx(soft_thump(),swipe(0.2)*0.4)][x]; g=0.7
    s=norm(s,1)*g
    return pan(s,R.uniform(-0.6,0.6)), (len(s)/SR if kind!="burst" else 0.0)
def add_transitions(fx, scenes, events, gain=1.0):
    """fx: buffer stéréo. scenes: plan['scenes']. Impacts (events) gardent leur propre son."""
    ev=[e["t"] for e in events]
    for i,s in enumerate(scenes[1:],1):
        t=s["t"]
        if any(abs(t-e)<0.25 for e in ev): continue
        kind="burst" if s.get("burst") else ("section" if s.get("tr")=="fade" or (scenes[i-1].get("img") is None) else "cut")
        x,lead=make(kind)
        start=t-lead*0.6 if kind!="burst" else t
        put(fx,x,start,gain)
