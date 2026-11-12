import sherpa_onnx, soundfile as sf, json, numpy as np
d="sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/"
r=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=d+"encoder.int8.onnx",decoder=d+"decoder.int8.onnx",joiner=d+"joiner.int8.onnx",tokens=d+"tokens.txt",model_type="nemo_transducer",num_threads=4)
a,sr=sf.read("voix16.wav",dtype="float32")
out=[]
# chunk ~20s at silences: simple fixed chunks with overlap avoided by cutting at low-energy points
step=sr*20; i=0
while i<len(a):
    j=min(len(a),i+step)
    if j<len(a):
        win=a[j-sr*2:j+sr*2]; e=np.convolve(win**2,np.ones(800),'same'); j=j-sr*2+int(np.argmin(e))
    if j-i<sr//2: i=j if j>i else len(a); continue
    s=r.create_stream(); s.accept_waveform(sr,a[i:j]); r.decode_stream(s)
    res=s.result
    for t,ts in zip(res.tokens,res.timestamps): out.append([t,round(ts+i/sr,3)])
    i=j
json.dump(out,open("tokens.json","w"),ensure_ascii=False)
print("".join(t for t,_ in out))
