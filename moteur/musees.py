"""Télécharge des tableaux du domaine public par thème (Art Institute of Chicago + Met Museum).
Usage : python3 musees.py prefixe "requete1;requete2;..." N   -> raw/prefixe_XXX.jpg + raw/prefixe_meta.json"""
import json,sys,os,io,time,urllib.request,urllib.parse
from PIL import Image
UA={"User-Agent":"PersonalVideoMontage/1.1 (https://claude.ai/code; personal one-off use)","AIC-User-Agent":"PersonalVideoMontage (claude.ai/code)"}
def get(u,js=True):
    for k in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read(); return json.loads(r) if js else r
        except Exception as e: time.sleep(3*(k+1))
    return None
pre,qs,N=sys.argv[1],sys.argv[2].split(";"),int(sys.argv[3])
metaf=f"raw/{pre}_meta.json"; meta=json.load(open(metaf)) if os.path.exists(metaf) else {}
seen={m["src"] for m in meta.values()}
def save(src,url,title,artist,q):
  with lock:
    if src in seen: return False
    seen.add(src)
  if True:
    d=get(url,False)
    if not d: return False
    try: im=Image.open(io.BytesIO(d)).convert("RGB")
    except Exception: return False
    if min(im.size)<700: return False
    with lock:
        k=f"{pre}_{len(meta):03d}"; meta[k]={"src":src,"title":title,"artist":artist,"q":q}
        im.save(f"raw/{k}.jpg",quality=90); json.dump(meta,open(metaf,"w"),ensure_ascii=False,indent=0)
    return True
import threading
lock=threading.Lock()
def run(q):
    got=0
    # Art Institute of Chicago
    u="https://api.artic.edu/api/v1/artworks/search?"+urllib.parse.urlencode({"q":q,"limit":40,"fields":"id,title,image_id,is_public_domain,artist_display,classification_title,artwork_type_title"})
    d=get(u) or {}
    for a in d.get("data",[]):
        if got>=N: break
        if not a.get("is_public_domain") or not a.get("image_id"): continue
        if (a.get("artwork_type_title") or "") not in ("Painting","Print","Drawing and Watercolor"): continue
        if save("aic:%s"%a["id"],f"https://www.artic.edu/iiif/2/{a['image_id']}/full/1686,/0/default.jpg",a.get("title"),a.get("artist_display"),q): got+=1
        time.sleep(0.3)
    # Met Museum
    u="https://collectionapi.metmuseum.org/public/collection/v1.1/search?"+urllib.parse.urlencode({"q":q,"hasImages":"true","limit":60})
    ids=((get(u) or {}).get("objectIDs",[]) or [])[:30]
    for oid in ids:
        if got>=N*2: break
        o=get(f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}") or {}
        if not o.get("isPublicDomain") or not o.get("primaryImage"): continue
        if o.get("classification") not in ("Paintings","Drawings","Prints"): continue
        if save("met:%s"%oid,o["primaryImage"],o.get("title"),o.get("artistDisplayName"),q): got+=1
        time.sleep(0.3)
    print(q,"->",got,flush=True)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(6) as ex: list(ex.map(run,qs))
print("TOTAL",len(meta))
