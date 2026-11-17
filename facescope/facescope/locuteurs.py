"""Qui parle : chaque morceau de phrase transcrit est attribué à une personne reconnue, à
une « voix hors champ », ou reste « indéterminé ».

1. La bouche (toujours). Pour un morceau, on prend les images couvertes par ses mots. Une
   personne est candidate si son visage est mesurable sur au moins VISIBLE_MIN de ces
   images ; on mesure la part de ses images mesurables où sa mâchoire bouge (règle de la
   0.4 : écart type de l'ouverture de la mâchoire sur 0,5 s au-dessus de 0,02).
     - la meilleure candidate a au moins SEUIL_BOUCHE et MARGE_BOUCHE d'avance : elle parle ;
     - elle a au moins SEUIL_BOUCHE mais une autre la suit de près : « indéterminé » (deux
       bouches bougent, souvent quand les personnes parlent en même temps) ;
     - sinon (personne à l'image, ou bouches immobiles) : « voix hors champ ».
2. La voix (sauf --sans-voix). Une empreinte vocale par morceau d'au moins DUREE_VOIX_MIN
   (modèle WeSpeaker ResNet34, licence CC BY 4.0). La voix d'une personne est la moyenne
   des empreintes des morceaux que la bouche lui attribue (au moins ANCRES_MIN morceaux et
   ANCRES_S secondes). Un morceau dont l'empreinte ressemble à une seule de ces voix
   (similarité ≥ SEUIL_VOIX, avance ≥ MARGE_VOIX) est attribué à cette personne, même hors
   champ ou quand deux bouches bougent. Une voix qui ne ressemble à aucune personne reconnue
   reste « voix hors champ ».
"""
from __future__ import annotations

import numpy as np

from .analyse import modele_controle

SEUIL_BOUCHE = 0.5     # part des images mesurables où la bouche bouge pendant les mots
MARGE_BOUCHE = 0.2     # avance sur la deuxième personne à l'image
VISIBLE_MIN = 0.25     # part des images des mots où le visage doit être mesurable
HORS_CHAMP = "voix hors champ"
INDETERMINE = "indéterminé"

# Empreinte vocale : WeSpeaker ResNet34-LM entraîné sur VoxCeleb, dépôt officiel de l'éditeur
# sur Hugging Face, fichier figé à un commit et contrôlé par son empreinte SHA-256.
URL_VOIX = ("https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM/resolve/"
            "f0c48c298fd835726c27956a5d617bad7115627e/voxceleb_resnet34_LM.onnx")
SHA256_VOIX = "7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068"
FICHIER_VOIX = "wespeaker_voxceleb_resnet34_LM.onnx"
MODELE_VOIX = ("WeSpeaker ResNet34-LM (huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM),"
               " licence CC BY 4.0, 26,5 Mo")
DUREE_VOIX_MIN = 1.0   # secondes : en dessous, pas d'empreinte vocale
ANCRES_MIN, ANCRES_S = 3, 6.0
SEUIL_VOIX = 0.5       # similarité cosinus minimale avec la voix d'une personne
MARGE_VOIX = 0.2       # avance sur la deuxième voix la plus proche


class EmpreinteVocale:
    """Empreinte vocale (256 nombres, normalisée) d'un extrait de son à 16 kHz."""

    def __init__(self):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.log_severity_level = 3
        chemin = modele_controle(URL_VOIX, FICHIER_VOIX, SHA256_VOIX,
                                 "d'empreinte vocale (WeSpeaker ResNet34, 26,5 Mo)")
        self.session = ort.InferenceSession(chemin, options, providers=["CPUExecutionProvider"])
        self.entree = self.session.get_inputs()[0].name
        self.bancs = _bancs_mel()

    def calculer(self, son: np.ndarray) -> np.ndarray:
        x = self.session.run(None, {self.entree: _fbank(son, self.bancs)[None]})[0][0]
        return x / max(float(np.linalg.norm(x)), 1e-9)


def _bancs_mel(nb: int = 80, taille: int = 512, freq: int = 16000) -> np.ndarray:
    """Bancs de filtres mel à la manière de Kaldi (20 Hz à 8 kHz)."""
    def mel(f):
        return 1127.0 * np.log(1.0 + f / 700.0)
    points = np.linspace(mel(20.0), mel(freq / 2), nb + 2)
    frequences = mel(np.arange(taille // 2) * freq / taille)
    bancs = np.zeros((nb, taille // 2 + 1))
    for b in range(nb):
        g, c, d = points[b], points[b + 1], points[b + 2]
        bancs[b, :taille // 2] = np.maximum(0.0, np.minimum((frequences - g) / (c - g),
                                                            (d - frequences) / (d - c)))
    return bancs


def _fbank(son: np.ndarray, bancs: np.ndarray) -> np.ndarray:
    """80 énergies log-mel par trame de 25 ms toutes les 10 ms, moyenne retirée (réglages
    Kaldi de WeSpeaker : fenêtre de Hamming, préaccentuation 0,97, sans tremblement)."""
    x = son.astype(np.float64)                 # entiers 16 bits, comme à l'entraînement
    nb = 1 + (len(x) - 400) // 160
    trames = x[np.arange(400)[None, :] + 160 * np.arange(nb)[:, None]]
    trames = trames - trames.mean(axis=1, keepdims=True)
    trames = np.concatenate([trames[:, :1] * 0.03, trames[:, 1:] - 0.97 * trames[:, :-1]], axis=1)
    spectre = np.abs(np.fft.rfft(trames * np.hamming(400)[None, :], 512, axis=1)) ** 2
    f = np.log(np.maximum(spectre @ bancs.T, np.finfo(np.float32).eps))
    return (f - f.mean(axis=0, keepdims=True)).astype(np.float32)


class Attribution:
    """Attribue chaque morceau de phrase (bouche, puis voix), puis répond à (début, fin)."""

    def __init__(self, transcription: dict, personnes: dict, fps: float, n: int):
        """`personnes` : {identifiant: (images mesurables, bouche en mouvement)}."""
        mots = transcription.get("mots", [])
        self.d = np.array([w["debut"] for w in mots])
        self.f = np.array([w["fin"] for w in mots])
        self.centres = (self.d + self.f) / 2
        self.fps, self.n = fps, n
        self.personnes = {p: (ok.astype(bool), (bouche & ok).astype(bool))
                          for p, (ok, bouche) in personnes.items()}
        self.morceaux = []
        self.voix = {}                         # personne -> nombre de morceaux qui font sa voix
        self.empreintes = None                 # empreinte vocale de chaque morceau (ou None)

    def _images(self, debut: float, fin: float) -> np.ndarray:
        choix = (self.centres >= debut) & (self.centres <= fin)
        if not choix.any():
            choix = (self.f > debut) & (self.d < fin)
        masque = np.zeros(self.n, bool)
        for a, b in zip(self.d[choix], self.f[choix]):
            masque[max(0, int(a * self.fps)):min(self.n, int(np.ceil(b * self.fps)) + 1)] = True
        if not masque.any():
            masque[max(0, int(debut * self.fps)):min(self.n, int(np.ceil(fin * self.fps)))] = True
        return masque

    def bouche(self, debut: float, fin: float) -> tuple:
        images = self._images(debut, fin)
        total = max(int(images.sum()), 1)
        scores = {}
        for p, (ok, bouche) in self.personnes.items():
            vus = int((ok & images).sum())
            if vus / total >= VISIBLE_MIN:
                scores[p] = (bouche & images).sum() / vus
        classes = sorted(scores.items(), key=lambda x: -x[1])
        if classes and classes[0][1] >= SEUIL_BOUCHE:
            second = classes[1][1] if len(classes) > 1 else 0.0
            qui = classes[0][0] if classes[0][1] - second >= MARGE_BOUCHE else INDETERMINE
        else:
            qui = HORS_CHAMP
        return qui, {p: round(float(x), 2) for p, x in classes}

    def attribuer(self, morceaux: list, son: np.ndarray | None = None,
                  vocale: EmpreinteVocale | None = None, freq: int = 16000,
                  empreintes: list | None = None) -> list:
        """Attribue tous les morceaux ; avec `son` et `vocale` (ou les `empreintes` vocales
        déjà calculées pour les mêmes morceaux), la voix complète la bouche."""
        self.morceaux = []
        for q in morceaux:
            qui, scores = self.bouche(q["debut"], q["fin"])
            self.morceaux.append({"debut": round(q["debut"], 2), "fin": round(q["fin"], 2),
                                  "locuteur": qui, "par_la_bouche": qui, "bouche": scores,
                                  "source": "bouche" if qui in self.personnes else None})
        if empreintes is None:
            if son is None or vocale is None:
                return self.morceaux
            empreintes = []
            for q in self.morceaux:
                a, b = int(q["debut"] * freq), min(len(son), int(q["fin"] * freq))
                empreintes.append(vocale.calculer(son[a:b])
                                  if (b - a) >= DUREE_VOIX_MIN * freq else None)
        self.empreintes = empreintes
        profils = {}
        for p in self.personnes:
            ancres = [k for k, q in enumerate(self.morceaux)
                      if q["par_la_bouche"] == p and empreintes[k] is not None]
            duree = sum(self.morceaux[k]["fin"] - self.morceaux[k]["debut"] for k in ancres)
            if len(ancres) >= ANCRES_MIN and duree >= ANCRES_S:
                moyenne = np.mean([empreintes[k] for k in ancres], axis=0)
                profils[p] = moyenne / max(float(np.linalg.norm(moyenne)), 1e-9)
                self.voix[p] = len(ancres)
        for q, e in zip(self.morceaux, empreintes):
            if e is None or not profils:
                continue
            sims = sorted(((float(e @ v), p) for p, v in profils.items()), reverse=True)
            q["voix"] = {p: round(x, 2) for x, p in sims}
            second = sims[1][0] if len(sims) > 1 else 0.0
            if sims[0][0] >= SEUIL_VOIX and sims[0][0] - second >= MARGE_VOIX:
                p = sims[0][1]
                q["source"] = "bouche et voix" if q["par_la_bouche"] == p else "voix"
                q["locuteur"] = p
            elif q["par_la_bouche"] in profils and q["voix"][q["par_la_bouche"]] \
                    < SEUIL_VOIX - MARGE_VOIX:
                # La bouche désigne une personne dont on connaît la voix, mais la voix de ce
                # morceau ne lui ressemble pas du tout : on ne tranche pas.
                q["locuteur"], q["source"] = INDETERMINE, None
        return self.morceaux

    def __call__(self, debut: float, fin: float) -> str:
        """Locuteur d'un morceau déjà attribué (sinon par la bouche seule)."""
        for q in self.morceaux:
            if abs(q["debut"] - debut) < 0.011 and abs(q["fin"] - fin) < 0.011:
                return q["locuteur"]
        return self.bouche(debut, fin)[0]


def tours(morceaux: list, qui: str) -> list:
    """Tours de parole d'une personne : ses morceaux consécutifs, réunis tant que personne
    d'autre ne parle entre eux."""
    sortie, ouvert = [], False
    for q in sorted(morceaux, key=lambda q: q["debut"]):
        if q["locuteur"] == qui:
            if ouvert:
                sortie[-1][1] = max(sortie[-1][1], q["fin"])
            else:
                sortie.append([q["debut"], q["fin"]])
            ouvert = True
        else:
            ouvert = False
    return [tuple(t) for t in sortie]


def pour_personne(transcription: dict, morceaux: list, qui: str) -> dict:
    """La transcription réduite à la parole attribuée à une personne, avec ses tours."""
    ses_tours = tours(morceaux, qui)
    mots, tour_prec = [], None
    for w in transcription.get("mots", []):
        centre = (w["debut"] + w["fin"]) / 2
        k = next((k for k, (a, b) in enumerate(ses_tours) if a <= centre <= b), None)
        if k is None:
            continue
        mots.append(dict(w, nouveau_tour=k != tour_prec))
        tour_prec = k
    phrases = []
    for q in morceaux:
        if q["locuteur"] == qui:
            texte = " ".join(w["mot"] for w in transcription.get("mots", [])
                             if q["debut"] <= (w["debut"] + w["fin"]) / 2 <= q["fin"])
            phrases.append({"texte": texte, "debut": q["debut"], "fin": q["fin"]})
    return {"langue": transcription.get("langue"), "modele": transcription.get("modele"),
            "mots": mots, "phrases": phrases, "tours": ses_tours}


def masque_tours(ses_tours: list, t: np.ndarray) -> np.ndarray:
    masque = np.zeros(len(t), bool)
    for a, b in ses_tours:
        masque |= (t >= a) & (t <= b)
    return masque


def repartition(morceaux: list) -> dict:
    """Secondes de parole par locuteur (personne, voix hors champ, indéterminé)."""
    temps = {}
    for q in morceaux:
        temps[q["locuteur"]] = temps.get(q["locuteur"], 0.0) + q["fin"] - q["debut"]
    return {qui: round(x, 1) for qui, x in sorted(temps.items(), key=lambda x: -x[1])}
