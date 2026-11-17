"""Qui est qui : regrouper les pistes de visage en personnes, d'un plan à l'autre.

1. Pendant le suivi (analyse.py), chaque piste reçoit des empreintes faciales : visage d'au
   moins 48 pixels, tourné de moins de 30°, une toutes les 0,5 s. Modèle SFace d'OpenCV Zoo
   (licence Apache 2.0), lancé avec onnxruntime sur le visage aligné par cinq points (yeux,
   nez, coins de la bouche). Une empreinte est un vecteur de 128 nombres ; deux visages de
   la même personne donnent des vecteurs proches (similarité cosinus élevée).
2. Pistes coupées (0.6) : le suivi rattache un visage à la piste ouverte au même endroit ;
   quand deux plans cadrés pareil s'enchaînent sans que la coupe soit vue (même décor), une
   piste peut passer d'une personne à une autre. Une piste est coupée là où ses empreintes
   changent de personne : similarité moyenne entre les FENETRE_CHANGEMENT empreintes avant
   et après sous SEUIL_CHANGEMENT (minimum local), à l'image où le cadre du visage saute le
   plus entre les deux empreintes. Deux morceaux de la même personne se retrouvent au
   regroupement.
3. Regroupement hiérarchique, lien moyen, sur la distance cosinus (1 - similarité) entre
   pistes : on réunit les deux groupes les plus proches tant que leur distance moyenne reste
   sous SEUIL_FUSION. Deux pistes vues en même temps (au moins CHEVAUCHEMENT images) ne sont
   jamais réunies : ce sont deux personnes.
4. Réaffectation (0.6) : une piste nettement plus proche d'une autre personne que de la
   sienne (MARGE_REAFFECTATION d'avance, et au moins 1 - SEUIL_FUSION de similarité) y est
   déplacée, sauf si elle est vue en même temps qu'une piste de cette personne.
5. Les groupes sont classés par temps à l'image. Un groupe vu moins de TEMPS_MIN_PERSONNE
   secondes, ou une piste sans empreinte (visage toujours de profil ou trop petit), va dans
   « autres ». Dans un débat, les personnes qui ne sont ni nommées ni ne parlent vraiment
   forment le « public » (personnes.py) ; les lettres A, B… ne sont données qu'aux
   participants.
6. Noms : l'outil ne reconnaît personne de lui-même. Il ne connaît que les lettres, les noms
   donnés par l'utilisateur (--noms) et ses photos de référence (--visages).
"""
from __future__ import annotations

import dataclasses
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .analyse import Visages, _Detecteur, _tuiles, _vignette, chemin_modele, modele_controle

# Modèle d'empreinte faciale : SFace (MobileFaceNet entraîné avec la perte SFace), dépôt
# officiel OpenCV Zoo, fichier figé à un commit, contrôlé par son empreinte SHA-256.
URL_EMPREINTE = ("https://github.com/opencv/opencv_zoo/raw/"
                 "ba91a3b91d00d76e86540d4013f944bd6b514e39/models/face_recognition_sface/"
                 "face_recognition_sface_2021dec.onnx")
SHA256_EMPREINTE = "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"
FICHIER_EMPREINTE = "face_recognition_sface_2021dec.onnx"
MODELE_EMPREINTE = ("SFace 2021dec, OpenCV Zoo (github.com/opencv/opencv_zoo), "
                    "licence Apache 2.0, 38,7 Mo")
# Positions des cinq points dans le visage aligné de 112 x 112 attendu par SFace
# (gabarit d'OpenCV, FaceRecognizerSF::alignCrop).
GABARIT = np.float32([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                      [41.5493, 92.3655], [70.7299, 92.2041]])

SEUIL_FUSION = 0.6          # distance cosinus moyenne maximale pour réunir deux groupes
CHEVAUCHEMENT = 3           # images vues ensemble à partir desquelles deux pistes s'excluent
TEMPS_MIN_PERSONNE = 4.0    # secondes à l'image pour devenir une personne (sinon « autres »)
SEUIL_PHOTO = 0.363         # similarité cosinus minimale photo / personne (seuil d'OpenCV)
MARGE_PHOTO = 0.05          # avance minimale sur la deuxième personne la plus proche
# Changement de personne dans une piste. Sur le débat Maréchal-Villepin (8 353 paires
# d'empreintes consécutives), 94 % des paires dépassent 0,7 ; les changements vus (plans du
# présentateur puis de Villepin dans la même piste) donnent -0,05 à 0,15. 0,25 sur une
# moyenne de 3 x 3 empreintes laisse passer une empreinte isolée floue ou tournée.
SEUIL_CHANGEMENT = 0.25
FENETRE_CHANGEMENT = 3      # empreintes de chaque côté
MARGE_REAFFECTATION = 0.1   # avance de similarité pour déplacer une piste vers une autre personne
EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def modele_empreinte() -> str:
    """Chemin du modèle SFace, téléchargé au premier lancement et toujours contrôlé."""
    return modele_controle(URL_EMPREINTE, FICHIER_EMPREINTE, SHA256_EMPREINTE,
                           "d'empreinte faciale (SFace, 38,7 Mo)")


class Empreinteur:
    """Empreinte faciale SFace (128 nombres, normalisée) d'un visage aligné sur 5 points."""

    def __init__(self):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.log_severity_level = 3
        self.session = ort.InferenceSession(modele_empreinte(), options,
                                            providers=["CPUExecutionProvider"])
        self.entree = self.session.get_inputs()[0].name

    @staticmethod
    def aligner(rgb: np.ndarray, points: np.ndarray) -> np.ndarray:
        mat, _ = cv2.estimateAffinePartial2D(np.asarray(points, np.float32), GABARIT,
                                             method=cv2.LMEDS)
        if mat is None:
            mat = cv2.getAffineTransform(np.asarray(points[:3], np.float32), GABARIT[:3])
        return cv2.warpAffine(rgb, mat, (112, 112))

    def calculer(self, visage: np.ndarray) -> np.ndarray:
        """Le modèle attend un visage RGB de 112 x 112, valeurs 0..255, sans normalisation."""
        x = visage.astype(np.float32).transpose(2, 0, 1)[None]
        v = self.session.run(None, {self.entree: x})[0][0].astype(np.float32)
        return v / max(float(np.linalg.norm(v)), 1e-9)


def _lettre(k: int) -> str:
    return chr(ord("A") + k) if k < 26 else f"P{k + 1}"


def separer_pistes(v: Visages) -> tuple:
    """Coupe les pistes dont les empreintes changent de personne en cours de route.

    Renvoie une copie de `v` (numéros de pistes, empreintes et vignettes mis à jour ; les
    mesures ne changent pas) et la liste des coupures. Un morceau sans vignette en reçoit une,
    prise dans la vidéo à sa meilleure empreinte."""
    piste, emp_piste = v.piste.copy(), v.emp_piste.copy()
    vig_piste = v.vig_piste.copy()
    suivant = int(max(v.piste.max(initial=-1), v.emp_piste.max(initial=-1))) + 1
    coupures, nouveaux = [], []
    for q in np.unique(v.emp_piste):
        idx = np.nonzero(v.emp_piste == q)[0]
        if idx.size < 2:
            continue
        idx = idx[np.argsort(v.emp_image[idx], kind="stable")]
        e = v.emp[idx].astype(float)
        f = FENETRE_CHANGEMENT
        croise = np.array([np.inf] + [float((e[max(0, k - f):k] @ e[k:k + f].T).mean())
                                      for k in range(1, len(idx))] + [np.inf])
        points = [k for k in range(1, len(idx)) if croise[k] < SEUIL_CHANGEMENT
                  and croise[k] <= croise[k - 1] and croise[k] <= croise[k + 1]]
        if not points:
            continue
        lignes, cases = np.nonzero(v.piste == q)
        ordre = np.argsort(lignes, kind="stable")
        lignes, cases = lignes[ordre], cases[ordre]
        b = v.boite[lignes, cases].astype(float)
        cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
        larg = np.maximum(b[:, 2] - b[:, 0], 1.0)
        saut = np.zeros(len(lignes))
        saut[1:] = (np.hypot(np.diff(cx), np.diff(cy)) + np.abs(np.diff(larg))) / larg[:-1]
        for k in points:
            a, z = v.emp_image[idx[k - 1]], v.emp_image[idx[k]]
            entre = np.nonzero((lignes > a) & (lignes <= z))[0]
            borne = int(lignes[entre[np.argmax(saut[entre])]]) if entre.size else int(z)
            dans = lignes >= borne
            piste[lignes[dans], cases[dans]] = suivant
            emp_piste[(v.emp_piste == q) & (v.emp_image >= borne)] = suivant
            vig_piste[(v.vig_piste == q) & (v.vig_image >= borne)] = suivant
            coupures.append({"piste": int(q), "image": borne, "nouvelle_piste": suivant,
                             "similarite": round(float(croise[k]), 3)})
            nouveaux.append(suivant)
            suivant += 1
    w = dataclasses.replace(v, piste=piste, emp_piste=emp_piste, vig_piste=vig_piste)
    # Vignettes des morceaux qui n'en ont pas (y compris le début d'une piste coupée).
    touchees = {c["piste"] for c in coupures} | set(nouveaux)
    sans = [p for p in sorted(touchees) if not (vig_piste == p).any() and (emp_piste == p).any()]
    if sans:
        ajout = _vignettes_video(w, sans)
        if ajout:
            w.vig_piste = np.concatenate([vig_piste, np.array([p for p, _, _ in ajout],
                                                              vig_piste.dtype)])
            w.vig_image = np.concatenate([v.vig_image, np.array([i for _, i, _ in ajout],
                                                                v.vig_image.dtype)])
            w.vig = np.concatenate([v.vig, np.stack([x for _, _, x in ajout]).astype(v.vig.dtype)])
    return w, coupures


def _vignettes_video(v: Visages, pistes: list) -> list:
    """Vignette de chaque piste à l'image de sa meilleure empreinte, relue dans la vidéo."""
    cap = cv2.VideoCapture(v.chemin)
    if not cap.isOpened():
        return []
    sortie = []
    try:
        for p in pistes:
            k = np.nonzero(v.emp_piste == p)[0]
            image = int(v.emp_image[k[np.argmax(v.emp_qualite[k])]])
            case = np.nonzero(v.piste[image] == p)[0]
            if not case.size:
                continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(v.debut * v.fps)) + image)
            lu, bgr = cap.read()
            if not lu:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            sortie.append((p, image, _vignette(rgb, v.boite[image, case[0]])))
    finally:
        cap.release()
    return sortie


def regrouper(v: Visages, seuil: float = SEUIL_FUSION,
              temps_min: float = TEMPS_MIN_PERSONNE) -> dict:
    """Pistes -> personnes. Renvoie {personnes, autres, piste_personne, details}."""
    lignes, cases = np.nonzero(v.piste >= 0)
    ids = v.piste[lignes, cases]
    pistes, premier, images = np.unique(ids, return_index=True, return_counts=True)
    images = dict(zip(pistes.tolist(), images.tolist()))
    premiere = dict(zip(pistes.tolist(), lignes[premier].tolist()))

    # Pistes vues en même temps : elles désignent deux personnes différentes.
    conflits = {}
    nb_cases = v.piste.shape[1]
    for k1 in range(nb_cases):
        for k2 in range(k1 + 1, nb_cases):
            a, b = v.piste[:, k1], v.piste[:, k2]
            ensemble = (a >= 0) & (b >= 0)
            if not ensemble.any():
                continue
            paires = np.stack([np.minimum(a[ensemble], b[ensemble]),
                               np.maximum(a[ensemble], b[ensemble])], axis=1)
            for (x, y), c in zip(*np.unique(paires, axis=0, return_counts=True)):
                conflits[(int(x), int(y))] = conflits.get((int(x), int(y)), 0) + int(c)

    # Une moyenne d'empreintes par piste ; le lien moyen entre deux groupes est le produit
    # scalaire de leurs moyennes pondérées (moyenne des similarités deux à deux).
    avec = [p for p in pistes.tolist() if (v.emp_piste == p).any()]
    index = {p: i for i, p in enumerate(avec)}
    nb = len(avec)
    moyennes = np.zeros((nb, v.emp.shape[1] if v.emp.size else 128))
    poids = np.zeros(nb)
    for p, i in index.items():
        choix = v.emp_piste == p
        moyennes[i] = v.emp[choix].astype(float).mean(axis=0)
        poids[i] = choix.sum()
    interdit = np.zeros((nb, nb), bool)
    for (x, y), c in conflits.items():
        if c >= CHEVAUCHEMENT and x in index and y in index:
            interdit[index[x], index[y]] = interdit[index[y], index[x]] = True
    conflit_piste = interdit.copy()
    moy_piste, poids_piste = moyennes.copy(), poids.copy()
    groupes = [[p] for p in avec]
    actif = np.ones(nb, bool)
    fusions, plus_proche = [], None
    while actif.sum() > 1:
        d = 1.0 - moyennes @ moyennes.T
        d[~actif, :] = np.inf
        d[:, ~actif] = np.inf
        d[interdit] = np.inf
        np.fill_diagonal(d, np.inf)
        i, j = np.unravel_index(int(np.argmin(d)), d.shape)
        if not np.isfinite(d[i, j]) or d[i, j] > seuil:
            plus_proche = None if not np.isfinite(d[i, j]) else round(float(d[i, j]), 3)
            break
        fusions.append(round(float(d[i, j]), 3))
        moyennes[i] = (poids[i] * moyennes[i] + poids[j] * moyennes[j]) / (poids[i] + poids[j])
        poids[i] += poids[j]
        interdit[i] |= interdit[j]
        interdit[:, i] |= interdit[:, j]
        actif[j] = False
        groupes[i] += groupes[j]

    # Réaffectation : chaque piste des groupes assez longs pour faire une personne va vers
    # la personne dont elle est nettement la plus proche (sa propre personne comptée sans
    # elle), si elle n'est jamais vue en même temps qu'une piste de celle-ci.
    grands = [i for i in (np.nonzero(actif)[0] if nb else [])
              if sum(images[p] for p in groupes[i]) >= temps_min * v.fps]
    somme = {i: sum(poids_piste[index[p]] * moy_piste[index[p]] for p in groupes[i])
             for i in grands}
    total_poids = {i: sum(poids_piste[index[p]] for p in groupes[i]) for i in grands}
    membres_idx = {i: np.array([index[p] for p in groupes[i]]) for i in grands}
    deplacements = []
    for i in grands:
        for p in groupes[i]:
            k, w = index[p], poids_piste[index[p]]
            if total_poids[i] - w <= 0:
                continue
            propre = float(moy_piste[k] @ ((somme[i] - w * moy_piste[k]) / (total_poids[i] - w)))
            meilleur, sim = None, propre + MARGE_REAFFECTATION
            for j in grands:
                if j == i or conflit_piste[k, membres_idx[j]].any():
                    continue
                s = float(moy_piste[k] @ (somme[j] / total_poids[j]))
                if s >= sim and s >= 1.0 - seuil:
                    meilleur, sim = j, s
            if meilleur is not None:
                deplacements.append((p, i, meilleur, round(propre, 3), round(sim, 3)))
    faits = []
    for p, i, j, propre, sim in deplacements:
        if conflit_piste[index[p], [index[x] for x in groupes[j]]].any():
            continue                       # une autre piste déplacée vers j la recouvre
        groupes[i].remove(p)
        groupes[j].append(p)
        faits.append((p, i, j, propre, sim))

    candidats = []
    for i in np.nonzero(actif)[0] if nb else []:
        if not groupes[i]:
            continue
        total = sum(images[p] for p in groupes[i])
        candidats.append((total, i))
    candidats.sort(key=lambda c: (-c[0], min(premiere[p] for p in groupes[c[1]])))
    personnes, piste_personne, lettre_groupe = [], {p: None for p in images}, {}
    for total, i in candidats:
        if total < temps_min * v.fps:
            continue
        ident = _lettre(len(personnes))
        lettre_groupe[i] = ident
        somme_i = sum(poids_piste[index[p]] * moy_piste[index[p]] for p in groupes[i])
        empreinte = somme_i / max(float(np.linalg.norm(somme_i)), 1e-9)
        membres = sorted(groupes[i], key=lambda p: premiere[p])
        personnes.append({"id": ident, "pistes": membres, "images": int(total),
                          "temps_s": round(total / v.fps, 1), "empreinte": empreinte,
                          "nb_empreintes": int(sum(poids_piste[index[p]] for p in groupes[i])),
                          "nom": None, "source_nom": None})
        for p in membres:
            piste_personne[p] = ident
    autres = sorted((p for p, x in piste_personne.items() if x is None), key=lambda p: premiere[p])
    similarites = {}
    for a in range(len(personnes)):
        for b in range(a + 1, len(personnes)):
            similarites[f"{personnes[a]['id']}-{personnes[b]['id']}"] = round(
                float(personnes[a]["empreinte"] @ personnes[b]["empreinte"]), 3)
    return {
        "personnes": personnes,
        "autres": {"pistes": autres, "images": int(sum(images[p] for p in autres)),
                   "temps_s": round(sum(images[p] for p in autres) / v.fps, 1),
                   "sans_empreinte": int(sum(p not in index for p in autres))},
        "piste_personne": piste_personne,
        "premiere": premiere,
        "details": {"pistes": len(images), "pistes_avec_empreinte": nb,
                    "empreintes": int(v.emp_piste.size), "fusions": len(fusions),
                    "distance_de_fusion_max": max(fusions) if fusions else None,
                    "plus_proche_non_fusionne": plus_proche,
                    "reaffectations": [
                        {"piste": int(p), "apparition": round(v.debut + premiere[p] / v.fps, 2),
                         "de": lettre_groupe.get(i), "vers": lettre_groupe.get(j),
                         "similarite_a_sa_personne": propre, "similarite_a_la_nouvelle": sim}
                        for p, i, j, propre, sim in faits],
                    "similarite_entre_personnes": similarites},
    }


def lire_noms(texte: str | None) -> dict:
    """« A=Marion Maréchal,B=Dominique de Villepin » -> {"A": "Marion Maréchal", …}."""
    noms = {}
    for morceau in (texte or "").replace(";", ",").split(","):
        if "=" not in morceau:
            if morceau.strip():
                raise SystemExit(f"--noms : « {morceau.strip()} » n'a pas la forme LETTRE=Nom.")
            continue
        lettre, nom = morceau.split("=", 1)
        if lettre.strip() and nom.strip():
            noms[lettre.strip().upper()] = nom.strip()
    return noms


def _lire_image(chemin: str):
    """cv2.imread ne lit pas les chemins accentués sous Windows : on passe par numpy."""
    donnees = np.fromfile(chemin, np.uint8)
    image = cv2.imdecode(donnees, cv2.IMREAD_COLOR) if donnees.size else None
    return None if image is None else cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def empreintes_photos(dossier: str, modele: str | None = None) -> list:
    """Une empreinte par photo de référence (le plus grand visage de la photo)."""
    fichiers = sorted(f for f in os.listdir(dossier) if f.lower().endswith(EXTENSIONS))
    if not fichiers:
        return []
    detecteur, empreinteur, sortie = _Detecteur(chemin_modele(modele), 4), Empreinteur(), []
    for f in fichiers:
        rgb = _lire_image(os.path.join(dossier, f))
        nom = os.path.splitext(f)[0].strip()
        if rgb is None:
            sortie.append({"photo": f, "nom": nom, "empreinte": None, "erreur": "illisible"})
            continue
        h, l = rgb.shape[:2]
        visages = [x for z in [(0, 0, l, h)] + _tuiles(l, h) for x in detecteur.chercher(rgb, z)]
        if not visages:
            sortie.append({"photo": f, "nom": nom, "empreinte": None,
                           "erreur": "aucun visage trouvé"})
            continue
        bx, _, _, points = max(visages, key=lambda x: (x[0][2] - x[0][0]) * (x[0][3] - x[0][1]))
        sortie.append({"photo": f, "nom": nom, "erreur": None,
                       "empreinte": empreinteur.calculer(empreinteur.aligner(rgb, points))})
    detecteur.fermer()
    return sortie


def nommer(ident: dict, noms: dict, photos: list) -> list:
    """Photos puis --noms (voir nommer_photos et nommer_lettres)."""
    return nommer_photos(ident, photos) + nommer_lettres(ident, noms)


def nommer_lettres(ident: dict, noms: dict) -> list:
    """--noms : la lettre de la planche (participants seulement) reçoit le nom donné ; il
    l'emporte sur une photo."""
    par_id = {p["id"]: p for p in ident["personnes"]}
    compte_rendu = []
    for lettre, nom in noms.items():
        if lettre in par_id:
            par_id[lettre]["nom"], par_id[lettre]["source_nom"] = nom, "--noms"
            compte_rendu.append({"noms": f"{lettre}={nom}", "retenue": True})
        else:
            compte_rendu.append({"noms": f"{lettre}={nom}", "retenue": False,
                                 "raison": f"aucune personne {lettre} dans cet extrait"})
    return compte_rendu


def separer_public(ident: dict, participants: set) -> dict:
    """Garde comme personnes les seuls participants, relettrés A, B… par temps à l'image ;
    les autres personnes reconnues forment le public (ni lettre, ni analyse, ni parole).
    Renvoie {ancienne lettre: nouvelle lettre} des participants."""
    anciennes = ident["personnes"]
    garde = [p for p in anciennes if p["id"] in participants]
    public = [p for p in anciennes if p["id"] not in participants]
    lettres = {p["id"]: _lettre(k) for k, p in enumerate(garde)}
    for p in garde:
        p["id"] = lettres[p["id"]]
    for p in public:
        p["id"] = None
    ident["personnes"] = garde
    ident["public"] = {"personnes": public, "pistes": [q for p in public for q in p["pistes"]],
                       "temps_s": round(sum(p["temps_s"] for p in public), 1)}
    ident["piste_personne"] = {q: lettres.get(x) for q, x in ident["piste_personne"].items()}
    d = ident["details"]
    d["similarite_entre_personnes"] = {
        f"{a['id']}-{b['id']}": round(float(a["empreinte"] @ b["empreinte"]), 3)
        for k, a in enumerate(garde) for b in garde[k + 1:]}
    for r in d.get("reaffectations", []):
        r["de"] = lettres.get(r["de"], "public" if r["de"] else None)
        r["vers"] = lettres.get(r["vers"], "public" if r["vers"] else None)
    return lettres


def nommer_photos(ident: dict, photos: list) -> list:
    """Donne leur nom aux personnes par les photos : la personne la plus proche, au-dessus de
    SEUIL_PHOTO et avec MARGE_PHOTO d'avance. Renvoie le compte rendu des photos."""
    personnes = ident["personnes"]
    compte_rendu = []
    paires = []
    for k, ph in enumerate(photos):
        if ph["empreinte"] is None:
            compte_rendu.append({"photo": ph["photo"], "nom": ph["nom"], "personne": None,
                                 "similarite": None, "retenue": False, "raison": ph["erreur"]})
            continue
        sims = sorted(((float(ph["empreinte"] @ p["empreinte"]), p["id"]) for p in personnes),
                      reverse=True)
        ph["sims"] = sims
        if sims:
            paires.append((sims[0][0], k, sims[0][1]))
    pris, places = set(), set()
    par_id = {p["id"]: p for p in personnes}
    for sim, k, pid in sorted(paires, reverse=True):
        ph = photos[k]
        second = ph["sims"][1][0] if len(ph["sims"]) > 1 else -1.0
        raison = None
        if sim < SEUIL_PHOTO:
            raison = f"similarité {sim:.2f} sous le seuil {SEUIL_PHOTO}"
        elif sim - second < MARGE_PHOTO:
            raison = "trop proche de deux personnes"
        elif pid in pris:
            raison = "cette personne a déjà reçu le nom d'une photo plus proche"
        if raison is None and k not in places:
            par_id[pid]["nom"], par_id[pid]["source_nom"] = ph["nom"], f"photo {ph['photo']}"
            pris.add(pid)
            places.add(k)
        # « _ref » : la personne elle-même, dont la lettre peut changer (separer_public).
        compte_rendu.append({"photo": ph["photo"], "nom": ph["nom"], "personne": pid,
                             "_ref": par_id[pid], "similarite": round(sim, 3),
                             "retenue": raison is None, "raison": raison})
    return compte_rendu


def finaliser_compte_rendu(compte_rendu: list) -> list:
    """Lettres définitives dans le compte rendu des photos (« public » hors participants)."""
    for x in compte_rendu:
        if "_ref" in x:
            x["personne"] = x.pop("_ref")["id"] or "public"
    return compte_rendu


def etiquette(personne: dict) -> str:
    """Nom donné par l'utilisateur, sinon la lettre."""
    return personne["nom"] or personne["id"]


def _duree(secondes: float) -> str:
    secondes = int(round(secondes))
    return f"{secondes} s" if secondes < 60 else f"{secondes // 60} min {secondes % 60:02d} s"


def _tenir(d, texte: str, fonte, largeur: float) -> str:
    """Le texte, raccourci avec « … » s'il dépasse la largeur."""
    while len(texte) > 1 and d.textlength(texte, font=fonte) > largeur:
        texte = texte[:-2].rstrip() + "…"
    return texte


def planche(v: Visages, ident: dict, chemin: str, titre: str, parole: dict) -> None:
    """Une ligne par personne (participant) : vignette, lettre, nom, temps à l'image et de
    parole, puis une vignette par piste (pour vérifier le regroupement) ; une ligne pour le
    public (une vignette par personne du public) ; une ligne pour les autres visages."""
    from .rendu import AVERTISSEMENT, DISCRET, FOND, PANNEAU, TEXTE, TRAIT, VERT, police, tc
    vig = {int(p): k for k, p in enumerate(v.vig_piste)}
    public = ident.get("public") or {"personnes": []}
    lignes = ident["personnes"] + ([{"public": True}] if public["personnes"] else []) \
        + ([{"autres": True}] if ident["autres"]["pistes"] else [])
    largeur, haut_ligne, petit = 1280, 214, 96
    img = Image.new("RGB", (largeur, 70 + haut_ligne * max(len(lignes), 1) + 96), FOND)
    d = ImageDraw.Draw(img)
    d.text((24, 18), "FACESCOPE · PERSONNES", font=police(28, True), fill=TEXTE)
    d.text((24 + d.textlength("FACESCOPE · PERSONNES   ", font=police(28, True)), 26),
           titre, font=police(18), fill=DISCRET)

    def imagette(piste, x, y, cote):
        if piste in vig:
            vignette = Image.fromarray(v.vig[vig[piste]]).resize((cote, cote))
            img.paste(vignette, (x, y))
        else:
            d.rectangle([x, y, x + cote, y + cote], fill=PANNEAU)
            d.text((x + cote / 2, y + cote / 2), "de profil", font=police(13), fill=DISCRET,
                   anchor="mm")
        d.rectangle([x, y, x + cote, y + cote], outline=TRAIT)

    if not lignes:
        d.text((24, 100), "Aucun visage suivi dans cet extrait.", font=police(24), fill=DISCRET)
    for r, p in enumerate(lignes):
        y0 = 70 + haut_ligne * r
        d.rectangle([12, y0, largeur - 12, y0 + haut_ligne - 10], fill=PANNEAU)
        if p.get("public"):
            gens = public["personnes"]
            d.text((24, y0 + 14), "PUBLIC", font=police(26, True), fill=DISCRET)
            d.text((24 + d.textlength("PUBLIC   ", font=police(26, True)), y0 + 20),
                   f"{len(gens)} personne{'s' if len(gens) > 1 else ''}, "
                   f"{_duree(public['temps_s'])} à l'image au total. Ni analysées, ni "
                   "étiquetées, sans lettre.", font=police(18), fill=DISCRET)
            d.text((24, y0 + 56), _tenir(d, public.get("regle", ""), police(16), largeur - 60),
                   font=police(16), fill=DISCRET)
            nb_max = (largeur - 24 - 24 + 10) // (petit + 10)
            for k, g in enumerate(gens[:nb_max]):
                x, y = 24 + k * (petit + 10), y0 + 92
                imagette(max(g["pistes"], key=lambda q: (q in vig, ident_images(v, q))), x, y,
                         petit)
                d.text((x + petit / 2, y + petit + 4), _duree(g["temps_s"]), font=police(13),
                       fill=DISCRET, anchor="ma")
            continue
        if p.get("autres"):
            membres = ident["autres"]["pistes"]
            d.text((24, y0 + 14), "AUTRES VISAGES", font=police(26, True), fill=DISCRET)
            d.text((24, y0 + 50), f"{len(membres)} pistes, {_duree(ident['autres']['temps_s'])} "
                   f"à l'image au total : vus moins de {TEMPS_MIN_PERSONNE:.0f} s, ou jamais "
                   "assez de face pour une empreinte", font=police(18), fill=DISCRET)
            x0 = 24
        else:
            membres = p["pistes"]
            meilleure = max(membres, key=lambda q: (q in vig, ident_images(v, q)))
            imagette(meilleure, 24, y0 + 14, 180)
            d.text((224, y0 + 12), p["id"], font=police(40, True), fill=VERT)
            d.text((276, y0 + 22), p["nom"] or "nom non fourni", font=police(28, True),
                   fill=TEXTE if p["nom"] else DISCRET)
            source = f" (nom : {p['source_nom']})" if p["source_nom"] else ""
            d.text((224, y0 + 62), f"à l'image {_duree(p['temps_s'])} · parole "
                   f"{_duree(parole.get(p['id'], 0.0))} · {len(membres)} pistes{source}",
                   font=police(18), fill=TEXTE)
            x0 = 224
        nb_max = (largeur - 24 - x0 + 10) // (petit + 10)
        choix = membres if len(membres) <= nb_max else [
            membres[round(k * (len(membres) - 1) / (nb_max - 1))] for k in range(nb_max)]
        for k, q in enumerate(choix):
            x, y = x0 + k * (petit + 10), y0 + 92
            imagette(q, x, y, petit)
            d.text((x + petit / 2, y + petit + 4), tc(v.debut + ident["premiere"][q] / v.fps),
                   font=police(13), fill=DISCRET, anchor="ma")
    y = 70 + haut_ligne * max(len(lignes), 1) + 8
    d.text((24, y), "Lettres attribuées aux participants par temps à l'image. L'outil ne "
           "reconnaît personne : les noms viennent de --noms ou des photos (--visages).",
           font=police(16), fill=DISCRET)
    d.text((24, y + 24), "Petites vignettes : une par piste (un passage continu du même visage "
           "dans un plan), avec l'heure de son apparition.", font=police(16), fill=DISCRET)
    d.text((24, y + 48), AVERTISSEMENT, font=police(16), fill=DISCRET)
    img.save(chemin, quality=90)


def ident_images(v: Visages, piste: int) -> int:
    return int((v.piste == piste).sum())
