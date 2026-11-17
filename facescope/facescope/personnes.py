"""Analyse par personne : qui est à l'image, qui parle, et pour chacune sa ligne de base,
ses passages (quand elle parle, quand elle écoute) et sa synthèse.

Deux modes :
  - « une personne » (une seule personne reconnue, sans --debat) : la personne A reprend
    exactement l'analyse de la 0.4 (visage dominant de chaque plan, toute la parole lui est
    comptée) ;
  - « débat » (au moins deux personnes, ou --debat) : une vue par personne (ses seules
    pistes), la parole attribuée au locuteur visible (locuteurs.py), une ligne de base par
    personne et par rôle (quand elle parle, quand elle écoute), et des passages coupés à
    chaque changement de locuteur.

Participants et public (0.6, débat avec transcription) : un participant est une personne
nommée par une photo (--visages) ou qui parle vraiment, c'est-à-dire qui reçoit, quand toutes
les personnes reconnues sont candidates, au moins SEUIL_PAROLE_S secondes de parole et
PART_PAROLE de la parole attribuée de l'extrait. Les autres forment le public : ni lettre, ni
analyse, ni étiquette dans la vidéo, ni parole (l'attribution est refaite entre les seuls
participants ; un morceau que seule la bouche d'une personne du public désignait, et qu'aucun
participant ne reprend, reste « indéterminé »). --noms nomme ensuite les lettres des
participants.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import croisement, identite, locuteurs, parole, signaux
from .analyse import Mesures, Visages, vue_personne
from .rendu import tc

VISIBLE_PASSAGE = 0.25   # part d'un passage où le visage est suivi pour « être à l'image »
# Participant : parole attribuée d'au moins SEUIL_PAROLE_S secondes et PART_PAROLE de la
# parole attribuée de l'extrait. Débat Maréchal-Villepin (50 min, 2 738 s attribuées) :
# huit personnes du public reçoivent 0 à 8,4 s chacune (0,3 % au plus, mâchoire qui bouge
# pendant qu'un candidat parle hors champ), le présentateur 74,6 s (2,7 %), les candidats
# plus de 1 000 s. 1 % (27 s ici) passe entre les deux avec une marge d'un facteur 3 de
# chaque côté ; le plancher de 5 s tient sur un court extrait (quelques minutes), où 1 %
# ne fait que 1 à 2 s.
SEUIL_PAROLE_S = 5.0
PART_PAROLE = 0.01


@dataclass
class Personne:
    id: str
    nom: str | None
    source_nom: str | None
    pistes: list
    m: Mesures
    s: signaux.Signaux | None
    croise: dict | None
    statut: str                      # « analysé » ou « pas assez de données »
    temps_image_s: float
    temps_fiable_s: float
    temps_parole_s: float
    transcription: dict | None       # parole attribuée à la personne
    passages: dict = field(default_factory=dict)   # numéro du passage commun -> passage

    @property
    def etiquette(self) -> str:
        return self.nom or self.id


@dataclass
class Debat:
    mode: str                        # « une personne » ou « débat »
    personnes: list
    passages: list                   # passages communs : locuteur, personne lue, autres
    piste_personne: dict             # piste -> identifiant de la personne (None : autres)
    v: Visages
    morceaux: list                   # attribution de la parole, morceau par morceau
    voix: dict | None = None         # personne -> morceaux qui font sa voix (None : sans voix)
    public: dict | None = None       # personnes reconnues hors participants (débat)
    participants: dict = field(default_factory=dict)   # règle appliquée et seuil
    noms: list = field(default_factory=list)           # compte rendu de --noms

    def personne(self, ident: str | None) -> Personne | None:
        return next((p for p in self.personnes if p.id == ident), None)

    def nom(self, ident: str | None) -> str | None:
        p = self.personne(ident)
        return p.etiquette if p else ident


def _a_l_image(m: Mesures, i0: int, i1: int) -> float:
    return float(m.valide[i0:i1].mean()) if i1 > i0 else 0.0


def _surface(m: Mesures, i0: int, i1: int) -> float:
    b = m.boite[i0:i1]
    return float(np.nansum((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]))) / max(i1 - i0, 1)


def _base(q: dict) -> dict:
    cles = ("temps", "debut_s", "fin_s", "duree_s", "image_debut", "image_fin", "texte",
            "themes", "mots_distinctifs", "chiffre", "sujet")
    return {c: q[c] for c in cles}


def _manque(p_s: float) -> str:
    return (f"Pas assez de données : {p_s:.0f} s d'images fiables de cette personne, il en "
            f"faut {signaux.TEMPS_MIN_BASE:.0f} pour établir son habitude.")


def _role(q: dict, qui: str, transcrit: bool) -> str:
    if not transcrit:
        return "non déterminé"
    if not q["texte"]:
        return "sans parole"
    loc = q.get("locuteur")
    if loc == qui:
        return "parle"
    return "parole non attribuée" if loc == locuteurs.INDETERMINE else "écoute"


def _qui_lire(bases: list, vues: dict) -> None:
    """Personne lue : celle qui parle si elle est à l'image, sinon le plus grand visage ;
    autres : les autres personnes à l'image. Un choix par passage, pour un affichage stable."""
    for q in bases:
        i0, i1 = q["image_debut"], q["image_fin"]
        part = {p: _a_l_image(m, i0, i1) for p, m in vues.items()}
        presents = [p for p, x in part.items() if x >= VISIBLE_PASSAGE]
        loc = q.get("locuteur")
        if loc in presents:
            q["lue"] = loc
        elif presents:
            q["lue"] = max(presents, key=lambda p: _surface(vues[p], i0, i1))
        else:
            q["lue"] = None
        q["autres"] = sorted((p for p in presents if p != q["lue"]), key=lambda p: -part[p])


def _nommer_locuteurs(personnes: list) -> None:
    """Chaque passage d'une personne donne aussi le nom de qui parle, s'il est connu."""
    noms = {p.id: p.nom for p in personnes}
    for p in personnes:
        for q in p.passages.values():
            q["locuteur_nom"] = noms.get(q.get("locuteur"))


def _attribution_seule(texte: dict | None, m: Mesures, s: signaux.Signaux, qui: str) -> list:
    """Mode une personne : attribution par la bouche, pour information (rapport, alerte)."""
    if not texte or not texte.get("mots"):
        return []
    attribution = locuteurs.Attribution(texte, {qui: (s.ok, s.parle)}, m.fps, m.n)
    return attribution.attribuer(croisement.morceaux_de(texte, m.n / m.fps))


def _participants(ident: dict, attribution, texte: dict) -> dict:
    """Sépare participants et public d'après la parole attribuée quand toutes les personnes
    reconnues sont candidates. Sans participant trouvé, tout le monde reste participant."""
    reconnues = ident["personnes"]
    parole0 = locuteurs.repartition(attribution.morceaux)
    total = sum(q["fin"] - q["debut"] for q in attribution.morceaux)
    seuil = max(SEUIL_PAROLE_S, PART_PAROLE * total)
    for r in reconnues:
        r["parole_avant_exclusion_s"] = parole0.get(r["id"], 0.0)
    garde = {r["id"] for r in reconnues if r["nom"] or parole0.get(r["id"], 0.0) >= seuil}
    regle = (f"participant : personne nommée par une photo, ou qui reçoit au moins "
             f"{seuil:.0f} s de parole attribuée (le plus grand de {SEUIL_PAROLE_S:.0f} s et "
             f"{PART_PAROLE:.0%} des {total:.0f} s de parole attribuée de l'extrait) quand "
             "toutes les personnes reconnues sont candidates")
    info = {"regle": regle, "seuil_s": round(seuil, 1), "parole_attribuee_s": round(total, 1),
            "regle_public": f"Public : ni nommé par une photo, ni {seuil:.0f} s de parole "
                            f"attribuée (seuil : le plus grand de {SEUIL_PAROLE_S:.0f} s et "
                            f"{PART_PAROLE:.0%} des {total:.0f} s de parole attribuée)"}
    if not garde:
        info["note"] = ("aucune personne nommée ni au-dessus du seuil : toutes les personnes "
                        "reconnues sont gardées comme participants (comme en 0.5)")
        garde = {r["id"] for r in reconnues}
    info["garde"] = garde
    return info


def analyser(v: Visages, ident: dict, m0: Mesures, s0: signaux.Signaux, croise0: dict,
             son: dict | None, base: tuple | None, texte: dict | None,
             debat: bool = False, son_brut: np.ndarray | None = None,
             noms: dict | None = None, demander_noms=None) -> Debat | None:
    """`m0`, `s0`, `croise0` : l'analyse du visage dominant de chaque plan (0.4).
    `son_brut` (16 kHz) : si fourni, la voix complète la bouche pour savoir qui parle.
    `noms` (--noms) : appliqués aux lettres définitives (participants).
    `demander_noms(ident, parole)` (--demander-noms) : appelée dès que les lettres des
    participants sont définitives, avant toute analyse par personne ; les noms qu'elle
    renvoie s'ajoutent à `noms`, comme s'ils venaient de --noms."""
    reconnues = ident["personnes"]
    if not reconnues:
        return None
    fps, n = v.fps, v.n
    transcrit = bool(texte)

    if len(reconnues) == 1 and not debat:
        if demander_noms:
            noms = {**(noms or {}), **demander_noms(ident, {})}
        compte_noms = identite.nommer_lettres(ident, noms or {})
        r = reconnues[0]
        fiable_s = float(s0.ok.sum()) / fps
        assez = fiable_s >= signaux.TEMPS_MIN_BASE
        bases, choisis = [], []
        for k, q in enumerate(croise0["passages"]):
            b = dict(_base(q), locuteur=r["id"] if q["texte"] else None, lue=r["id"], autres=[])
            bases.append(b)
            role = _role(b, r["id"], transcrit)
            choisis.append(dict(q, numero=k, role=role, locuteur=b["locuteur"]))
        duree = n / fps
        parle_s = sum(max(0.0, min(duree, ph["fin"]) - max(0.0, ph["debut"]))
                      for ph in (texte or {}).get("phrases", []) if ph["texte"].strip())
        croise = None
        if assez:
            croise = {"passages": choisis,
                      "synthese": {"en_parlant": croisement.synthese(
                          [p for p in choisis if p["role"] == "parle"], s0),
                          "en_ecoutant": croisement.synthese([], s0)},
                      "regle": croisement.regle()}
        p = Personne(id=r["id"], nom=r["nom"], source_nom=r["source_nom"], pistes=r["pistes"],
                     m=m0, s=s0 if assez else None, croise=croise,
                     statut="analysé" if assez else "pas assez de données",
                     temps_image_s=r["temps_s"], temps_fiable_s=round(fiable_s, 1),
                     temps_parole_s=round(parle_s, 1), transcription=texte)
        p.passages = {k: q if assez else croisement.passage_vide(bases[k], _manque(fiable_s),
                                                                  q["role"])
                      for k, q in enumerate(choisis)}
        _nommer_locuteurs([p])
        return Debat(mode="une personne", personnes=[p], passages=bases,
                     piste_personne=ident["piste_personne"], v=v,
                     morceaux=_attribution_seule(texte, m0, s0, r["id"]), noms=compte_noms)

    # Débat : une vue par personne, la parole attribuée au locuteur visible.
    vues = {r["id"]: vue_personne(v, r["pistes"]) for r in reconnues}
    bouches = {}
    for qui, m in vues.items():
        ok = signaux.fiable(m)
        bouches[qui] = (ok, signaux.bouche_en_mouvement(m, ok))
    attribution, public, info = None, None, {
        "regle": "sans transcription, on ne sait pas qui parle : toutes les personnes "
                 "reconnues sont participants (comme en 0.5)"}
    if texte and texte.get("mots"):
        morceaux_texte = croisement.morceaux_de(texte, n / fps)
        attribution = locuteurs.Attribution(texte, bouches, fps, n)
        vocale = locuteurs.EmpreinteVocale() if son_brut is not None else None
        attribution.attribuer(morceaux_texte, son_brut, vocale)
        info = _participants(ident, attribution, texte)
        garde = info.pop("garde")
        exclus = {r["id"] for r in reconnues} - garde
        if exclus:
            lettres = identite.separer_public(ident, garde)
            public = ident["public"]
            public["regle"] = info["regle_public"]
            reconnues = ident["personnes"]
            vues = {lettres[a]: m for a, m in vues.items() if a in lettres}
            bouches = {lettres[a]: b for a, b in bouches.items() if a in lettres}
            # La parole se réattribue entre les seuls participants (mêmes empreintes vocales).
            premiere = attribution
            attribution = locuteurs.Attribution(texte, bouches, fps, n)
            attribution.attribuer(morceaux_texte, empreintes=premiere.empreintes)
            for q0, q in zip(premiere.morceaux, attribution.morceaux):
                if q0["locuteur"] in exclus:
                    q["avant_exclusion_du_public"] = "public"
                    if q["locuteur"] not in lettres.values():
                        q["locuteur"], q["source"] = locuteurs.INDETERMINE, None
    if demander_noms:
        parole = {}
        for q in (attribution.morceaux if attribution else []):
            parole[q["locuteur"]] = parole.get(q["locuteur"], 0.0) + q["fin"] - q["debut"]
        noms = {**(noms or {}), **demander_noms(ident, parole)}
    compte_noms = identite.nommer_lettres(ident, noms or {})
    reconnues = ident["personnes"]
    bases = croisement.passages_de_base(m0, texte, attribution)
    if attribution is None:
        for q in bases:
            q["locuteur"] = None
    _qui_lire(bases, vues)
    morceaux = attribution.morceaux if attribution else []

    personnes = []
    for r in reconnues:
        qui, m = r["id"], vues[r["id"]]
        ok = bouches[qui][0]
        fiable_s = float(ok.sum()) / fps
        if attribution is not None:
            texte_p = locuteurs.pour_personne(texte, morceaux, qui)
            voix = locuteurs.masque_tours(texte_p["tours"], m.t)
            parle_s = sum(q["fin"] - q["debut"] for q in morceaux if q["locuteur"] == qui)
        else:
            texte_p, voix, parle_s = texte, None, 0.0
        p = Personne(id=qui, nom=r["nom"], source_nom=r["source_nom"], pistes=r["pistes"], m=m,
                     s=None, croise=None, statut="pas assez de données",
                     temps_image_s=r["temps_s"], temps_fiable_s=round(fiable_s, 1),
                     temps_parole_s=round(parle_s, 1), transcription=texte_p)
        choisis = []
        for k, q in enumerate(bases):
            role = _role(q, qui, transcrit)
            if role == "parle" or _a_l_image(m, q["image_debut"], q["image_fin"]) \
                    >= VISIBLE_PASSAGE:
                choisis.append((k, q, role))
        if fiable_s >= signaux.TEMPS_MIN_BASE:
            p.s = signaux.calculer(m, son, base, texte_p, voix=voix, par_role=True)
            p.croise = croisement.croiser_personne(m, p.s, choisis, texte_p, transcrit,
                                                   p.nom or "la personne")
            p.statut = "analysé"
            p.passages = {q["numero"]: q for q in p.croise["passages"]}
        else:
            p.passages = {k: croisement.passage_vide(dict(q, numero=k), _manque(fiable_s), role)
                          for k, q, role in choisis}
        personnes.append(p)
    _nommer_locuteurs(personnes)
    return Debat(mode="débat", personnes=personnes, passages=bases,
                 piste_personne=ident["piste_personne"], v=v, morceaux=morceaux,
                 voix=attribution.voix if attribution is not None and son_brut is not None
                 else None, public=public, participants=info, noms=compte_noms)


# --- Rapport et console -----------------------------------------------------------------

def moments(s: signaux.Signaux, debut: float) -> list:
    return [{"temps": tc(debut + mo["t"]), "temps_s": round(debut + mo["t"], 2),
             "ecart": round(mo["ecart"], 2), "percentile": round(mo["percentile"], 1),
             "signaux": mo["signaux"]} for mo in s.moments]


def figements(s: signaux.Signaux, debut: float) -> list:
    return [{"temps": tc(debut + f["t"]), "temps_s": round(debut + f["t"], 2),
             "duree_s": round(f["duree"], 1), "z": f["z"]} for f in s.figements]


def ecarts_simultanes(s: signaux.Signaux, debut: float) -> list:
    return [{"temps": tc(debut + c["t"]), "temps_s": round(debut + c["t"], 2),
             "duree_s": round(c["duree"], 1), "canaux": c["canaux"]} for c in s.convergences]


def rapport(d: Debat, ident: dict, debut: float, photos: list) -> dict:
    entrees = []
    for p in d.personnes:
        e = {"id": p.id, "nom": p.nom, "source_du_nom": p.source_nom, "pistes": len(p.pistes),
             "temps_a_l_image_s": p.temps_image_s, "temps_fiable_s": p.temps_fiable_s,
             "temps_de_parole_s": p.temps_parole_s, "statut": p.statut,
             "ligne_de_base": None, "moments_atypiques": [], "figements": [],
             "ecarts_simultanes": [], "parole": None, "croisement": None}
        if p.s is not None:
            e.update(ligne_de_base=p.s.base, moments_atypiques=moments(p.s, debut),
                     figements=figements(p.s, debut),
                     ecarts_simultanes=ecarts_simultanes(p.s, debut),
                     parole=parole.lexique(p.transcription), croisement=p.croise)
        else:
            e["raison"] = _manque(p.temps_fiable_s)
        entrees.append(e)
    temps = locuteurs.repartition(d.morceaux)
    if d.mode == "une personne":
        methode = ("Une seule personne reconnue : toute la parole transcrite lui est comptée, "
                   "comme en 0.4. La répartition ci-dessous (bouche de la personne en "
                   "mouvement ou non pendant les mots) est donnée pour information.")
    else:
        methode = (f"Bouche : chaque morceau de phrase est attribué à la personne à l'image "
                   f"dont la bouche bouge sur au moins {locuteurs.SEUIL_BOUCHE:.0%} de ses "
                   f"images mesurables pendant les mots, avec {locuteurs.MARGE_BOUCHE:.0%} "
                   f"d'avance sur la suivante (visage mesurable sur au moins "
                   f"{locuteurs.VISIBLE_MIN:.0%} des images des mots) ; deux bouches qui "
                   "bougent : « indéterminé » ; aucune : « voix hors champ ».")
        if d.voix is None:
            methode += " Voix : non utilisée (--sans-voix ou pas de son)."
        else:
            methode += (f" Voix : la voix d'une personne est la moyenne des empreintes vocales "
                        f"des morceaux que la bouche lui attribue (au moins "
                        f"{locuteurs.ANCRES_MIN} morceaux et {locuteurs.ANCRES_S:.0f} s) ; un "
                        f"morceau d'au moins {locuteurs.DUREE_VOIX_MIN:.0f} s dont la voix lui "
                        f"ressemble (similarité ≥ {locuteurs.SEUIL_VOIX}, avance ≥ "
                        f"{locuteurs.MARGE_VOIX}) lui est attribué, même hors champ. Voix "
                        "établies : " + (", ".join(f"{p} ({k} morceaux)"
                                                   for p, k in d.voix.items()) or "aucune")
                        + f". Modèle : {locuteurs.MODELE_VOIX}.")
        if d.public:
            methode += (" Public : l'attribution est faite une première fois avec toutes les "
                        "personnes reconnues (pour savoir qui parle), puis refaite entre les "
                        "seuls participants ; un morceau que la bouche d'une personne du public "
                        "désignait porte « avant_exclusion_du_public » et reste « indéterminé » "
                        "si aucun participant ne le reprend.")
    public = None
    if d.public:
        public = {"personnes": len(d.public["personnes"]),
                  "temps_a_l_image_s": d.public["temps_s"], "pistes": len(d.public["pistes"]),
                  "regle": d.public.get("regle"),
                  "detail": [{"temps_a_l_image_s": g["temps_s"], "pistes": len(g["pistes"]),
                              "parole_attribuee_avant_exclusion_s":
                                  g.get("parole_avant_exclusion_s", 0.0)}
                             for g in d.public["personnes"]]}
    return {
        "mode": d.mode,
        "participants": {k: x for k, x in d.participants.items() if k != "regle_public"}
        if d.mode == "débat" else None,
        "personnes": entrees,
        "public": public,
        "autres_visages": {"pistes": len(ident["autres"]["pistes"]),
                           "temps_a_l_image_s": ident["autres"]["temps_s"],
                           "pistes_sans_empreinte": ident["autres"]["sans_empreinte"]},
        "identite": {"modele": identite.MODELE_EMPREINTE,
                     "methode": "pistes coupées là où leurs empreintes changent de personne ; "
                                "regroupement hiérarchique (lien moyen) sur la distance "
                                "cosinus entre pistes ; deux pistes vues en même temps ne sont "
                                "jamais réunies ; réaffectation d'une piste nettement plus "
                                "proche d'une autre personne ; personnes classées par temps à "
                                "l'image, lettres données aux seuls participants",
                     "seuil_de_fusion": identite.SEUIL_FUSION,
                     "seuil_de_changement_dans_une_piste": identite.SEUIL_CHANGEMENT,
                     "marge_de_reaffectation": identite.MARGE_REAFFECTATION,
                     "temps_min_personne_s": identite.TEMPS_MIN_PERSONNE,
                     **ident["details"], "noms_et_photos": photos},
        "locuteurs": {"methode": methode, "parole_par_locuteur_s": temps,
                      "morceaux": [dict(q, debut=round(debut + q["debut"], 2),
                                        fin=round(debut + q["fin"], 2)) for q in d.morceaux]},
    }


def _duree(secondes: float) -> str:
    secondes = int(round(secondes))
    return f"{secondes} s" if secondes < 60 else f"{secondes // 60} min {secondes % 60:02d} s"


def resume(d: Debat, debut: float) -> list:
    """Lignes de la synthèse par personne, pour la console."""
    lignes = []
    for p in d.personnes:
        nom = f"Personne {p.id}" + (f" ({p.nom})" if p.nom else "")
        lignes.append(f"\n{nom} : {_duree(p.temps_image_s)} à l'image, "
                      f"{_duree(p.temps_parole_s)} de parole attribuée.")
        if p.s is None:
            lignes.append("  " + _manque(p.temps_fiable_s))
            continue
        roles = p.s.base.get("par_role")
        par_role = ""
        if roles:
            par_role = " (habitude par rôle : " + ", ".join(
                f"{'en parlant' if r == 'parle' else 'en écoutant'} "
                f"{_duree(x['images_de_reference_s'])}" + (" → repli global" if x["repli"] else "")
                for r, x in roles.items()) + ")"
        lignes.append(f"  Ligne de base sur {_duree(p.temps_fiable_s)} d'images fiables"
                      f"{par_role}. "
                      f"{len(p.s.moments)} moments atypiques, {len(p.s.figements)} figements, "
                      f"{len(p.s.convergences)} écarts simultanés.")
        for k, mo in enumerate(p.s.moments[:5]):
            causes = ", ".join(f"{x['nom']} ({x['z']:+.1f})" for x in mo["signaux"])
            lignes.append(f"    {k + 1}. {tc(debut + mo['t'])}  écart {mo['ecart']:.1f}  {causes}")
        for cle, quand in (("en_parlant", "En parlant"), ("en_ecoutant", "En écoutant")):
            synth = p.croise["synthese"][cle]
            if not synth["passages"]:
                continue
            lignes.append(f"  {quand} : {synth['passages']} passages ("
                          + ", ".join(f"{o} {nb}" for o, nb in synth["repartition"].items() if nb)
                          + ").")
            if synth["themes"] and not synth["classement"]:
                lignes.append(f"    Aucun thème assez long pour un classement (minimum "
                              f"{croisement.TEMPS_THEME_MIN:.0f} s et "
                              f"{croisement.PASSAGES_THEME_MIN} passages mesurés).")
            for sens in ("s'anime", "se retient"):
                themes = synth["plus_marques"][sens][:3]
                if themes:
                    lignes.append(f"    Thèmes où la personne {sens} le plus : " + ", ".join(
                        f"{t['theme']} ({t['part_pct']} % de {_duree(t['temps_s'])})"
                        for t in themes))
    if d.public:
        lignes.append(f"\nPublic : {len(d.public['personnes'])} personnes, "
                      f"{_duree(d.public['temps_s'])} à l'image au total, ni analysées ni "
                      f"étiquetées ({d.public.get('regle', '')}).")
    if d.morceaux:
        lignes.append("\nParole par locuteur : " + ", ".join(
            f"{d.nom(q) if q not in (locuteurs.HORS_CHAMP, locuteurs.INDETERMINE) else q} "
            f"{_duree(x)}" for q, x in locuteurs.repartition(d.morceaux).items()))
    return lignes
