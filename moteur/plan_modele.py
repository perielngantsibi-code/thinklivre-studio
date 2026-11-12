# Style "ancien" (validé) : une image choisie par phrase, mouvement lent, pas d'effets spéciaux
import json, re, os
W=json.load(open("words.json"))
def nz(s): return re.sub(r"[^\w'\-]","",s.lower())
def T(w,o=1,after=0):
    c=0
    for x in W:
        if x["t"]>=after and nz(w)==nz(x["w"]):
            c+=1
            if c==o: return x["t"]
    raise Exception(w)
def L(i): return min(x["t"] for x in W if x["line"]==i)
G=[242,194,48];R=[220,40,60];V=[90,200,100]
E={}
def e(ws,col,it=False,sc=1.55):
    for w in ws.split(): E[w]=[col,it,sc]
e("DISPUTE…",R,False,1.5); e("RAISON",G,False,1.5); e("GAGNE.",G,False,1.8); e("RÈGLES",G,False,1.5); e("JEU.",G,True,1.4)
e("PERDU",R,False,1.5); e("TARD.",R,True,1.6); e("INTELLIGENCE.",G,True,1.4); e("TECHNIQUES…",R,False,1.5)
e("BERLIN.",G,False,1.8); e("1820.",G,False,1.8); e("HEURE",R); e("CRAQUER.",G,True,1.4); e("POIGNÉE",R,True,1.4)
e("AMÈRE",R,True,1.4); e("SUFFIT",R,False,1.5); e("GAGNER.",G,False,1.8); e("INCROYABLE.",G,True,1.4); e("RUSES",R,False,1.5); e("TORT.",R,True,1.4)
e("DÉRANGEANT…",R,True,1.4); e("MORT.",R,True,1.4); e("BIO,",R,False,1.4); e("IMPORTANT",G); e("TROIS",G); e("RUSES",R)
e("SUJET.",R,False,1.6); e("CALMEMENT",G,True,1.4); e("DÉPART.",G,False,1.5); e("DÉFORME",R,False,1.5); e("EXTRÊME…",R,True,1.4); e("VRAIE",G,False,1.4); e("PHRASE.",G)
e("ARGUMENT…",R); e("TOI.",R,False,1.6); e("DERNIER",R,True,1.4); e("CALME.",G,False,1.6); e("INSULTE…",R,True,1.4); e("PERDU.",R,False,1.9)
e("VRAIE.",G,True,1.4); e("FORT",R,False,1.6); e("FICELLES.",G,False,1.6); e("POUVOIR.",G,False,1.7); e("DÉBATTRE.",G); e("LIEN",R,False,1.6); e("BIO.",R,False,1.6)
CH={"img":"schop_char.png","x":0.8,"h":820}   # personnage propre au livre
S=[]
def s(t,img,char=CH,focus=(0.5,0.42),z=(1.0,1.1),pan=(0,0),tr="cut"):
    S.append({"t":t,"img":img,"char":char,"focus":list(focus),"z":list(z),"pan":list(pan),"tr":tr})
HOOK=T("gagne.")
s(0,None,None)
# hook
s(L(1),"sch_021.jpg",None)                                  # règles du jeu : joueurs de cartes (Cézanne)
s(L(2),"sch_017.jpg",None)                                  # tu as perdu un débat : dispute littéraire (Daumier)
s(L(3),"sch_229.jpg",None)                                  # tu rentres chez toi : étudiant à la bougie
s(T("Et",1,L(3)),"sch_037.jpg",None,z=(1.05,1.15))          # trop tard : philosophe qui pleure
s(L(4),"sch_027.jpg",None)                                  # intelligence : savant dans son étude
s(L(5),"sch_201.jpg",None,focus=(0.5,0.4))                  # techniques : la diseuse de bonne aventure (ruse)
# histoire
s(L(6),"ber_015.jpg",None,tr="fade")                        # Berlin 1820 (Gaertner, Parochialstraße 1831)
s(L(7),"sch_portrait_schop.jpg",None,focus=(0.5,0.3))       # jeune philosophe Schopenhauer
s(T("défier",1,L(7)),"sch_portrait_hegel.jpg",None,focus=(0.5,0.3))  # Hegel
s(L(8),"sch_067.jpg")                                       # ses cours
s(L(9),"sch_075.jpg")                                       # salle pleine
s(L(10),"sch_059.jpg")                                      # poignée d'étudiants
s(L(11),"sch_035.jpg",focus=(0.5,0.3))                      # convaincu d'avoir raison
s(L(12),"sch_224.jpg")                                      # vérité amère : contemplation
s(L(13),"sch_161.jpg")                                      # ne suffit pas
s(L(14),"sch_071.jpg")                                      # quelque chose d'incroyable : nuit de travail
s(L(15),"sch_032.jpg")                                      # observé, noté (Dürer, saint Jérôme)
s(T("toutes",1,L(15)),"sch_020.jpg")                        # ruses des gens (Daumier)
s(L(16),"sch_053.jpg")                                      # 38 stratagèmes : échecs
s(L(17),"sch_230.jpg",tr="fade")                            # petit livre dérangeant
s(L(18),"bookworm.jpg",None,focus=(0.5,0.45),tr="fade")     # CTA 1
s(L(21),"sch_010.jpg",tr="fade")                            # trois ruses
# ruse 1 : diversion
s(L(22),"sch_012.jpg")
s(L(23),"sch_023.jpg")                                      # change de sujet
s(L(24),"sch_103.jpg")                                      # ramène calmement
# ruse 2 : exagération
s(L(25),"sch_215.jpg")                                      # caricature = exagération
s(L(26),"sch_293.jpg")
s(L(27),"sch_119.jpg",focus=(0.5,0.35))                     # répète ta vraie phrase
# ruse 3 : attaque personnelle
s(L(28),"sch_110.jpg")
s(L(29),"sch_006.jpg")                                      # il s'en prend à toi
s(L(30),"sch_049.jpg")                                      # dernier stratagème : échecs
s(L(31),"sch_217.jpg")                                      # reste calme
# question / espoir
s(L(32),"r_moine.jpg",tr="fade")
s(L(33),"sch_190.jpg")                                      # parlait plus fort : public
s(L(34),"sch_181.jpg")
s(L(35),"sch_258.jpg",tr="fade")                            # tu vois les ficelles : lever du jour
s(L(36),"wanderer.jpg")
s(L(37),"bookworm.jpg",None,focus=(0.5,0.45),tr="fade")     # CTA 2
END_T=W[-1]["t"]+1.3; DUR=END_T+6.4
ts_=[x["t"] for x in S]; print("NON-MONO",[(i,S[i]["img"]) for i in range(1,len(ts_)) if ts_[i]<=ts_[i-1]])
# rafale du hook (0,3 s) : images toutes différentes et jamais reprises ensuite
used={x["img"] for x in S}
POOL=[i for i in ["sch_007.jpg","sch_158.jpg","sch_025.jpg","sch_127.jpg","sch_209.jpg","sch_148.jpg","sch_141.jpg","sch_024.jpg","sch_226.jpg","eminence.jpg","sch_013.jpg","sch_022.jpg"] if i not in used and os.path.exists("raw/"+i)]
BURST=[(HOOK,L(1)-0.02)]
out=[]
for a,b in BURST:
    t=a;k=0
    while t<b-0.2:
        out.append({"t":t,"img":POOL[k%len(POOL)],"char":None,"focus":[0.5,0.45],"z":[1.08,1.0],"pan":[0,0],"tr":"cut","burst":1}); t+=0.3; k+=1
for i,x in enumerate(S):
    out.append(dict(x))
# mouvement de caméra lent alterné (pas de recadrage dans une même image)
k=0
for x in out:
    if x.get("img") and not x.get("burst") and x["img"]!="bookworm.jpg":
        x["z"]=[1.0,1.12] if k%2==0 else [1.12,1.0]; x["pan"]=[(-1)**k*0.5,0]; k+=1
out.sort(key=lambda s:s["t"])
ev=[]
def f(t,sh,fl): ev.append({"t":t,"shake":sh,"flash":fl})
f(HOOK,14,0.6); f(L(6),12,0.5); f(L(16),14,0.5); f(T("gagner.",1,49),12,0.4); f(T("perdu.",1,115),14,0.5); f(T("pouvoir.",1,130),12,0.4)
ctas=[{"t0":L(18)+0.6,"t1":L(21)-0.05,"h":560,"y":0.5,"x":0.7},{"t0":L(37)+0.2,"t1":END_T,"h":600,"y":0.5,"x":0.7}]
regions=[[0,L(8),"center"],[L(8),999,"left"]]
P={"base":S,"duration":DUR,"emphasis":E,"regions":regions,"scenes":out,"events":ev,"ctas":ctas,"book":"book_schop3d.png","smoke_from":3.0,"endcard":END_T,"endtext":"pour découvrir le prochain livre"}
json.dump(P,open("plan.json","w"),ensure_ascii=False)
from collections import Counter
c=Counter(x["img"] for x in out if x.get("img"))
print(len(out),"plans; DUR",round(DUR,1),"répétées:",[k for k,v in c.items() if v>1],"manquantes:",[k for k in c if not os.path.exists("raw/"+k)])
