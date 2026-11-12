from sfxlib import *
import numpy as np, json
PL=json.load(open("plan.json")); OUT_D=PL["duration"]
def L(i): return min(x["t"] for x in W if x["line"]==i)
L_=int((OUT_D+3)*SR)
tt=np.arange(L_)/SR
keys=[(0,0),(3.0,0),(3.8,0.45),(L(2),0.5),(L(3),0.35),(L(5),0.55),(L(6),0.6),(L(7),0.65),(L(8),0.6),(L(10),0.4),(L(12),0.35),(L(13),0.7),(L(14),0.5),
      (L(15),0.65),(L(16),0.85),(L(18),0.45),(L(21),0.6),(L(25),0.7),(L(28),0.8),(L(31),0.75),(L(31)+2.0,0.05),(L(32),0.25),(L(33),0.2),(L(34),0.5),(L(36),0.8),(L(37),0.85),(L(37)+3,0.7),(OUT_D+3,0.5)]
I=np.interp(tt,[k[0] for k in keys],[k[1] for k in keys])
Wm=np.interp(tt,[0,L(34)-1,L(35),OUT_D+3],[0,0,1,1])
def osc(f,det=0.0): return np.sin(2*np.pi*np.cumsum(np.full(L_,f)*(1+det*np.sin(2*np.pi*0.05*tt)))/SR)
d=(osc(36.71)*0.9+osc(55.0,0.002)*0.5+osc(73.42,0.003)*0.25)*(0.75+0.25*np.sin(2*np.pi*0.07*tt))+osc(92.5,0.003)*0.3*Wm
saw=lambda f:((np.cumsum(np.full(L_,f))/SR)%1)*2-1
pad=lp(saw(146.83)+saw(147.3)+saw(174.61)*(1-Wm)+saw(185.0)*Wm+saw(220.0)+saw(219.4),700,2)/6
rum=lp(rng.standard_normal(L_),90,2)*3
wl=bp(rng.standard_normal(L_),500,1800)*0.5; wr=bp(rng.standard_normal(L_),500,1800)*0.5
mono=d*0.55+pad*0.35+rum*0.2
bed=np.zeros((L_,2)); bed[:,0]=(mono+wl*0.18)*I; bed[:,1]=(mono+wr*0.18)*I
bed=verb(bed,0.22)[:L_]
fx=np.zeros((L_,2)); P=lambda x,t,g: put(fx,x,t,g)
for e_ in PL["events"]:
    P(revswell(1.6),e_["t"]-1.55,0.5); P(hit(3,0.25),e_["t"],0.9)
for k in range(int((L(17)-L(16))/0.5)+1): P(tick(),L(15)+k*0.5,0.3)
for k in range(4): P(heart(),L(33)+k*0.72,0.7)
P(gong(10,73),L(38),0.5); P(shimmer(4),PL["ctas"][0]["t0"],0.5); P(shimmer(4),L(35),0.45)
EC=PL["endcard"]; P(shimmer(4),EC+0.1,0.6); P(boom(2.5,90,30),EC,0.5)
v=np.stack([voice,voice],1); vv=np.zeros((L_,2)); vv[:len(v)]=v
env=np.abs(vv[:,0]); k=int(0.2*SR); env=np.convolve(env,np.ones(k)/k,'same'); duck=1-0.3*np.clip(env/0.06,0,1)
b=norm(bed,1)*duck[:,None]; f=norm(fx,1)
ON=int(OUT_D*SR)
sf.write("stem_v.wav",vv[:ON],SR); sf.write("stem_b.wav",b[:ON],SR); sf.write("stem_f.wav",f[:ON],SR); print("ok")
