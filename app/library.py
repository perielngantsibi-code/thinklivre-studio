"""Index des tableaux (embeddings CLIP) pour choisir automatiquement l'image de chaque phrase."""
import os, json, numpy as np
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW=os.path.join(ROOT,"raw"); INDEX=os.environ.get("LIBRARY_INDEX") or os.path.join(ROOT,"app","data","library.npz")
# Jamais en sélection automatique : nudité, violence, logos, portraits propres à un livre
EXCLUDE={"calumny","pompeii","medusa","rebel","r_liberte","r_wagon","s_cleo_cesar","s_venus","s_cleo_poison","s_flaming",
 "s_primavera","pollice","janegrey","delaroche","judas","caesar","d_incendie","kuni_raw","kuni_heroes","kuni_bridge","khorgos",
 "r_anatomie","sch_006","sch_012","s_balancoire","s_sirenes","s_cleo_arthur","zhaoyun","sch_188","sch_humboldt",
 "sch_portrait_hegel","sch_portrait_schop","bookworm","cossacks","s_baiser","r_icare","sch_120",
 # trop liés à une histoire précise (Égypte, Chine, Napoléon, Louis XIV…) : réservés aux plans écrits à la main
 "sphinx","s_pyramide","s_temple","s_alexandrie","s_reine","qin","simayi","zhuge2","bianjing","kuni_guan","s_cesar_portrait",
 "sacre","alps","rigaud","conde","banquet","s_madamex","s_perle","a_arnolfini","a_ambassadeurs","nightwatch","school","r_temeraire","temeraire"}
_img=_txt=None
def models():
    global _img,_txt
    if _img is None:
        from sentence_transformers import SentenceTransformer
        _img=SentenceTransformer("clip-ViT-B-32")
    return _img,None
def build():
    from PIL import Image
    img,_=models()
    names=sorted(f for f in os.listdir(RAW) if f.endswith(".jpg") and f[:-4] not in EXCLUDE)
    ims=[Image.open(os.path.join(RAW,n)).convert("RGB") for n in names]
    E=img.encode(ims,batch_size=16,normalize_embeddings=True,show_progress_bar=False)
    np.savez(INDEX,names=np.array(names),emb=E); return len(names)
def load():
    if not os.path.exists(INDEX): build()
    d=np.load(INDEX); return list(d["names"]),d["emb"]
def embed_text(lines):
    global _txt
    if _txt is None:
        from sentence_transformers import SentenceTransformer
        _txt=SentenceTransformer("sentence-transformers/clip-ViT-B-32-multilingual-v1")
    return _txt.encode(lines,normalize_embeddings=True,show_progress_bar=False)
if __name__=="__main__": print(build(),"images indexées")
