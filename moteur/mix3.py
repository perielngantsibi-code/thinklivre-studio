import soundfile as sf, numpy as np
v,sr=sf.read("stem_v.wav"); b,_=sf.read("stem_b.wav"); f,_=sf.read("stem_f.wav")
import os
tr,_=sf.read("stem_t.wav") if os.path.exists("stem_t.wav") else (f*0,0)
dB=lambda x:10**(x/20)
out=v+b*dB(-5.5)+f*dB(-1.5)+tr*dB(-9)
n=int(2*sr); out[-n:]*=np.linspace(1,0,n)[:,None]
sf.write("mix.wav",out/np.abs(out).max()*0.95,sr)
