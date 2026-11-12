"""Passe 2 : des mesures brutes aux signaux lisibles.

Tout est comparé à la personne elle-même (sa "ligne de base" dans la vidéo).
Aucun de ces signaux n'indique un mensonge : ils disent quand le comportement
s'écarte de l'habituel, pas pourquoi.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import audio as voix
from .analyse import Mesures

# Unités d'action FACS approchées à partir des coefficients MediaPipe.
UNITES = [
    ("AU1", "Sourcils intérieurs levés", ["browInnerUp"]),
    ("AU2", "Sourcils extérieurs levés", ["browOuterUpLeft", "browOuterUpRight"]),
    ("AU4", "Sourcils froncés", ["browDownLeft", "browDownRight"]),
    ("AU5", "Yeux écarquillés", ["eyeWideLeft", "eyeWideRight"]),
    ("AU6", "Joues remontées", ["cheekSquintLeft", "cheekSquintRight"]),
    ("AU7", "Paupières plissées", ["eyeSquintLeft", "eyeSquintRight"]),
    ("AU9", "Nez plissé", ["noseSneerLeft", "noseSneerRight"]),
    ("AU10", "Lèvre supérieure levée", ["mouthUpperUpLeft", "mouthUpperUpRight"]),
    ("AU12", "Coins des lèvres tirés", ["mouthSmileLeft", "mouthSmileRight"]),
    ("AU14", "Lèvres serrées en coin", ["mouthDimpleLeft", "mouthDimpleRight"]),
    ("AU15", "Coins des lèvres abaissés", ["mouthFrownLeft", "mouthFrownRight"]),
    ("AU17", "Menton relevé", ["mouthShrugLower"]),
    ("AU20", "Lèvres étirées", ["mouthStretchLeft", "mouthStretchRight"]),
    ("AU24", "Lèvres pressées", ["mouthPressLeft", "mouthPressRight"]),
    ("AU26", "Mâchoire ouverte", ["jawOpen"]),
    ("AU28", "Lèvres rentrées", ["mouthRollLower", "mouthRollUpper"]),
    ("AU45", "Clignement", ["eyeBlinkLeft", "eyeBlinkRight"]),
]
CODES = [u[0] for u in UNITES]
AFFICHEES = ["AU1", "AU2", "AU4", "AU5", "AU7", "AU10", "AU12", "AU14", "AU15", "AU17",
             "AU20", "AU24"]
HORS_VISAGE = {"AU26", "AU45"}     # parole et clignements sont traités à part
BOUCHE = {"AU10", "AU12", "AU14", "AU15", "AU17", "AU20", "AU24", "AU28"}

# Configurations types (Ekman/Friesen) : (nom, unités obligatoires, poids).
EXPRESSIONS = [
    ("Sourire", ["AU12"], {"AU12": .70, "AU6": .15, "AU7": .15}),
    ("Surprise", ["AU1", "AU2"], {"AU1": .30, "AU2": .30, "AU5": .20, "AU26": .20}),
    ("Froncement (colère)", ["AU4"], {"AU4": .50, "AU7": .20, "AU24": .30}),
    ("Tristesse", ["AU1", "AU15"], {"AU1": .35, "AU4": .20, "AU15": .45}),
    ("Dégoût", ["AU10"], {"AU9": .40, "AU10": .60}),
    ("Peur", ["AU5", "AU20"], {"AU1": .20, "AU2": .15, "AU4": .15, "AU5": .25, "AU20": .25}),
]

SEUIL_MOMENT = 2.0      # indice d'écart à partir duquel un moment est signalé
SEUIL_BREF = 3.5        # écart d'une unité d'action pour un mouvement bref
DUREE_BREF = 0.5        # secondes


@dataclass
class Signaux:
    ok: np.ndarray             # mesure exploitable (visage assez grand, pas trop de profil)
    au: np.ndarray             # (n, nAU) intensité brute 0..1
    intensite: np.ndarray      # (n, nAU) intensité par rapport au visage au repos
    z_au: np.ndarray           # (n, nAU) écart à la ligne de base, lissé sur 1 s
    expressions: np.ndarray    # (n, nExpr) ressemblance 0..1
    parle: np.ndarray
    vitesse_tete: np.ndarray   # degrés par seconde
    clignements: np.ndarray    # par minute, fenêtre de 10 s
    f0: np.ndarray             # Hz quand la personne parle
    db: np.ndarray
    groupes: dict              # famille -> (n,) écart
    ecart: np.ndarray          # (n,) indice global, ~1 = habituel
    percentile: np.ndarray     # (n,) rang 0..100 dans la vidéo
    moments: list
    brefs: list
    base: dict


def _noyau(k, n) -> np.ndarray:
    """Fenêtre de k images, impaire et jamais plus longue que l'extrait."""
    k = min(max(1, int(k)), n)
    return np.ones(k if k % 2 else max(k - 1, 1))


def glissant(x, ok, k) -> np.ndarray:
    """Moyenne glissante qui ignore les images non exploitables."""
    noyau = _noyau(k, len(x))
    k = len(noyau)
    bon = ok & np.isfinite(x)
    num = np.convolve(np.where(bon, x, 0.0), noyau, "same")
    den = np.convolve(bon.astype(float), noyau, "same")
    return np.where(den >= max(1.0, 0.3 * k), num / np.maximum(den, 1.0), np.nan)


def _z(x, ref, plancher):
    v = x[ref & np.isfinite(x)]
    if v.size < 10:
        return np.full(len(x), np.nan), np.nan
    med = float(np.median(v))
    ech = max(1.4826 * float(np.median(np.abs(v - med))), plancher)
    return (x - med) / ech, med


def _rms(colonnes) -> np.ndarray:
    pile = np.stack(colonnes, axis=1)
    nb = np.isfinite(pile).sum(axis=1)
    somme = np.nansum(np.clip(pile, -6, 6) ** 2, axis=1)
    return np.where(nb > 0, np.sqrt(somme / np.maximum(nb, 1)), np.nan)


def _stable(masque, mini) -> np.ndarray:
    """Ne garde que les séquences d'au moins `mini` images consécutives."""
    sortie, i, n = masque.copy(), 0, len(masque)
    while i < n:
        if not masque[i]:
            i += 1
            continue
        j = i
        while j < n and masque[j]:
            j += 1
        if j - i < mini:
            sortie[i:j] = False
        i = j
    return sortie


def _pics(x, separation, nb_max, seuil) -> list:
    choisis = []
    for i in np.argsort(-np.nan_to_num(x, nan=-1.0)):
        if not np.isfinite(x[i]) or x[i] < seuil or len(choisis) >= nb_max:
            break
        if all(abs(int(i) - j) >= separation for j in choisis):
            choisis.append(int(i))
    return sorted(choisis)


def calculer(m: Mesures, audio: dict | None = None, base: tuple | None = None) -> Signaux:
    n, fps = m.n, m.fps
    col = {nom: i for i, nom in enumerate(m.noms_bs)}

    def moyenne(noms):
        presents = [m.bs[:, col[x]].astype(float) for x in noms if x in col]
        return np.mean(presents, axis=0) if presents else np.full(n, np.nan)

    au = np.stack([moyenne(b) for _, _, b in UNITES], axis=1)
    k_au = {code: i for i, code in enumerate(CODES)}
    largeur_visage = m.boite[:, 2] - m.boite[:, 0]
    with np.errstate(invalid="ignore"):
        ok = m.valide & (largeur_visage >= 60) & (np.abs(m.angles[:, 0]) <= 40)
    ok = _stable(ok, int(0.5 * fps))       # un visage vu moins d'une demi-seconde ne compte pas

    ref, source = ok.copy(), "vidéo entière"
    if base:
        dans = ok & (m.t >= base[0]) & (m.t <= base[1])
        if dans.sum() >= 3 * fps:
            ref, source = dans, f"passage {base[0]:.0f}-{base[1]:.0f} s"

    # Unités d'action : écart image par image, puis lissé sur une seconde.
    z_image = np.full_like(au, np.nan)
    z_au = np.full_like(au, np.nan)
    intensite = np.zeros_like(au)
    for k in range(au.shape[1]):
        z_image[:, k], _ = _z(au[:, k], ref, 0.03)
        z_au[:, k] = glissant(z_image[:, k], ok, fps)
        v = au[ref, k]
        repos, haut = np.percentile(v, [10, 99.5]) if v.size else (0.0, 0.5)
        # Les coefficients n'ont pas tous la même plage : on se cale sur celle observée.
        amplitude = float(np.clip(haut - repos, 0.2, 0.5))
        intensite[:, k] = np.clip(np.nan_to_num((au[:, k] - repos) / amplitude), 0, 1)

    expressions = np.zeros((n, len(EXPRESSIONS)))
    for e, (_, pivots, poids) in enumerate(EXPRESSIONS):
        pivot = np.mean([intensite[:, k_au[c]] for c in pivots], axis=0)
        total = sum(w * intensite[:, k_au[c]] for c, w in poids.items())
        expressions[:, e] = np.clip(np.minimum(1.0, pivot / 0.35) * total, 0, 1)

    # Parole : la mâchoire bouge.
    machoire = au[:, k_au["AU26"]]
    m1, m2 = glissant(machoire, ok, 0.5 * fps), glissant(machoire ** 2, ok, 0.5 * fps)
    with np.errstate(invalid="ignore"):
        parle = np.sqrt(np.maximum(m2 - m1 ** 2, 0)) > 0.02
    parle = np.convolve(parle.astype(float), _noyau(0.6 * fps, n), "same") > 0

    # Tête : vitesse angulaire.
    d = np.diff(m.angles, axis=0, prepend=m.angles[:1])
    vitesse = np.linalg.norm(d, axis=1) * fps
    continu = ok & np.roll(ok, 1)
    continu[0] = False
    continu[[c for c in m.coupes if c < n]] = False
    vitesse_tete = glissant(np.where(continu, vitesse, np.nan), continu, fps)
    z_tete, _ = _z(vitesse_tete, ref, 2.0)

    # Regard : écart par rapport à la direction habituelle.
    def bs(nom):
        return m.bs[:, col[nom]].astype(float) if nom in col else np.zeros(n)
    horiz = (bs("eyeLookInLeft") + bs("eyeLookOutRight")
             - bs("eyeLookOutLeft") - bs("eyeLookInRight")) / 2
    vert = (bs("eyeLookUpLeft") + bs("eyeLookUpRight")
            - bs("eyeLookDownLeft") - bs("eyeLookDownRight")) / 2
    h0 = np.median(horiz[ref]) if ref.any() else 0.0
    v0 = np.median(vert[ref]) if ref.any() else 0.0
    regard = glissant(np.hypot(horiz - h0, vert - v0), ok, fps)
    z_regard, _ = _z(regard, ref, 0.03)

    # Clignements par minute sur 10 secondes.
    # Un clignement = paupières fermées moins d'une demi-seconde (au-delà, c'est un plissement).
    paupiere = np.nan_to_num(au[:, k_au["AU45"]])
    seuil = min(0.75, (np.median(paupiere[ref]) if ref.any() else 0.2) + 0.3)
    debut_clign = np.zeros(n, bool)
    i = 0
    while i < n:
        if not (ok[i] and paupiere[i] > seuil):
            i += 1
            continue
        j = i
        while j < n and ok[j] and paupiere[j] > seuil - 0.15:
            j += 1
        debut_clign[i] = j - i <= 0.5 * fps
        i = j
    noyau = _noyau(10 * fps, n)
    secondes = np.convolve(ok.astype(float), noyau, "same") / fps
    clignements = np.where(secondes >= 5,
                           np.convolve(debut_clign.astype(float), noyau, "same")
                           / np.maximum(secondes, 1e-6) * 60, np.nan)
    z_clign, clign_base = _z(clignements, ref, 4.0)

    # Voix : seulement quand la personne suivie parle.
    f0, db = voix.sur_images(audio, m.t)
    f0 = np.where(parle & ok, f0, np.nan)
    db_parle = np.where(parle & ok, db, np.nan)
    z_f0, f0_base = _z(f0, ref, 8.0)
    z_db, _ = _z(db_parle, ref, 2.0)

    visage = [z_au[:, k] for k, c in enumerate(CODES) if c not in HORS_VISAGE]
    groupes = {
        "Visage": _rms(visage),
        "Tête": np.abs(z_tete),
        "Regard": _rms([z_regard, z_clign]),
        "Voix": _rms([z_f0, z_db]),
    }
    ecart = _rms(list(groupes.values()))
    ecart[~np.isfinite(groupes["Visage"]) | ~ok] = np.nan

    percentile = np.full(n, np.nan)
    fini = np.isfinite(ecart)
    if fini.sum() > 1:
        rang = np.argsort(np.argsort(ecart[fini]))
        percentile[fini] = 100.0 * rang / (fini.sum() - 1)

    # Moments les plus atypiques, avec les signaux qui les expliquent.
    details = [(f"{c} {lib}", z_au[:, k]) for k, (c, lib, _) in enumerate(UNITES)
               if c not in HORS_VISAGE]
    details += [("Mouvements de tête", z_tete), ("Regard détourné", z_regard),
                ("Clignements", z_clign), ("Hauteur de la voix", z_f0),
                ("Énergie de la voix", z_db)]
    moments = []
    for i in _pics(ecart, int(3 * fps), 8, SEUIL_MOMENT):
        forts = sorted(((nom, float(z[i])) for nom, z in details if np.isfinite(z[i])),
                       key=lambda p: -abs(p[1]))[:3]
        moments.append({"image": i, "t": float(m.t[i]), "ecart": float(ecart[i]),
                        "percentile": float(percentile[i]),
                        "signaux": [{"nom": nom, "z": round(z, 1)} for nom, z in forts]})

    # Mouvements brefs (moins d'une demi-seconde) d'une unité d'action.
    brefs = []
    for k, (code, lib, _) in enumerate(UNITES):
        if code in HORS_VISAGE:
            continue
        z = z_image[:, k]
        with np.errstate(invalid="ignore"):
            haut = ok & (np.nan_to_num(z, nan=0.0) > SEUIL_BREF)
        i = 0
        while i < n:
            if not haut[i]:
                i += 1
                continue
            j = i
            while j < n and haut[j]:
                j += 1
            articulation = code in BOUCHE and parle[i]     # la parole fait bouger la bouche
            if 2 <= j - i <= DUREE_BREF * fps and not articulation:
                brefs.append({"image": i, "t": float(m.t[i]), "duree": (j - i) / fps,
                              "code": code, "nom": lib, "z": round(float(np.max(z[i:j])), 1)})
            i = j
    brefs.sort(key=lambda b: b["t"])

    base_info = {
        "source": source,
        "images_exploitables_pct": round(100.0 * ok.mean(), 1),
        "parle_pct": round(100.0 * (parle & ok).sum() / max(ok.sum(), 1), 1),
        "clignements_par_min": None if not np.isfinite(clign_base) else round(clign_base, 1),
        "hauteur_voix_hz": None if not np.isfinite(f0_base) else round(f0_base, 1),
    }
    return Signaux(ok=ok, au=au, intensite=intensite, z_au=z_au, expressions=expressions,
                   parle=parle, vitesse_tete=vitesse_tete, clignements=clignements, f0=f0,
                   db=db, groupes=groupes, ecart=ecart, percentile=percentile,
                   moments=moments, brefs=brefs, base=base_info)
