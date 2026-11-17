"""Passe 1 : découpage en plans, suivi des visages, mesures image par image.

Quatre briques :
  1. détection des changements de plan (coupes) ;
  2. recherche des visages, sur l'image entière puis par tuiles pour les visages lointains ;
  3. suivi par zoom : chaque visage connu est recadré serré avant d'être analysé ;
  4. pour chaque visage suivi (jusqu'à max_visages par image) : 52 coefficients musculaires
     (blendshapes MediaPipe), orientation de la tête, et quelques empreintes faciales par
     piste pour reconnaître la même personne d'un plan à l'autre (voir identite.py).

Le résultat (`Visages`) garde tous les visages. Deux vues en tirent une `Mesures` à une
seule personne par image : `vue_dominante` (le visage dominant de chaque plan, comme en
0.4) et `vue_personne` (les pistes d'une personne reconnue).
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import sys
import urllib.request
from collections import defaultdict
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

URL_MODELE = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
              "face_landmarker/float16/1/face_landmarker.task")
SEUIL_COUPE = 27.0        # écart moyen HSV entre deux images (même réglage que PySceneDetect)
IOU_MIN = 0.2             # recouvrement minimal pour rattacher un visage à une piste
ZOOM = 1.7                # côté du cadre affiché = 1,7 x la taille du visage
ZOOM_SUIVI = 2.5          # côté du recadrage d'analyse = 2,5 x la taille du visage
TUILE = 600               # côté des tuiles de recherche, en pixels
PERTE = 0.3               # secondes sans le retrouver avant d'abandonner un visage
RECHERCHE = 0.5           # secondes entre deux recherches complètes
# Empreintes faciales : visage assez grand et assez de face, une toutes les 0,5 s par piste
# (puis toutes les 3 s au-delà de 20), et une vignette par piste pour la planche.
EMPREINTE_LARGEUR = 48    # pixels
EMPREINTE_LACET = 30.0    # degrés
EMPREINTE_PAS = 0.5       # secondes
EMPREINTE_PAS_LONG = 3.0  # secondes, au-delà de EMPREINTE_NB empreintes
EMPREINTE_NB = 20
VIGNETTE = 128            # côté des vignettes, en pixels
FORMAT_MESURES = 1        # version du fichier *_mesures.npz ; à changer si son contenu change
# Points du maillage MediaPipe : coins des deux yeux, bout du nez, coins de la bouche.
_OEIL_1, _OEIL_2, _NEZ, _BOUCHE = (33, 133), (362, 263), 1, (61, 291)


@dataclass
class Mesures:
    chemin: str
    fps: float
    largeur: int
    hauteur: int
    debut: float
    t: np.ndarray            # (n,) secondes depuis le début de l'extrait
    coupes: list             # index des images où un nouveau plan commence
    valide: np.ndarray       # (n,) visage suivi présent
    boite: np.ndarray        # (n,4) x0,y0,x1,y1 en pixels
    cadre: np.ndarray        # (n,3) cx,cy,côté du zoom, lissés
    bs: np.ndarray           # (n,52) coefficients musculaires 0..1
    noms_bs: list
    angles: np.ndarray       # (n,3) lacet, tangage, roulis en degrés
    nb_visages: np.ndarray   # (n,) nombre de visages vus dans l'image

    @property
    def n(self) -> int:
        return len(self.t)


@dataclass
class Visages:
    """Tous les visages suivis, image par image (au plus `max_visages` par image)."""
    chemin: str
    fps: float
    largeur: int
    hauteur: int
    debut: float
    coupes: list
    piste: np.ndarray        # (n,K) numéro de piste, -1 si la case est vide
    boite: np.ndarray        # (n,K,4) x0,y0,x1,y1 en pixels
    bs: np.ndarray           # (n,K,52) coefficients musculaires
    angles: np.ndarray       # (n,K,3) lacet, tangage, roulis
    noms_bs: list
    emp_piste: np.ndarray    # (E,) piste de chaque empreinte faciale
    emp_image: np.ndarray    # (E,) image de chaque empreinte
    emp: np.ndarray          # (E,128) empreintes normalisées
    emp_qualite: np.ndarray  # (E,) largeur du visage x cos(lacet)
    vig_piste: np.ndarray    # (V,) piste de chaque vignette (une par piste)
    vig_image: np.ndarray    # (V,) image d'où vient la vignette
    vig: np.ndarray          # (V,VIGNETTE,VIGNETTE,3) RGB

    @property
    def n(self) -> int:
        return self.piste.shape[0]

    @property
    def t(self) -> np.ndarray:
        return np.arange(self.n) / self.fps


@contextlib.contextmanager
def _silence():
    """Masque le journal technique que MediaPipe écrit sur la sortie d'erreur."""
    sys.stderr.flush()
    sauvegarde, nul = os.dup(2), os.open(os.devnull, os.O_WRONLY)
    os.dup2(nul, 2)
    try:
        yield
    finally:
        os.dup2(sauvegarde, 2)
        os.close(nul)
        os.close(sauvegarde)


def dossier_cache() -> str:
    cache = os.path.join(os.path.expanduser("~"), ".cache", "facescope")
    os.makedirs(cache, exist_ok=True)
    return cache


def _sha256(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def modele_controle(url: str, fichier: str, sha256: str, libelle: str) -> str:
    """Modèle téléchargé une fois dans ~/.cache/facescope depuis une adresse fixe, puis
    contrôlé par son empreinte SHA-256 à chaque lancement : un fichier qui ne correspond pas
    est supprimé et rien n'est lancé."""
    cible = os.path.join(dossier_cache(), fichier)
    if not os.path.exists(cible):
        print(f"Téléchargement du modèle {libelle}…", file=sys.stderr)
        partiel = cible + ".partiel"
        try:
            urllib.request.urlretrieve(url, partiel)
        except OSError as erreur:
            raise SystemExit(f"Téléchargement du modèle {libelle} impossible ({erreur}). "
                             f"Adresse : {url}")
        os.replace(partiel, cible)
    if _sha256(cible) != sha256:
        os.remove(cible)
        raise SystemExit(f"Le modèle {libelle} ne correspond pas à l'empreinte SHA-256 "
                         "attendue : fichier supprimé, rien n'a été lancé.")
    return cible


def chemin_modele(chemin: str | None = None) -> str:
    if chemin:
        return chemin
    cible = os.path.join(dossier_cache(), "face_landmarker.task")
    if not os.path.exists(cible):
        print("Téléchargement du modèle de visage (3,7 Mo)…", file=sys.stderr)
        urllib.request.urlretrieve(URL_MODELE, cible)
    return cible


def _iou(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _doublon(a, b) -> bool:
    """Deux boîtes désignent le même visage si l'une recouvre la moitié de la plus petite."""
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    petite = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return petite > 0 and inter / petite > 0.5


def _angles(matrice) -> tuple:
    r = np.asarray(matrice, dtype=float)[:3, :3]
    r = r / np.maximum(np.linalg.norm(r, axis=0, keepdims=True), 1e-9)
    tangage = np.degrees(np.arctan2(r[2, 1], r[2, 2]))
    lacet = np.degrees(np.arctan2(-r[2, 0], np.hypot(r[2, 1], r[2, 2])))
    roulis = np.degrees(np.arctan2(r[1, 0], r[0, 0]))
    return lacet, tangage, roulis


def _lisser(x: np.ndarray, k: int) -> np.ndarray:
    if len(x) < 3 or k < 3:
        return x
    k = min(k, len(x)) | 1
    return np.convolve(np.pad(x, k // 2, mode="edge"), np.ones(k) / k, mode="valid")


def _positions(longueur: int, cote: int) -> list:
    if longueur <= cote:
        return [0]
    nb = math.ceil((longueur - cote) / (cote * 0.67)) + 1
    return [round(k * (longueur - cote) / (nb - 1)) for k in range(nb)]


def _tuiles(largeur: int, hauteur: int) -> list:
    """Zones de recherche qui se recouvrent d'un tiers, pour voir les petits visages."""
    cote = min(TUILE, largeur, hauteur)
    zones = [(x, y, min(cote, largeur), min(cote, hauteur))
             for y in _positions(hauteur, cote) for x in _positions(largeur, cote)]
    return zones if len(zones) > 1 else []


def _cinq_points(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Yeux, nez et coins de la bouche, ordonnés de gauche à droite dans l'image."""
    def centre(indices):
        return [float(np.mean(xs[list(indices)])), float(np.mean(ys[list(indices)]))]
    yeux = sorted([centre(_OEIL_1), centre(_OEIL_2)])
    bouche = sorted([[float(xs[_BOUCHE[0]]), float(ys[_BOUCHE[0]])],
                     [float(xs[_BOUCHE[1]]), float(ys[_BOUCHE[1]])]])
    return np.array(yeux + [[float(xs[_NEZ]), float(ys[_NEZ])]] + bouche, np.float32)


class _Detecteur:
    def __init__(self, modele: str, max_visages: int):
        options = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=modele),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=max_visages,
            min_face_detection_confidence=0.4,
            min_face_presence_confidence=0.4,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        with _silence():
            self.modele = vision.FaceLandmarker.create_from_options(options)
            self.modele.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                        data=np.zeros((64, 64, 3), np.uint8)))
        self.noms = None

    def chercher(self, rgb, zone) -> list:
        """Visages trouvés dans une zone (x, y, largeur, hauteur) : boîte, muscles, angles,
        cinq points (yeux, nez, coins de la bouche)."""
        x0, y0, l, h = zone
        extrait = np.ascontiguousarray(rgb[y0:y0 + h, x0:x0 + l])
        res = self.modele.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=extrait))
        trouves = []
        for k, points in enumerate(res.face_landmarks):
            xs = np.fromiter((p.x for p in points), float) * l + x0
            ys = np.fromiter((p.y for p in points), float) * h + y0
            if self.noms is None:
                self.noms = [c.category_name for c in res.face_blendshapes[k]]
            trouves.append(((xs.min(), ys.min(), xs.max(), ys.max()),
                            np.fromiter((c.score for c in res.face_blendshapes[k]), np.float32),
                            _angles(res.facial_transformation_matrixes[k]),
                            _cinq_points(xs, ys)))
        return trouves

    def fermer(self):
        self.modele.close()


def _vignette(rgb, boite) -> np.ndarray:
    """Visage recadré au carré avec un peu de marge, VIGNETTE x VIGNETTE pixels."""
    cx, cy = (boite[0] + boite[2]) / 2, (boite[1] + boite[3]) / 2
    cote = 1.5 * max(boite[2] - boite[0], boite[3] - boite[1], 1.0)
    e = VIGNETTE / cote
    mat = np.float32([[e, 0, VIGNETTE / 2 - cx * e], [0, e, VIGNETTE / 2 - cy * e]])
    return cv2.warpAffine(rgb, mat, (VIGNETTE, VIGNETTE), flags=cv2.INTER_AREA)


def analyser(chemin: str, modele: str | None = None, max_visages: int = 4,
             debut: float = 0.0, duree: float | None = None) -> Visages:
    from .identite import Empreinteur     # import tardif : identite importe ce module

    cap = cv2.VideoCapture(chemin)
    if not cap.isOpened():
        raise SystemExit(f"Impossible d'ouvrir la vidéo : {chemin}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    largeur = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    hauteur = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    saut = int(round(debut * fps))
    n_max = int(round(duree * fps)) if duree else max(total - saut, 0) or 10 ** 9
    for _ in range(saut):
        if not cap.grab():
            break

    detecteur = _Detecteur(chemin_modele(modele), max_visages)
    empreinteur = Empreinteur()
    entiere, tuiles = (0, 0, largeur, hauteur), _tuiles(largeur, hauteur)
    candidats = []            # par image : [(piste, boîte, muscles, angles, points)]
    coupes = []
    pistes = {}               # piste -> (boîte, dernière image vue)
    prochaine, derniere_coupe, derniere_recherche, prec = 0, -10 ** 9, -10 ** 9, None
    empreintes = []           # (piste, image, vecteur, qualité)
    suivi_emp = {}            # piste -> (dernière image échantillonnée, nombre)
    vignettes = {}            # piste -> (qualité, image, vignette)

    i = 0
    while i < n_max:
        ok, image = cap.read()
        if not ok:
            break
        petit = cv2.cvtColor(cv2.resize(image, (96, 54), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2HSV).astype(np.int16)
        if prec is not None and np.abs(petit - prec).mean() > SEUIL_COUPE \
                and i - derniere_coupe > 0.4 * fps:
            coupes.append(i)
            derniere_coupe = i
            pistes.clear()                        # nouveau plan : on repart de zéro
            derniere_recherche = -10 ** 9
        prec = petit
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        vus = {}

        # Suivi par zoom : chaque visage connu est recadré serré puis analysé.
        for pid, (b, vu) in list(pistes.items()):
            if i - vu > PERTE * fps:
                del pistes[pid]
                continue
            cote = int(min(max((b[2] - b[0]), (b[3] - b[1])) * ZOOM_SUIVI, largeur, hauteur))
            cote = max(cote, min(160, largeur, hauteur))
            x0 = int(min(max((b[0] + b[2]) / 2 - cote / 2, 0), largeur - cote))
            y0 = int(min(max((b[1] + b[3]) / 2 - cote / 2, 0), hauteur - cote))
            meilleur, score = None, IOU_MIN
            for visage in detecteur.chercher(rgb, (x0, y0, cote, cote)):
                s = _iou(visage[0], b)
                if s > score and not any(_doublon(visage[0], v[0]) for v in vus.values()):
                    meilleur, score = visage, s
            if meilleur:
                vus[pid] = meilleur
                pistes[pid] = (meilleur[0], i)

        # Recherche de nouveaux visages : image entière, puis tuiles pour les plus petits.
        complete = i - derniere_recherche >= RECHERCHE * fps
        if complete or (not vus and i % 3 == 0):
            zones = [entiere] + (tuiles if complete else [])
            if complete:
                derniere_recherche = i
            trouves = [v for z in zones for v in detecteur.chercher(rgb, z)]
            trouves.sort(key=lambda v: -(v[0][2] - v[0][0]) * (v[0][3] - v[0][1]))
            for visage in trouves:
                if len(vus) >= max_visages or any(_doublon(visage[0], v[0]) for v in vus.values()):
                    continue
                pid = next((p for p, (b, _) in pistes.items()
                            if p not in vus and _iou(visage[0], b) > IOU_MIN), None)
                if pid is None:
                    pid, prochaine = prochaine, prochaine + 1
                vus[pid] = visage
                pistes[pid] = (visage[0], i)

        # Empreintes faciales et vignettes : visages assez grands et assez de face.
        for pid, (bx, _, ang, points) in vus.items():
            larg, lacet = bx[2] - bx[0], float(ang[0])
            if larg < EMPREINTE_LARGEUR or abs(lacet) > EMPREINTE_LACET:
                continue
            qualite = float(larg * math.cos(math.radians(lacet)))
            if qualite > vignettes.get(pid, (-1.0,))[0]:
                vignettes[pid] = (qualite, i, _vignette(rgb, bx))
            derniere, nb = suivi_emp.get(pid, (-10 ** 9, 0))
            pas = EMPREINTE_PAS if nb < EMPREINTE_NB else EMPREINTE_PAS_LONG
            if i - derniere >= pas * fps:
                vecteur = empreinteur.calculer(empreinteur.aligner(rgb, points))
                empreintes.append((pid, i, vecteur, qualite))
                suivi_emp[pid] = (i, nb + 1)

        candidats.append([(pid, *v) for pid, v in vus.items()])
        i += 1
        if i % 250 == 0:
            print(f"  analyse : {i} images", file=sys.stderr, flush=True)
    cap.release()
    noms_bs = detecteur.noms or []
    detecteur.fermer()

    n = len(candidats)
    if n == 0:
        raise SystemExit("Aucune image lue dans la vidéo.")
    # Une piste perdue reste connue 0,3 s : une image peut compter un visage de plus que
    # max_visages. On garde toutes les cases pour que la vue dominante reste celle de 0.4.
    k_max = max(max(len(c) for c in candidats), 1)
    piste = np.full((n, k_max), -1, np.int32)
    boite = np.full((n, k_max, 4), np.nan)
    bs = np.full((n, k_max, len(noms_bs) or 52), np.nan, np.float32)
    angles = np.full((n, k_max, 3), np.nan)
    for j, liste in enumerate(candidats):
        for k, (pid, bx, coeffs, ang, _) in enumerate(liste):
            piste[j, k], boite[j, k], bs[j, k], angles[j, k] = pid, bx, coeffs, ang
    vig_pistes = sorted(vignettes)
    return Visages(
        chemin=chemin, fps=fps, largeur=largeur, hauteur=hauteur, debut=debut, coupes=coupes,
        piste=piste, boite=boite, bs=bs, angles=angles, noms_bs=noms_bs,
        emp_piste=np.array([e[0] for e in empreintes], np.int32),
        emp_image=np.array([e[1] for e in empreintes], np.int32),
        emp=np.array([e[2] for e in empreintes], np.float32).reshape(-1, 128),
        emp_qualite=np.array([e[3] for e in empreintes], np.float32),
        vig_piste=np.array(vig_pistes, np.int32),
        vig_image=np.array([vignettes[p][1] for p in vig_pistes], np.int32),
        vig=np.array([vignettes[p][2] for p in vig_pistes], np.uint8).reshape(
            -1, VIGNETTE, VIGNETTE, 3))


# --- Vues à une personne par image ------------------------------------------------------

def _cadres(valide, piste, boite, fps) -> np.ndarray:
    """Cadre de zoom stabilisé, piste par piste."""
    n = len(valide)
    cadre = np.full((n, 3), np.nan)
    j = 0
    while j < n:
        if not valide[j]:
            j += 1
            continue
        k = j
        while k < n and valide[k] and piste[k] == piste[j]:
            k += 1
        bx = boite[j:k]
        fenetre = int(0.4 * fps) | 1
        cadre[j:k, 0] = _lisser((bx[:, 0] + bx[:, 2]) / 2, fenetre)
        cadre[j:k, 1] = _lisser((bx[:, 1] + bx[:, 3]) / 2, fenetre)
        cadre[j:k, 2] = _lisser(np.maximum(bx[:, 2] - bx[:, 0], bx[:, 3] - bx[:, 1]) * ZOOM,
                                fenetre * 2 + 1)
        j = k
    return cadre


def _vue(v: Visages, choix: np.ndarray) -> Mesures:
    """Mesures d'une personne : `choix[j]` est la case retenue à l'image j (-1 : aucune)."""
    n = v.n
    valide = choix >= 0
    lignes, cases = np.nonzero(valide)[0], choix[valide]
    boite = np.full((n, 4), np.nan)
    bs = np.full((n, v.bs.shape[2]), np.nan, np.float32)
    angles = np.full((n, 3), np.nan)
    piste = np.full(n, -1)
    boite[lignes], bs[lignes] = v.boite[lignes, cases], v.bs[lignes, cases]
    angles[lignes], piste[lignes] = v.angles[lignes, cases], v.piste[lignes, cases]
    return Mesures(chemin=v.chemin, fps=v.fps, largeur=v.largeur, hauteur=v.hauteur,
                   debut=v.debut, t=np.arange(n) / v.fps, coupes=v.coupes, valide=valide,
                   boite=boite, cadre=_cadres(valide, piste, boite, v.fps), bs=bs,
                   noms_bs=v.noms_bs, angles=angles, nb_visages=(v.piste >= 0).sum(axis=1))


def vue_dominante(v: Visages) -> Mesures:
    """Le visage dominant de chaque plan (plus grande surface cumulée), comme en 0.4."""
    n = v.n
    choix = np.full(n, -1)
    bornes = [0] + list(v.coupes) + [n]
    for a, b in zip(bornes[:-1], bornes[1:]):
        surface, presence = defaultdict(float), defaultdict(int)
        for j in range(a, b):
            for k in range(v.piste.shape[1]):
                pid = int(v.piste[j, k])
                if pid < 0:
                    continue
                bx = v.boite[j, k]
                surface[pid] += (bx[2] - bx[0]) * (bx[3] - bx[1])
                presence[pid] += 1
        if not surface:
            continue
        sujet = max(surface, key=surface.get)
        if presence[sujet] < 0.4 * v.fps:
            continue
        for j in range(a, b):
            for k in range(v.piste.shape[1]):
                if v.piste[j, k] == sujet:
                    choix[j] = k
    return _vue(v, choix)


def vue_personne(v: Visages, pistes) -> Mesures:
    """Les images où l'une des pistes de la personne est présente (le plus grand visage si
    deux de ses pistes se recouvrent un court instant)."""
    dans = np.isin(v.piste, np.asarray(sorted(pistes), dtype=np.int32))
    surfaces = np.where(dans, (v.boite[..., 2] - v.boite[..., 0])
                        * (v.boite[..., 3] - v.boite[..., 1]), -1.0)
    choix = np.where(dans.any(axis=1), np.argmax(surfaces, axis=1), -1)
    return _vue(v, choix)


# --- Cache des mesures ------------------------------------------------------------------

def cle_cache(video: str, debut: float, duree: float | None, max_visages: int,
              modele: str | None) -> dict:
    etat = os.stat(video)
    return {"format": FORMAT_MESURES, "video": os.path.basename(video), "taille": etat.st_size,
            "date": int(etat.st_mtime), "debut": round(float(debut), 3),
            "duree": None if duree is None else round(float(duree), 3),
            "max_visages": int(max_visages), "modele": os.path.basename(modele) if modele
            else "face_landmarker.task"}


def enregistrer(v: Visages, chemin: str, cle: dict) -> None:
    """Écrit les mesures dans un fichier .npz (écrit à côté puis renommé)."""
    provisoire = chemin + ".partiel.npz"
    np.savez_compressed(
        provisoire, cle=np.array(json.dumps(cle, sort_keys=True)), fps=np.array(v.fps),
        largeur=np.array(v.largeur), hauteur=np.array(v.hauteur), debut=np.array(v.debut),
        coupes=np.array(v.coupes, np.int64), piste=v.piste, boite=v.boite, bs=v.bs,
        angles=v.angles, noms_bs=np.array(v.noms_bs, dtype=str), emp_piste=v.emp_piste,
        emp_image=v.emp_image, emp=v.emp, emp_qualite=v.emp_qualite, vig_piste=v.vig_piste,
        vig_image=v.vig_image, vig=v.vig)
    os.replace(provisoire, chemin)


def charger(chemin: str, cle: dict, video: str) -> Visages | None:
    """Relit les mesures si le fichier existe et correspond à la même vidéo, au même extrait
    et au même format ; sinon None."""
    if not os.path.exists(chemin):
        return None
    try:
        with np.load(chemin, allow_pickle=False) as f:
            if json.loads(str(f["cle"])) != json.loads(json.dumps(cle, sort_keys=True)):
                return None
            return Visages(
                chemin=video, fps=float(f["fps"]), largeur=int(f["largeur"]),
                hauteur=int(f["hauteur"]), debut=float(f["debut"]),
                coupes=[int(c) for c in f["coupes"]], piste=f["piste"], boite=f["boite"],
                bs=f["bs"], angles=f["angles"], noms_bs=[str(x) for x in f["noms_bs"]],
                emp_piste=f["emp_piste"], emp_image=f["emp_image"], emp=f["emp"],
                emp_qualite=f["emp_qualite"], vig_piste=f["vig_piste"],
                vig_image=f["vig_image"], vig=f["vig"])
    except (OSError, ValueError, KeyError) as erreur:
        print(f"  (cache des mesures illisible, analyse refaite : {erreur})", file=sys.stderr)
        return None
