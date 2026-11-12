"""Stockage simple en JSON (réglages, livres, textes, vidéos)."""
import json, os, threading, time, uuid, re, unicodedata
HERE=os.path.dirname(os.path.abspath(__file__)); DATA=os.path.join(HERE,"data"); F=os.path.join(DATA,"store.json")
ROOT=os.path.dirname(HERE)
KNOWN={"Power, les 48 lois du pouvoir":("book3d.png","penseur_cut.png"),"L'art d'avoir toujours raison":("book_schop3d.png","schop_char.png"),
 "La psychologie de l'argent":("book_argent3d.png","penseur_cut.png"),"Plus malin que le Diable":("book_diable3d.png","penseur_cut.png"),
 "L'art de la séduction":("book_seduction3d.png","penseur_cut.png"),"Tout le monde n'a pas eu la chance de rater ses études":("book_roland3d.png","penseur_cut.png")}
def slug(s):
    s=unicodedata.normalize("NFD",s.lower()); s="".join(c for c in s if unicodedata.category(c)!="Mn"); return re.sub(r"[^a-z0-9]+","-",s).strip("-")[:50]
class Store:
    def __init__(self):
        self.lock=threading.RLock(); os.makedirs(DATA,exist_ok=True)
        if os.path.exists(F): self.d=json.load(open(F))
        else:
            cat=json.load(open(os.path.join(ROOT,"catalogue","livres.json")))
            livres=[]
            for b in cat["livres"]:
                cv,ch=KNOWN.get(b["titre"],(None,"penseur_cut.png")); livres.append({**b,"id":slug(b["titre"]),"cover":b.get("cover") or cv,"char":ch})
            self.d={"reglages":{"comptes":[],"voice_id":"","voice_nom":"","pin":""},"livres":livres,"textes":[],"videos":[]}
            seed=os.path.join(HERE,"seed_textes.json")
            if os.path.exists(seed):
                for t in json.load(open(seed)): self.add_texte(t,save=False)
            self.save()
    def save(self):
        with self.lock:
            tmp=F+".tmp"; json.dump(self.d,open(tmp,"w"),ensure_ascii=False,indent=1); os.replace(tmp,F)
    def settings(self): return self.d["reglages"]
    def livre(self,lid): return next((b for b in self.d["livres"] if b["id"]==lid),None)
    def add_texte(self,t,save=True):
        with self.lock:
            t={"id":uuid.uuid4().hex[:8],"livre":t["livre"],"sujet":t.get("sujet",""),"hook":t.get("hook",""),"script":t["script"],
               "description":t.get("description",""),"statut":"pret","cree":time.time()}
            self.d["textes"].append(t)
            if save: self.save()
            return t
    def texte(self,tid): return next((t for t in self.d["textes"] if t["id"]==tid),None)
    def add_video(self,texte,voix_fichier=None):
        with self.lock:
            v={"id":uuid.uuid4().hex[:10],"texte":texte["id"],"livre":texte["livre"],"sujet":texte["sujet"],"statut":"attente","progress":0,
               "etape":"En attente","cree":time.time(),"voix_fichier":voix_fichier}
            self.d["videos"].insert(0,v); texte["statut"]="en_cours"; self.save(); return v
    def video(self,vid): return next((v for v in self.d["videos"] if v["id"]==vid),None)
    def update_video(self,vid,**kw):
        with self.lock:
            v=self.video(vid); v.update(kw); self.save(); return v
