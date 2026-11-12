# THINK LIVRE Studio (appli)

Appli web installable (PWA) qui fabrique automatiquement les vidéos au format cinéma.

## Lancer
```bash
cd thinklivre && ./installer.sh                 # modèle de reconnaissance vocale (modele_asr/)
pip install -r app/requirements.txt             # + ffmpeg avec rubberband
cd app && python3 library.py                    # indexe les tableaux de raw/ (une fois, ou après ajout d'images)
uvicorn server:app --host 0.0.0.0 --port 8000
```
Variables utiles : `SHERPA_MODEL` (dossier du modèle), `ENGINE_PYTHON` (python qui lance le moteur).

## Fonctionnement
- `store.py` : données (réglages, comptes ElevenLabs, livres, textes, vidéos) dans `app/data/store.json` (**privé, hors git**).
- `pipeline.py` : voix ElevenLabs (bascule entre comptes) ou MP3 envoyé → synchro → `autoplan.py` (une image par phrase choisie par CLIP
  dans la bibliothèque vérifiée, personnage, couverture aux appels « LIVRE ») → `son_auto.py` → rendu (`moteur/render.py`).
- `library.py` : liste `EXCLUDE` = tableaux interdits en sélection automatique (nudité, violence, trop spécifiques).
- Une vidéo à la fois (file d'attente). Environ 10 min par vidéo sur 4 cœurs.
