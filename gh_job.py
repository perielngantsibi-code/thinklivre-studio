"""Fabrique UNE vidéo dans GitHub Actions.
Usage : python gh_job.py <texte_id> [chemin_voix.mp3]
Lit data/textes.json, data/config.json (comptes ElevenLabs : nom/actif/secret), catalogue/livres.json.
Les clés ElevenLabs viennent des secrets GitHub (variable SECRETS = toJSON(secrets))."""
import os, sys, json, shutil
ROOT=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(ROOT,"app"))
import pipeline
from store import KNOWN
tid=sys.argv[1]; voix=sys.argv[2] if len(sys.argv)>2 and sys.argv[2] else None
textes=json.load(open(os.path.join(ROOT,"data","textes.json")))
t=next(x for x in textes if x["id"]==tid)
cfg=json.load(open(os.path.join(ROOT,"data","config.json")))
sec=json.loads(os.environ.get("SECRETS","{}") or "{}")
comptes=[{"nom":c["nom"],"key":sec.get(c["secret"],""),"actif":c.get("actif",True)} for c in cfg.get("comptes",[])]
class St:
    def settings(self): return {"comptes":comptes,"voice_id":cfg.get("voice_id",""),"voice_nom":cfg.get("voice_nom","")}
cat=json.load(open(os.path.join(ROOT,"catalogue","livres.json")))["livres"]
from store import slug
b=next(x for x in cat if slug(x["titre"])==t["livre"])
cover=b.get("cover") or KNOWN.get(b["titre"],("book3d.png",""))[0]; char=KNOWN.get(b["titre"],("","penseur_cut.png"))[1]
if b.get("char"): char=b["char"]
job={"id":tid+"_"+os.environ.get("GITHUB_RUN_ID","local"),"texte":t,"livre":{"titre":b["titre"],"auteur":b["auteur"],"cover":cover,"char":char},
     "voix_fichier":os.path.join(ROOT,voix) if voix else None,"hook":""}
def progress(p,e): print(f"::notice title=Étape::{p}% — {e}",flush=True)
res=pipeline.run(job,St(),progress)
os.makedirs(os.path.join(ROOT,"out"),exist_ok=True)
shutil.copy(res["video"],os.path.join(ROOT,"out","video.mp4")); shutil.copy(res["thumb"],os.path.join(ROOT,"out","miniature.jpg"))
open(os.path.join(ROOT,"out","description.txt"),"w").write(t.get("description",""))
print("OK",res)
