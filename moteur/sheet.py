import sys,os
sys.argv=[sys.argv[0]]+sys.argv[1:]
from render import render
from PIL import Image
ts=[float(a) for a in sys.argv[2:]]; out=sys.argv[1]
W=960;H=540; c=Image.new('RGB',(W*2,H*((len(ts)+1)//2)))
for i,t in enumerate(ts): c.paste(Image.fromarray(render(int(t*30))).resize((W,H)),((i%2)*W,(i//2)*H))
c.save(out)
