"""Fabrication complète d'une vidéo (format cinéma) dans un dossier de travail."""
import os, json, shutil, subprocess, time, urllib.request, sys
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE); MOTEUR=os.path.join(ROOT,"moteur")
SHERPA=os.environ.get("SHERPA_MODEL", os.path.join(ROOT,"modele_asr"))
PY=os.environ.get("ENGINE_PYTHON","python3")
VOICE_FX=("aresample=48000,rubberband=pitch=0.94:tempo=1.03:formant=preserved:pitchq=quality,highpass=f=70,"
 "equalizer=f=120:t=q:w=0.8:g=4,equalizer=f=300:t=q:w=1.0:g=-3,equalizer=f=3200:t=q:w=1.2:g=3,deesser=i=0.4,"
 "acompressor=threshold=-22dB:ratio=3:attack=4:release=90:makeup=3,loudnorm=I=-14:TP=-1.5:LRA=6")
class Fail(Exception): pass
def sh(cmd,cwd):
    r=subprocess.run(cmd,cwd=cwd,shell=isinstance(cmd,str),capture_output=True,text=True)
    if r.returncode: raise Fail((r.stderr or r.stdout)[-800:])
    return r.stdout
def elevenlabs(text, accounts, voice_id, out):
    need=len(text); last=None
    for acc in accounts:
        try:
            rq=urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription",headers={"xi-api-key":acc["key"]})
            s=json.load(urllib.request.urlopen(rq,timeout=30)); left=s["character_limit"]-s["character_count"]
            if left<need: last=f"{acc['nom']} : plus assez de crédits"; continue
            body=json.dumps({"text":text,"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.8,"style":0.2}}).encode()
            rq=urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",data=body,
                headers={"xi-api-key":acc["key"],"Content-Type":"application/json"})
            open(out,"wb").write(urllib.request.urlopen(rq,timeout=300).read()); return acc["nom"]
        except Exception as e: last=f"{acc.get('nom')} : {e}"
    raise Fail("Voix impossible avec ElevenLabs ("+str(last)+")")
def run(job, store, progress):
    """job: dict(id, texte{script,description,titre}, livre{titre,auteur,cover,char}, voix_fichier?)"""
    work=os.path.join(HERE,"data","jobs",job["id"]); os.makedirs(work,exist_ok=True)
    for f in ["render.py","sfxlib.py","align.py","asr.py","mix3.py","build.sh"]: shutil.copy(os.path.join(MOTEUR,f),work)
    shutil.copy(os.path.join(HERE,"son_auto.py"),work)
    for l,t in [("raw",os.path.join(ROOT,"raw")),("img",os.path.join(ROOT,"img")),("fonts",os.path.join(ROOT,"polices")),("sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",SHERPA)]:
        p=os.path.join(work,l)
        if not os.path.exists(p): os.symlink(t,p)
    lines=[l.strip() for l in job["texte"]["script"].strip().split("\n") if l.strip()]
    open(os.path.join(work,"script.txt"),"w").write("\n".join(lines)+"\n")
    progress(5,"Voix")
    if job.get("voix_fichier"): shutil.copy(job["voix_fichier"],os.path.join(work,"voix.mp3"))
    else:
        st=store.settings(); accs=[a for a in st.get("comptes",[]) if a.get("key") and a.get("actif",True)]
        if not accs: raise Fail("Aucun compte ElevenLabs activé (Profil → Comptes ElevenLabs)")
        job["compte_voix"]=elevenlabs(" ".join(lines),accs,st.get("voice_id",""),os.path.join(work,"voix.mp3"))
    sh(["ffmpeg","-y","-loglevel","error","-i","voix.mp3","-af",VOICE_FX,"-ar","48000","voix_fx.wav"],work)
    sh(["ffmpeg","-y","-loglevel","error","-i","voix_fx.wav","-ac","1","-ar","16000","voix16.wav"],work)
    progress(15,"Synchro des sous-titres"); sh([PY,"asr.py"],work); sh([PY,"align.py"],work)
    progress(25,"Choix des images")
    import autoplan; info=autoplan.make(work,{"book":job["livre"],"hook":job.get("hook","")})
    progress(30,"Son")
    # voix seule (demande de l'utilisateur : ni ambiance ni bruitages)
    dur=json.load(open(os.path.join(work,"plan.json")))["duration"]
    sh(["ffmpeg","-y","-loglevel","error","-i","voix_fx.wav","-af",f"apad=whole_dur={dur:.2f},alimiter=limit=0.89:attack=2:release=80,loudnorm=I=-12:TP=-1.0:LRA=8,pan=stereo|c0=c0|c1=c0","-ar","48000","mix_final.wav"],work)
    progress(35,"Montage")
    env=dict(os.environ); p=subprocess.Popen(["bash","build.sh","HQ.mp4"],cwd=work,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env)
    dur=json.load(open(os.path.join(work,"plan.json")))["duration"]; t0=time.time()
    while p.poll() is None:
        time.sleep(5); el=time.time()-t0; progress(min(92,35+int(57*el/(dur*4.2))),"Montage")
    if p.returncode: raise Fail("Montage : "+p.stdout.read()[-600:])
    progress(95,"Finition")
    out=os.path.join(work,"video.mp4")
    sh(["ffmpeg","-y","-loglevel","error","-i","HQ.mp4","-c:v","libx264","-preset","slow","-crf","26","-maxrate","2.5M","-bufsize","5M","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",out],work)
    sh(["ffmpeg","-y","-loglevel","error","-ss","20","-i",out,"-frames:v","1","-vf","scale=480:-1","thumb.jpg"],work)
    for f in ["HQ.mp4","mix.wav","stem_v.wav","stem_b.wav","stem_f.wav","voix16.wav"]:
        try: os.remove(os.path.join(work,f))
        except OSError: pass
    shutil.rmtree(os.path.join(work,"parts"),ignore_errors=True)
    return {"video":out,"thumb":os.path.join(work,"thumb.jpg"),**info}
