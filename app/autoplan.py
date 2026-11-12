"""Plan automatique (format cinéma) : une image choisie par phrase avec CLIP, personnage du livre,
couverture aux appels « écris LIVRE en commentaire », impacts. Écrit plan.json dans le dossier de travail."""
import json, re, os, sys, unicodedata, numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import library
def nz(s):
    s=unicodedata.normalize("NFD",s.lower()); return re.sub(r"[^a-z0-9]","","".join(c for c in s if unicodedata.category(c)!="Mn"))
STOP=set("alors avant apres aussi autre autres avait avec avoir cette comme dans depuis encore elle elles entre etait faire leurs mais meme moins notre nous parce pendant plus pour quand quelque sans sont tout toute toutes tous votre vous juste deja jamais rien".split())
NEG=set(nz(w) for w in "perdu perdre jamais rien peur mort ruine pauvre pauvres tort piege pieges pire mal humilie colere tard faux seul seule detruit detruire echec dette dettes honte blesse".split())
GOLD=[242,194,48]; RED=[220,40,60]
def make(work, meta):
    W=json.load(open(f"{work}/words.json")); lines=open(f"{work}/script.txt").read().strip().split("\n")
    n=len(lines); L=lambda i: min(x["t"] for x in W if x["line"]==i); LE=lambda i: max(x["t"] for x in W if x["line"]==i)+0.45
    END_T=W[-1]["t"]+1.3; DUR=END_T+6.4
    book=meta["book"]; titre_k=[nz(w) for w in re.findall(r"\w+",book["titre"]) if len(w)>3]; auteur_k=nz(book["auteur"].split()[-1])
    # ---- appels à l'action : ligne « commentaire » + ligne qui cite le livre juste avant
    titre_n=nz(re.sub(r"^(power,?|le|la|les|l')\s*","",book["titre"].lower()))
    def cites(i): t=nz(lines[i]); return auteur_k in t or titre_n[:18] in t
    # appels à l'action : lignes « bio » / « commentaire » / « dans le livre » (+ la ligne qui cite le livre juste avant)
    cta_lines=[i for i,l in enumerate(lines) if i>0 and ("commentaire" in l.lower() or re.search(r"\bbio\b",l.lower()) or "dans le livre" in l.lower())]
    ctas=[]; cta_span=set()
    for k,c in enumerate(cta_lines):
        if c in cta_span: continue
        s=c
        for j in range(c,max(0,c-3),-1):
            if cites(j): s=j; break
        e=c
        while e+1<n and e+1 in cta_lines: e+=1
        last=(e>=n-2)
        t0=L(s); t1=END_T if last else (L(e+1)-0.05)
        btn="ÉCRIS « LIVRE » EN COMMENTAIRE" if "commentaire" in " ".join(lines[s:e+1]).lower() else ("LIEN EN BIO" if re.search(r"\bbio\b"," ".join(lines[s:e+1]).lower()) else "")
        ctas.append({"t0":t0+0.3,"t1":t1,"h":600 if last else 560,"y":0.47,"x":0.7,"btn":btn}); cta_span.update(range(s,e+1 if not last else n))
    # présentation du livre (1re fois qu'il est cité, avant tout appel) : couverture sans bouton
    pres=next((i for i in range(1,n) if titre_n[:18] in nz(lines[i]) and i not in cta_span),None)
    if pres is None: pres=next((i for i in range(1,n) if cites(i) and i not in cta_span),None)
    if pres is not None and (not cta_lines or pres<min(cta_lines)):
        ctas.append({"t0":L(pres)+0.2,"t1":(L(pres+1)-0.05) if pres+1<n else END_T,"h":560,"y":0.5,"x":0.7,"btn":""}); cta_span.add(pres)
    ctas.sort(key=lambda c:c["t0"])
    # ---- personnage : après le hook (≈ 8 s)
    ch_from=next((i for i in range(n) if L(i)>=7.5),1)
    CH={"img":book.get("char","penseur_cut.png"),"x":0.8,"h":820}
    names,E=library.load(); used=set(); S=[{"t":0,"img":None,"char":None,"focus":[.5,.42],"z":[1,1.1],"pan":[0,0],"tr":"cut"}]
    texts=[]; starts=[]
    for i in range(1,n):
        if i in cta_span: continue
        ws=[x for x in W if x["line"]==i]
        if ws[-1]["t"]-ws[0]["t"]>4.8 and len(ws)>6:
            m=len(ws)//2; texts+= [" ".join(x["w"] for x in ws[:m+2]), " ".join(x["w"] for x in ws[m:])]; starts+=[(i,ws[0]["t"]),(i,ws[m]["t"])]
        else: texts.append(lines[i]); starts.append((i,ws[0]["t"]))
    T=library.embed_text(texts); ctx=library.embed_text([" ".join(lines[max(0,i-1):i+2]) for i,_ in starts])
    Q=0.75*T+0.25*ctx; sims=Q@E.T
    for k,(i,t) in enumerate(starts):
        order=np.argsort(-sims[k]); pick=next((names[j] for j in order if names[j] not in used), names[order[0]])
        used.add(pick)
        S.append({"t":t,"img":pick,"char":CH if i>=ch_from else None,"focus":[.5,.42],"z":[1.0,1.12] if k%2==0 else [1.12,1.0],"pan":[(-1)**k*0.5,0],"tr":"fade" if t>0 and k%9==0 else "cut"})
    for c in ctas: S.append({"t":c["t0"]-(0.3 if c["btn"] else 0.2),"img":"bookworm.jpg","char":None,"focus":[.5,.45],"z":[1,1.1],"pan":[0,0],"tr":"fade"})
    S.sort(key=lambda s:s["t"]); clean=[]
    for s in S:
        if clean and s["t"]-clean[-1]["t"]<0.4 and s["img"]!="bookworm.jpg": continue
        if clean and s["t"]-clean[-1]["t"]<0.4: clean[-1]=s; continue
        clean.append(s)
    # ---- rafale du hook (fin de la 1re phrase -> début de la 2e)
    hook=max(x["t"] for x in W if x["line"]==0)
    if n>1 and L(1)-hook>0.4:
        order=np.argsort(-(library.embed_text([lines[0]])[0]@E.T)); pool=[names[j] for j in order if names[j] not in used][:6]; t=hook; k=0
        while t<L(1)-0.2 and k<len(pool):
            clean.append({"t":t,"img":pool[k],"char":None,"focus":[.5,.45],"z":[1.08,1.0],"pan":[0,0],"tr":"cut","burst":1}); used.add(pool[k]); t+=0.3; k+=1
        clean.sort(key=lambda s:s["t"])
    # ---- mots en couleur (1 à 2 par phrase)
    E_={}
    for i,l in enumerate(lines):
        ws=[w for w in l.split() if len(nz(w))>=5 and nz(w) not in STOP]
        if not ws: continue
        picks=[ws[-1]]+([max(ws[:-1],key=len)] if len(ws)>3 else [])
        for w in picks:
            k=re.sub(r"[«»\"]","",w).upper(); E_[k]=[RED if nz(w) in NEG else GOLD,False,1.55 if w==ws[-1] else 1.4]
    # ---- impacts (tremblement + flash)
    ev=[{"t":hook,"shake":14,"flash":0.6}]
    for i,l in enumerate(lines):
        if re.match(r"(premier|deuxi[eè]me|troisi[eè]me|un|deux|trois)\b",l.strip().lower()) and L(i)>10: ev.append({"t":L(i),"shake":10,"flash":0.3})
    if n>4: ev.append({"t":L(n//3),"shake":12,"flash":0.4})
    plan={"base":[],"duration":DUR,"emphasis":E_,"regions":[[0,L(ch_from),"center"],[L(ch_from),999,"left"]],"scenes":clean,"events":ev,
          "ctas":ctas,"book":book.get("cover","book3d.png"),"smoke_from":3.0,"endcard":END_T,"endtext":"pour découvrir le prochain livre","hook_text":"","char_entree":"sol","hook_t1":(L(2) if n>2 else 5.0)}
    json.dump(plan,open(f"{work}/plan.json","w"),ensure_ascii=False)
    return {"plans":len(clean),"images":len(used),"duree":round(DUR,1),"ctas":len(ctas)}
if __name__=="__main__":
    print(make(sys.argv[1], json.load(open(sys.argv[2]))))
