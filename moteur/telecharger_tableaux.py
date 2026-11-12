import json,urllib.request,urllib.parse,sys,time,io,re,os
from urllib.error import HTTPError
from PIL import Image
UA={"User-Agent":"PersonalVideoMontage/1.1 (https://claude.ai/code; personal one-off use)"}
def get(u,js=True):
    for k in range(4):
        try:
            r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read()
            return json.loads(r) if js else r
        except HTTPError as e:
            if e.code==404: return None
            time.sleep(6*(k+1))
        except Exception: time.sleep(6*(k+1))
    return None
q=json.load(open(sys.argv[1]))
for name,query in q.items():
    if os.path.exists(f"raw/{name}.jpg"): continue
    s=get("https://en.wikipedia.org/w/api.php?"+urllib.parse.urlencode({"action":"query","list":"search","srsearch":query,"format":"json","srlimit":1}))
    if not s or not s.get("query",{}).get("search"): print("NOTFOUND",name,flush=True); continue
    title=s["query"]["search"][0]["title"]
    d=get("https://en.wikipedia.org/api/rest_v1/page/summary/"+urllib.parse.quote(title.replace(" ","_")))
    oi=(d or {}).get("originalimage",{}); u=oi.get("source","").split("?")[0]; w=oi.get("width",0)
    if not u: print("NOIMG",name,title,flush=True); continue
    if "/thumb/" in u: u=re.sub(r"/\d+px-","/1920px-",u) if w<3840 else u
    elif w>1920:
        base=u.replace("/wikipedia/commons/","/wikipedia/commons/thumb/"); fn=u.rsplit("/",1)[1]; u=f"{base}/1920px-{fn}"
    data=get(u,False)
    if not data: print("FAIL",name,flush=True); continue
    im=Image.open(io.BytesIO(data)).convert("RGB"); im.save(f"raw/{name}.jpg",quality=93); print(name,im.size,"|",title,flush=True); time.sleep(2)
print("DONE",flush=True)
