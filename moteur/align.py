import json,re,unicodedata,difflib
toks=json.load(open("tokens.json"))
# ASR words
aw=[]
for t,ts in toks:
    if t.startswith(" ") or not aw: aw.append([t.strip(),ts])
    else: aw[-1][0]+=t
aw=[w for w in aw if re.sub(r"\W","",w[0])]
def norm(s):
    s=unicodedata.normalize("NFD",s.lower()); s="".join(c for c in s if unicodedata.category(c)!="Mn")
    return re.sub(r"[^a-z0-9]","",s)
num={"2000":"deuxmille","100000":"centmille","48":"48","5":"cinq","47":"quarantesept","1":"un","2":"deux","3":"trois"}
lines=open("script.txt").read().strip().split("\n")
sw=[]
for li,l in enumerate(lines):
    for w in l.split():
        if re.sub(r"\W","",w): sw.append({"w":w,"line":li})
        elif sw: sw[-1]["w"]+=" "+w  # attach punctuation like ? :
A=[num.get(norm(w[0]),norm(w[0])) for w in aw]
# expand ASR number tokens like "deuxmille" to match multiple script words: join script norms
S=[norm(x["w"]) for x in sw]
sm=difflib.SequenceMatcher(None,S,A,autojunk=False)
for tag,i1,i2,j1,j2 in sm.get_opcodes():
    for k in range(i1,i2):
        if tag=="equal": sw[k]["t"]=aw[j1+k-i1][1]; sw[k]["ok"]=1
        elif j2>j1:
            # spread proportionally
            f=(k-i1)/max(1,i2-i1); idx=j1+int(f*(j2-j1)); sw[k]["t"]=aw[min(idx,len(aw)-1)][1]
# fill missing by interpolation
for k,x in enumerate(sw):
    if "t" not in x:
        p=next((sw[q]["t"] for q in range(k-1,-1,-1) if "t" in sw[q]),0)
        n=next((sw[q]["t"] for q in range(k+1,len(sw)) if "t" in sw[q]),p+0.5)
        x["t"]=p+(n-p)*0.5; x["interp"]=1
# enforce monotonic
for k in range(1,len(sw)):
    if sw[k]["t"]<sw[k-1]["t"]+0.05: sw[k]["t"]=sw[k-1]["t"]+0.05
json.dump(sw,open("words.json","w"),ensure_ascii=False,indent=0)
print(len(sw),"mots;",sum(1 for x in sw if x.get("interp")),"interpolés")
for li in range(len(lines)):
    ws=[x for x in sw if x["line"]==li]; print(f'{ws[0]["t"]:7.2f}  {lines[li][:60]}')
