"""Vidéo en ligne : téléchargement par yt-dlp (module Python), une seule fois.

La vidéo est enregistrée sous `<dossier>/<id>.mp4` (720p au plus, image et son fusionnés par
ffmpeg), avec à côté `<id>.source.json` : adresse, titre, chaîne, date. Si les deux fichiers
existent déjà, rien n'est retéléchargé et le réseau n'est pas consulté.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

FORMAT = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]/b"


def est_url(texte: str) -> bool:
    return texte.strip().lower().startswith(("http://", "https://"))


def _ffmpeg() -> str | None:
    """Le ffmpeg de l'environnement (Scripts du Python lancé), sinon celui du PATH."""
    for nom in ("ffmpeg.exe", "ffmpeg"):
        chemin = os.path.join(os.path.dirname(sys.executable), nom)
        if os.path.isfile(chemin):
            return chemin
    return shutil.which("ffmpeg")


def _id_sans_reseau(url: str) -> str | None:
    """L'identifiant de la vidéo lu dans l'adresse, sans réseau (None si inconnu)."""
    from yt_dlp.extractor import gen_extractor_classes
    for ie in gen_extractor_classes():
        if ie.ie_key() == "Generic" or not ie.suitable(url):
            continue
        try:
            return ie.get_temp_id(url)
        except Exception:
            return None
    return None


def _source(info: dict, url: str, fichier: str) -> dict:
    date = info.get("upload_date") or ""
    if len(date) == 8:
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return {"url": info.get("webpage_url") or url, "id": info.get("id"),
            "titre": info.get("title"), "chaine": info.get("channel") or info.get("uploader"),
            "date": date or None, "duree_s": info.get("duration"),
            "fichier": os.path.basename(fichier)}


def telecharger(url: str, dossier: str) -> tuple:
    """Renvoie (chemin de la vidéo, description de la source)."""
    try:
        import yt_dlp
    except ImportError:
        raise SystemExit("Adresse en entrée : yt-dlp n'est pas installé "
                         "(pip install -U \"yt-dlp[default]\").")
    os.makedirs(dossier, exist_ok=True)
    ident = _id_sans_reseau(url)
    if ident:
        video = os.path.join(dossier, f"{ident}.mp4")
        meta = os.path.join(dossier, f"{ident}.source.json")
        if os.path.isfile(video) and os.path.isfile(meta):
            with open(meta, encoding="utf-8") as f:
                source = json.load(f)
            print(f"0/4  Vidéo déjà téléchargée : {video}", file=sys.stderr)
            return video, source

    ffmpeg = _ffmpeg()
    if not ffmpeg:
        raise SystemExit("Adresse en entrée : ffmpeg introuvable (il fusionne l'image et le son).")
    options = {
        "format": FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(dossier, "%(id)s.%(ext)s"),
        "ffmpeg_location": ffmpeg,
        "js_runtimes": {"node": {"path": None}},
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": False,
    }
    print(f"0/4  Téléchargement de {url} (720p au plus)…", file=sys.stderr)
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                raise SystemExit("Adresse en entrée : c'est une liste de lecture, donner "
                                 "l'adresse d'une seule vidéo.")
            video = os.path.join(dossier, f"{info['id']}.mp4")
            if os.path.isfile(video):
                print(f"     Déjà présente : {video}", file=sys.stderr)
            else:
                ydl.process_info(info)
    except yt_dlp.utils.DownloadError as erreur:
        raise SystemExit(f"Téléchargement impossible : {erreur}")
    if not os.path.isfile(video):
        raise SystemExit(f"Téléchargement terminé mais fichier introuvable : {video}")
    source = _source(info, url, video)
    with open(os.path.join(dossier, f"{info['id']}.source.json"), "w", encoding="utf-8") as f:
        json.dump(source, f, ensure_ascii=False, indent=2)
    print(f"     Vidéo : {video}", file=sys.stderr)
    return video, source
