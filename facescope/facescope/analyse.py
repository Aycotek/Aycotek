"""Passe 1 : découpage en plans, suivi du visage, mesures image par image.

Quatre briques :
  1. détection des changements de plan (coupes) ;
  2. recherche des visages, sur l'image entière puis par tuiles pour les visages lointains ;
  3. suivi par zoom : chaque visage connu est recadré serré avant d'être analysé ;
  4. pour le visage dominant de chaque plan : 52 coefficients musculaires
     (blendshapes MediaPipe), orientation de la tête et cadre de zoom stabilisé.
"""
from __future__ import annotations

import contextlib
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


def chemin_modele(chemin: str | None = None) -> str:
    if chemin:
        return chemin
    cache = os.path.join(os.path.expanduser("~"), ".cache", "facescope")
    os.makedirs(cache, exist_ok=True)
    cible = os.path.join(cache, "face_landmarker.task")
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
        """Visages trouvés dans une zone (x, y, largeur, hauteur) : boîte, muscles, angles."""
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
                            _angles(res.facial_transformation_matrixes[k])))
        return trouves

    def fermer(self):
        self.modele.close()


def analyser(chemin: str, modele: str | None = None, max_visages: int = 4,
             debut: float = 0.0, duree: float | None = None) -> Mesures:
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
    entiere, tuiles = (0, 0, largeur, hauteur), _tuiles(largeur, hauteur)
    candidats = []            # par image : [(piste, boîte, muscles, angles)]
    coupes = []
    pistes = {}               # piste -> (boîte, dernière image vue)
    prochaine, derniere_coupe, derniere_recherche, prec = 0, -10 ** 9, -10 ** 9, None

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
    valide = np.zeros(n, bool)
    boite = np.full((n, 4), np.nan)
    bs = np.full((n, len(noms_bs) or 52), np.nan, np.float32)
    angles = np.full((n, 3), np.nan)
    piste = np.full(n, -1)

    # Dans chaque plan, on garde le visage dominant (plus grande surface cumulée).
    bornes = [0] + coupes + [n]
    for a, b in zip(bornes[:-1], bornes[1:]):
        surface, presence = defaultdict(float), defaultdict(int)
        for j in range(a, b):
            for pid, bx, _, _ in candidats[j]:
                surface[pid] += (bx[2] - bx[0]) * (bx[3] - bx[1])
                presence[pid] += 1
        if not surface:
            continue
        sujet = max(surface, key=surface.get)
        if presence[sujet] < 0.4 * fps:
            continue
        for j in range(a, b):
            for pid, bx, coeffs, ang in candidats[j]:
                if pid == sujet:
                    valide[j], boite[j], bs[j], angles[j], piste[j] = True, bx, coeffs, ang, pid

    # Cadre de zoom stabilisé, piste par piste.
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

    return Mesures(chemin=chemin, fps=fps, largeur=largeur, hauteur=hauteur, debut=debut,
                   t=np.arange(n) / fps, coupes=coupes, valide=valide, boite=boite,
                   cadre=cadre, bs=bs, noms_bs=noms_bs, angles=angles,
                   nb_visages=np.array([len(c) for c in candidats]))
