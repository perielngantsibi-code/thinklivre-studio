"""THINK LIVRE Studio — serveur de l'appli (FastAPI). Lancer : uvicorn server:app --host 0.0.0.0 --port 8000"""
import os, json, threading, queue, time, traceback, hashlib, shutil, urllib.request
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from store import Store, ROOT, slug
import pipeline
HERE=os.path.dirname(os.path.abspath(__file__))
app=FastAPI(title="THINK LIVRE Studio"); S=Store(); Q=queue.Queue()
UPL=os.path.join(HERE,"data","img"); os.makedirs(UPL,exist_ok=True)
for _f in os.listdir(UPL): shutil.copy(os.path.join(UPL,_f),os.path.join(ROOT,"img",_f))  # images envoyées depuis l'appli (persistantes)
def tok(pin): return hashlib.sha256(("thinklivre:"+pin).encode()).hexdigest()
@app.middleware("http")
async def auth(req:Request, call_next):
    pin=S.settings().get("pin")
    if pin and req.url.path.startswith("/api/") and req.url.path!="/api/login" and req.cookies.get("tl")!=tok(pin):
        return JSONResponse({"erreur":"connexion"},status_code=401)
    return await call_next(req)
@app.post("/api/login")
async def login(req:Request):
    b=await req.json(); pin=S.settings().get("pin")
    if pin and b.get("pin")!=pin: raise HTTPException(401,"Code incorrect")
    r=JSONResponse({"ok":True}); r.set_cookie("tl",tok(pin or ""),max_age=3600*24*365,httponly=True,samesite="lax"); return r
# ---------- crédits ElevenLabs (cache 2 min)
_cred={"t":0,"v":[]}
def credits(force=False):
    if not force and time.time()-_cred["t"]<120: return _cred["v"]
    out=[]
    for a in S.settings().get("comptes",[]):
        if a.get("actif") is False: out.append({"nom":a["nom"],"actif":False}); continue
        try:
            rq=urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription",headers={"xi-api-key":a["key"]})
            s=json.load(urllib.request.urlopen(rq,timeout=15)); out.append({"nom":a["nom"],"actif":True,"restant":s["character_limit"]-s["character_count"],"limite":s["character_limit"],"plan":s.get("tier","")})
        except Exception as e: out.append({"nom":a["nom"],"actif":True,"erreur":"clé invalide ou réseau"})
    _cred.update(t=time.time(),v=out); return out
def pub_video(v):
    return {k:v.get(k) for k in ["id","livre","sujet","statut","progress","etape","erreur","cree","texte","duree"]}|{"miniature":f"/api/videos/{v['id']}/miniature" if v.get("thumb") else None}
@app.get("/api/etat")
def etat():
    d=S.d; prets=[t for t in d["textes"] if t["statut"]=="pret"]
    cr=credits(); restant=sum(c.get("restant",0) for c in cr if c.get("actif"))
    moy=max(1500,int(sum(len(t["script"]) for t in d["textes"])/max(1,len(d["textes"]))))
    return {"prochain":prets[0] if prets else None,"textes_prets":len(prets),"videos_possibles":restant//moy if cr else None,
            "credits":cr,"videos":[pub_video(v) for v in d["videos"][:6]],"publiees":sum(v["statut"]=="publiee" for v in d["videos"]),
            "voix":S.settings().get("voice_nom") or "","pin":bool(S.settings().get("pin"))}
@app.get("/api/livres")
def livres(): return S.d["livres"]
@app.post("/api/livres/{lid}/{kind}")
async def up_livre(lid:str,kind:str,f:UploadFile=File(...)):
    b=S.livre(lid)
    if not b or kind not in ("couverture","personnage"): raise HTTPException(404)
    from PIL import Image
    im=Image.open(f.file).convert("RGBA"); im.thumbnail((1400,1400))
    name=f"{'cover' if kind=='couverture' else 'char'}_{lid}.png"; im.save(os.path.join(ROOT,"img",name)); im.save(os.path.join(UPL,name))
    b["cover" if kind=="couverture" else "char"]=name; S.save(); return b
@app.get("/api/textes")
def textes(): return S.d["textes"]
@app.post("/api/textes")
async def add_texte(req:Request):
    b=await req.json()
    if not S.livre(b.get("livre","")) or len(b.get("script","").strip())<50: raise HTTPException(400,"Livre ou texte manquant")
    return S.add_texte(b)
@app.delete("/api/textes/{tid}")
def del_texte(tid:str):
    S.d["textes"]=[t for t in S.d["textes"] if t["id"]!=tid]; S.save(); return {"ok":True}
@app.post("/api/creer")
async def creer(req:Request):
    b=await req.json(); out=[]
    for tid in b.get("textes",[]):
        t=S.texte(tid)
        if t and t["statut"] in ("pret","erreur"): v=S.add_video(t); Q.put(v["id"]); out.append(v["id"])
    return {"videos":out}
@app.post("/api/creer_avec_voix")
async def creer_voix(texte:str=Form(...), f:UploadFile=File(...)):
    t=S.texte(texte)
    if not t: raise HTTPException(404)
    d=os.path.join(HERE,"data","voix"); os.makedirs(d,exist_ok=True); p=os.path.join(d,f"{texte}_{int(time.time())}.mp3")
    with open(p,"wb") as o: shutil.copyfileobj(f.file,o)
    v=S.add_video(t,voix_fichier=p); Q.put(v["id"]); return {"videos":[v["id"]]}
@app.get("/api/videos")
def videos(): return [pub_video(v) for v in S.d["videos"]]
@app.get("/api/videos/{vid}")
def video(vid:str):
    v=S.video(vid)
    if not v: raise HTTPException(404)
    t=S.texte(v["texte"]) or {}; return pub_video(v)|{"description":t.get("description",""),"hook":t.get("hook","")}
@app.get("/api/videos/{vid}/fichier")
def video_file(vid:str):
    v=S.video(vid)
    if not v or not v.get("video"): raise HTTPException(404)
    return FileResponse(v["video"],media_type="video/mp4",filename=f"ThinkLivre_{slug(v['sujet'] or v['livre'])}.mp4")
@app.get("/api/videos/{vid}/miniature")
def video_thumb(vid:str):
    v=S.video(vid)
    if not v or not v.get("thumb"): raise HTTPException(404)
    return FileResponse(v["thumb"],media_type="image/jpeg")
@app.post("/api/videos/{vid}/publiee")
def publiee(vid:str):
    v=S.update_video(vid,statut="publiee"); t=S.texte(v["texte"])
    if t: t["statut"]="utilise"; S.save()
    return pub_video(v)
@app.get("/api/reglages")
def get_reglages():
    r=S.settings(); return {"comptes":[{"nom":a["nom"],"cle":"••••"+a["key"][-4:]} for a in r["comptes"]],"voice_id":r["voice_id"],"voice_nom":r["voice_nom"],"pin":bool(r["pin"]),"credits":credits()}
@app.post("/api/reglages")
async def set_reglages(req:Request):
    b=await req.json(); r=S.settings()
    if b.get("ajouter_compte"):
        a=b["ajouter_compte"]
        if a.get("nom") and a.get("key"): r["comptes"].append({"nom":a["nom"].strip(),"key":a["key"].strip()})
    if "basculer_compte" in b:
        for a in r["comptes"]:
            if a["nom"]==b["basculer_compte"]: a["actif"]=not a.get("actif",True)
    if "supprimer_compte" in b: r["comptes"]=[a for a in r["comptes"] if a["nom"]!=b["supprimer_compte"]]
    for k in ("voice_id","voice_nom"):
        if k in b: r[k]=b[k].strip()
    if "pin" in b: r["pin"]=b["pin"].strip()
    S.save(); credits(force=True); return get_reglages()
# ---------- travailleur : une vidéo après l'autre
def worker():
    while True:
        vid=Q.get(); v=S.video(vid)
        if not v: continue
        t=S.texte(v["texte"]); b=S.livre(t["livre"])
        S.update_video(vid,statut="en_cours",etape="Démarrage",progress=1)
        try:
            job={"id":vid,"texte":t,"livre":{"titre":b["titre"],"auteur":b["auteur"],"cover":b.get("cover") or "book3d.png","char":b.get("char") or "penseur_cut.png"},"voix_fichier":v.get("voix_fichier"),"hook":t.get("hook","")}
            res=pipeline.run(job,S,lambda p,e: S.update_video(vid,progress=p,etape=e))
            S.update_video(vid,statut="prete",progress=100,etape="Prête",video=res["video"],thumb=res["thumb"],duree=res["duree"]); t["statut"]="video"; S.save()
        except Exception as e:
            traceback.print_exc(); S.update_video(vid,statut="erreur",etape="Erreur",erreur=str(e)[:400]); t["statut"]="erreur"; S.save()
for v in S.d["videos"]:
    if v["statut"] in ("attente","en_cours"): v["statut"]="attente"; Q.put(v["id"])
threading.Thread(target=worker,daemon=True).start()
app.mount("/",StaticFiles(directory=os.path.join(HERE,"static"),html=True),name="static")
