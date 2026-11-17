"""Croisement : ce qui est dit, mis en regard de ce que montrent les mesures.

La parole est découpée en passages de 4 à 15 secondes. Pour chaque passage : le sujet
(thèmes reconnus par mots-clés, sinon les mots les plus distinctifs), les écarts mesurés
sur les images fiables, une orientation et une phrase de lecture.

Règle d'orientation (seuils SEUIL_* ci-dessous, réglés à la main, non validés sur des
extraits annotés). Chaque critère compare un écart signé à l'habitude de la personne,
moyenné sur les images fiables du passage (pour le silence : le plus long du passage).
  s'anime    : plus de mouvement (tête ou haut du visage), voix plus aiguë, voix plus
               forte, débit plus rapide, expressions plus marquées (haut du visage et
               coins des lèvres) ;
  se retient : figement ou mobilité en baisse, regard détourné, silence long, débit plus
               lent, hésitations.
Dans un passage qui contient un moment atypique, les seuils sont divisés par deux
(FACTEUR_MOMENT) : le moment montre déjà que la personne s'écarte, il reste à dire dans
quel sens. Le silence long demande en plus une pause d'au moins DUREE_SILENCE_LONG
secondes, durée qui n'est pas divisée par deux. Sur un passage sans parole transcrite, débit, silence et hésitations ne sont
pas évalués ; ailleurs, débit et hésitations ne sont lus qu'à l'intérieur des phrases.
Aucun critère atteint : « habituel ». Critères d'un seul sens : ce sens. Les deux sens :
« mixte », sauf si l'un compte au moins MARGE_MIXTE critères de plus. Moins de 30 %
d'images fiables, ou trop peu pour un écart moyen : « non mesuré ».
L'orientation décrit la direction d'un écart, jamais sa cause : s'animer peut traduire
de l'intérêt comme de l'agacement, se retenir de la gêne comme de la concentration.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from . import parole
from .analyse import Mesures
from .rendu import tc
from .signaux import HAUT_VISAGE, HORS_VISAGE, SEUIL_MOMENT, TEMPS_MIN_BASE, UNITES, Signaux

DUREE_MIN, DUREE_MAX = 4.0, 15.0     # secondes : longueur visée d'un passage
DUREE_FIXE = 8.0                     # fenêtres régulières sans transcription
DUREE_PLANCHER = 2.0                 # un passage plus court rejoint son voisin
SILENCE_COUPURE = 0.7                # un silence plus long ferme un passage assez long
SANS_PAROLE = 4.0                    # un silence plus long devient un passage à part
FIN_PHRASE = (".", "?", "!", "…")

# Seuils en dispersions habituelles de la personne, réglés à la main sur une allocution lue
# (58 passages) : 29 % des passages mesurés y sortent de « habituel », dont les 8 passages
# qui contiennent un moment atypique. Sur 4 min d'une déclaration : 26 %.
SEUIL_SIGNAL = 1.5       # voix, débit, mouvement, regard, hésitations
SEUIL_EXPRESSION = 5.0   # unités du haut du visage et coins des lèvres, très asymétriques
SEUIL_SILENCE = 4.0      # silence le plus long du passage
# Durée minimale, en secondes, du plus long silence pour le critère « silence long », jamais
# divisée par FACTEUR_MOMENT : l'échelle de l'écart a un plancher de 0,2 s, si bien qu'une
# pause de 1,3 s y atteignait déjà le seuil.
DUREE_SILENCE_LONG = 2.0
PART_FIGEMENT = 0.25     # part du passage passée en figement
FACTEUR_MOMENT = 0.5     # seuils multipliés par ce facteur si le passage a un moment atypique
MARGE_MIXTE = 2          # critères d'avance pour trancher quand les deux sens sont présents
PART_FIABLE_MIN = 0.3    # en dessous, le passage n'est pas mesuré
# Classement des thèmes : un thème n'y entre qu'avec au moins TEMPS_THEME_MIN secondes et
# PASSAGES_THEME_MIN passages mesurés. 30 s = deux passages de durée maximale (15 s) : aucun
# passage seul ne pèse plus de la moitié du temps du thème, et un « 100 % » demande au moins
# trois passages concordants. En 0.5 (8 s, sans minimum de passages), un thème de 13 s
# (un passage) sortait en tête à 100 %.
TEMPS_THEME_MIN = 30.0   # secondes mesurées
PASSAGES_THEME_MIN = 3   # passages mesurés

ORIENTATIONS = ["s'anime", "se retient", "mixte", "habituel", "non mesuré"]

# Lexique des thèmes : formes régulières, reconnues en mots entiers, sans casse.
THEMES = [
    ("pouvoir d'achat et prix",
     ["pouvoir d'achat", "prix", "inflation", "salaires?", "salaria(?:l|le|les|ux)", "smic",
      "fins? de mois", "vie chère", "coût de la vie", "cherté", "revenus?", "panier",
      "chèques?"]),
    ("énergie et carburants",
     ["énergies?", "énergétiques?", "carburants?", "essence", "gazole", "diesel", "pétrole",
      "pétroli(?:er|ère|ers|ères)", "gaz", "électricité", "nucléaire", "pompes?",
      "raffineries?", "barils?", "opep", "transition énergétique"]),
    ("sécurité et violences",
     ["sécurité", "insécurité", "sécuritaires?", "violences?", "violent(?:e|s|es)?",
      "casseurs?", "délinquan(?:t|ts|te|tes|ce)", "polices?", "policiers?", "policières?",
      "gendarmes?", "gendarmerie", "émeutes?", "émeutiers?", "pillages?", "pillé(?:e|s|es)?",
      "pilleurs?", "factieux", "terroris(?:me|te|tes)", "attentats?", "agressions?",
      "interpell(?:é|ée|és|ées|ation|ations)", "forces de l'ordre", "ordre public",
      "maintien de l'ordre", "rétablir l'ordre", "saccag(?:é|ée|és|ées|es)",
      "ministre de l'intérieur", "ministère de l'intérieur", "ultra-?gauche",
      "ultra-?droite", "groupuscules?", "black blocs?", "couvre-feux?", "préfets? de police"]),
    ("immigration",
     ["immigr(?:ation|é|és|ée|ées|ant|ants)", "migrants?", "migratoires?", "étrangers?",
      "étrangères?", "frontières?", "asile", "clandestins?", "titres? de séjour",
      "régularisations?", "expulsions?", "oqtf", "naturalisations?"]),
    ("éducation et jeunesse",
     ["écoles?", "éducation", "éducati(?:f|fs|ve|ves)", "élèves?", "enseignant(?:e|s|es)?",
      "professeurs?", "lycées?", "lycéens?", "collèges?", "collégiens?", "universités?",
      "étudiant(?:e|s|es)?", "études", "jeunesse", "jeunes", "apprentissage", "apprentis",
      "baccalauréat", "scolaires?", "parcoursup"]),
    ("santé",
     ["santé", "hôpita(?:l|ux)", "médecins?", "soignants?", "infirmi(?:er|ère|ers|ères)",
      "malades?", "maladies?", "soins", "sécurité sociale", "pandémie", "covid", "vaccins?",
      "médicaments?", "déserts? médica(?:l|ux)"]),
    ("retraites",
     ["retraites?", "retraités?", "pensions?", "âge de départ", "cotisations?",
      "régimes? spéciaux"]),
    ("emploi et économie",
     ["emplois?", "chômage", "chômeurs?", "travail", "travailleurs?", "entreprises?",
      "entrepreneurs?", "économie", "économiques?", "croissance", "industries?",
      "industriel(?:le|s|les)?", "usines?", "embauches?", "commerces?", "commerçants?",
      "artisans?", "pme", "investissements?", "compétitivité"]),
    ("impôts et dette",
     ["impôts?", "fisca(?:l|le|les|ux|lité)", "taxes?", "dettes?", "déficits?", "budgets?",
      "budgétaires?", "dépenses? publiques?", "tva", "contribuables?", "prélèvements?",
      "finances publiques"]),
    ("écologie",
     ["écologie", "écologiques?", "climat", "climatiques?", "environnement",
      "environnementa(?:l|le|les|ux)", "biodiversité", "pollutions?", "carbone",
      "réchauffement", "renouvelables?", "transition écologique"]),
    ("international et défense",
     ["guerres?", "armées?", "militaires?", "défense", "ukraine", "russie", "golfe", "iran",
      "israël", "gaza", "europe", "européen(?:ne|s|nes)?", "internationa(?:l|le|les|ux)",
      "diplomati(?:e|que|ques)", "otan", "conflits?", "alliés?", "belligérants?", "chine",
      "états-unis", "arabie", "moyen-orient", "frappes?", "ormuz"]),
    ("institutions et élection",
     ["républiques?", "républicain(?:e|s|es)?", "élections?", "électora(?:l|le|les|ux)",
      "présidentielles?", "votes?", "voter", "scrutins?", "démocraties?", "démocratiques?",
      "assemblée", "parlement", "parlementaires?", "sénat", "sénateurs?", "députés?",
      "gouvernements?", "premier ministre", "ministres?", "constitution",
      "constitutionnel(?:le|s|les)?", "institutions?", "partis", "parti politique",
      "référendum", "dissolution"]),
    ("justice",
     ["justice", "juges?", "judiciaires?", "judiciarisation", "tribuna(?:l|ux)", "procès",
      "condamn(?:é|ée|és|ées|ation|ations)", "peines? de prison", "prisons?", "impunité",
      "enquêtes?", "enquêteurs?", "procureurs?", "garde des sceaux", "magistrats?",
      "ministre de la justice", "sanctionn(?:er|é|és|ée|ées)"]),
    ("logement",
     ["logements?", "loyers?", "locataires?", "propriétaires?", "immobili(?:er|ère|ers)",
      "hlm", "sans-abri", "hébergement", "sans domicile"]),
    ("agriculture",
     ["agricultu(?:re|res)", "agriculteurs?", "agricoles?", "paysans?", "éleveurs?",
      "élevages?", "exploitations? agricoles?", "pac", "récoltes?", "alimentaires?"]),
]
_MOTIFS = [(nom, re.compile(r"\b(?:" + "|".join(formes) + r")\b", re.IGNORECASE))
           for nom, formes in THEMES]
AUTRES_VIDES = {"voilà", "chose", "choses", "veux", "voulons", "allons", "avons", "beaucoup",
                "moins", "enfin", "vraiment", "justement", "évidemment", "effectivement",
                "toujours", "jamais", "rien", "personne", "certain", "certaine", "certains",
                "fois", "ceci", "celui-ci", "celle-ci", "était", "avait", "pourquoi", "comment",
                "est-à-dire", "soit", "quel", "quelle", "quels", "quelles"}

FAMILLES = {
    "Visage": [f"{c} {lib}" for c, lib, _ in UNITES if c not in HORS_VISAGE],
    "Mobilité": ["Mouvements de tête", "Mobilité du haut du visage"],
    "Regard": ["Regard détourné", "Clignements"],
    "Voix": ["Hauteur de la voix", "Énergie de la voix"],
    "Parole": ["Débit de parole", "Silence", "Hésitations"],
}
MOUVEMENT = FAMILLES["Mobilité"]
PAROLE = FAMILLES["Parole"]
VOIX = FAMILLES["Voix"]
# Pour qui écoute, seuls le visage, la mobilité et le regard comptent.
CRITERES_ECOUTE = ("plus de mouvement", "expressions plus marquées",
                   "figement ou mobilité en baisse", "regard détourné")
ROLES_ECOUTE = ("écoute", "parole non attribuée")
EXPRESSIVES = [f"{c} {lib}" for c, lib, _ in UNITES if c in HAUT_VISAGE or c == "AU12"]
# Signal -> (en mots quand il monte, en mots quand il baisse).
MOTS = {
    "AU1 Sourcils intérieurs levés": ("sourcils levés", "sourcils moins levés"),
    "AU2 Sourcils extérieurs levés": ("sourcils extérieurs levés",
                                      "sourcils extérieurs moins levés"),
    "AU4 Sourcils froncés": ("sourcils froncés", "sourcils moins froncés"),
    "AU5 Yeux écarquillés": ("yeux écarquillés", "yeux moins ouverts"),
    "AU6 Joues remontées": ("joues remontées", "joues moins remontées"),
    "AU7 Paupières plissées": ("paupières plissées", "paupières moins plissées"),
    "AU9 Nez plissé": ("nez plissé", "nez moins plissé"),
    "AU10 Lèvre supérieure levée": ("lèvre supérieure levée", "lèvre supérieure moins levée"),
    "AU12 Coins des lèvres tirés": ("coins des lèvres tirés", "coins des lèvres moins tirés"),
    "AU14 Lèvres serrées en coin": ("lèvres serrées en coin", "lèvres moins serrées en coin"),
    "AU15 Coins des lèvres abaissés": ("coins des lèvres abaissés",
                                       "coins des lèvres moins abaissés"),
    "AU17 Menton relevé": ("menton relevé", "menton moins relevé"),
    "AU20 Lèvres étirées": ("lèvres étirées", "lèvres moins étirées"),
    "AU24 Lèvres pressées": ("lèvres pressées", "lèvres moins pressées"),
    "AU28 Lèvres rentrées": ("lèvres rentrées", "lèvres moins rentrées"),
    "Mouvements de tête": ("tête plus mobile", "tête moins mobile"),
    "Mobilité du haut du visage": ("haut du visage plus mobile", "haut du visage moins mobile"),
    "Regard détourné": ("regard détourné", "regard plus fixe"),
    "Clignements": ("clignements plus fréquents", "clignements plus rares"),
    "Hauteur de la voix": ("voix plus aiguë", "voix plus grave"),
    "Énergie de la voix": ("voix plus forte", "voix plus faible"),
    "Débit de parole": ("débit plus rapide", "débit plus lent"),
    "Silence": ("silence long", "silences courts"),
    "Hésitations": ("plus d'hésitations", "moins d'hésitations"),
}
NOTABLE = 0.5            # en dessous, le signal principal d'un canal est dit habituel


def _nombre(x: float, signe: bool = True) -> str:
    return (f"{x:+.1f}" if signe else f"{x:.1f}").replace(".", ",")


def _mot(signal: str, z: float) -> str:
    haut, bas = MOTS.get(signal, (signal.lower(), signal.lower()))
    return haut if z >= 0 else bas


# --- Passages ---------------------------------------------------------------------------

def _joindre(mots) -> str:
    """Recolle les mots de la transcription (« l » + « 'office » -> « l'office »)."""
    texte = ""
    for w in mots:
        texte += w if texte and w[:1] in "'’-" else (" " + w if texte else w)
    return texte


def _scinder(phrase: dict, mots: list) -> list:
    """Coupe une phrase trop longue sur ses mots : ponctuation ou silence près du milieu."""
    dedans = [w for w in mots if phrase["debut"] <= (w["debut"] + w["fin"]) / 2 <= phrase["fin"]]
    if phrase["fin"] - phrase["debut"] <= DUREE_MAX or len(dedans) < 4:
        return [phrase]
    milieu = (phrase["debut"] + phrase["fin"]) / 2

    def score(k):
        w, suivant = dedans[k], dedans[k + 1]
        if w["fin"] - phrase["debut"] < DUREE_PLANCHER or phrase["fin"] - suivant["debut"] \
                < DUREE_PLANCHER:
            return -100.0
        ponctuation = 2.0 if w["mot"].endswith(FIN_PHRASE) else \
            1.0 if w["mot"].endswith((",", ";", ":")) else 0.0
        return ponctuation + 4 * (suivant["debut"] - w["fin"]) - abs(w["fin"] - milieu) / 4
    k = max(range(len(dedans) - 1), key=score)
    if score(k) <= -100:                # aucune coupe ne laisse 2 s de chaque côté
        return [phrase]
    gauche = {"debut": phrase["debut"], "fin": dedans[k]["fin"],
              "texte": _joindre(w["mot"] for w in dedans[:k + 1])}
    droite = {"debut": dedans[k + 1]["debut"], "fin": phrase["fin"],
              "texte": _joindre(w["mot"] for w in dedans[k + 1:])}
    return _scinder(gauche, mots) + _scinder(droite, mots)


def _fusion(a: dict, b: dict, texte: str) -> dict:
    """Deux morceaux réunis ; dans un débat, le locuteur est celui qui y parle le plus longtemps."""
    sortie = {"debut": a["debut"], "fin": b["fin"], "texte": texte}
    if "parole_par_locuteur" in a or "parole_par_locuteur" in b:
        temps = dict(a.get("parole_par_locuteur", {}))
        for qui, duree in b.get("parole_par_locuteur", {}).items():
            temps[qui] = temps.get(qui, 0.0) + duree
        sortie["parole_par_locuteur"] = temps
        sortie["locuteur"] = max(temps, key=temps.get) if temps else None
    return sortie


def _regrouper(phrases: list) -> list:
    """Assemble les phrases jusqu'à 4 s au moins, coupe sur une fin de phrase ou un silence,
    et, dans un débat, à chaque changement de locuteur."""
    groupes, cour = [], None
    for p in phrases:
        if cour is None:
            cour = dict(p)
            continue
        silence, duree = p["debut"] - cour["fin"], cour["fin"] - cour["debut"]
        fin_nette = cour["texte"].rstrip().endswith(FIN_PHRASE) or silence >= SILENCE_COUPURE
        if p["fin"] - cour["debut"] > DUREE_MAX or silence >= SANS_PAROLE \
                or (duree >= DUREE_MIN and fin_nette) or cour.get("locuteur") != p.get("locuteur"):
            groupes.append(cour)
            cour = dict(p)
        else:
            cour = _fusion(cour, p, cour["texte"] + " " + p["texte"])
    if cour:
        groupes.append(cour)
    return groupes


def _fenetres(a: float, b: float) -> list:
    """Fenêtres régulières d'environ 8 s entre a et b (sans transcription ou sans parole)."""
    k = max(1, int(round((b - a) / DUREE_FIXE)))
    bornes = np.linspace(a, b, k + 1)
    return [{"debut": float(x), "fin": float(y), "texte": ""}
            for x, y in zip(bornes[:-1], bornes[1:])]


def _couvrir(groupes: list, duree: float) -> list:
    """Couvre toute la durée : un silence court rejoint le passage qui le précède, un
    silence long devient un passage sans parole."""
    sortie, t = [], 0.0
    for g in groupes:
        g = dict(g, debut=max(g["debut"], t))
        if g["fin"] <= g["debut"]:
            continue
        if g["debut"] - t >= SANS_PAROLE:
            sortie += _fenetres(t, g["debut"])
        elif sortie:
            sortie[-1]["fin"] = g["debut"]
        else:
            g["debut"] = 0.0
        sortie.append(g)
        t = g["fin"]
    if not sortie:
        return _fenetres(0.0, duree)
    if duree - t >= SANS_PAROLE:
        sortie += _fenetres(t, duree)
    else:
        sortie[-1]["fin"] = duree
    # Un passage trop court rejoint son voisin (le précédent, sinon le suivant).
    k = 0
    while k < len(sortie) and len(sortie) > 1:
        if sortie[k]["fin"] - sortie[k]["debut"] >= DUREE_PLANCHER:
            k += 1
            continue
        j = max(k - 1, 0)                 # la paire fusionnée : (j, j + 1)
        a, b = sortie[j], sortie[j + 1]
        sortie[j:j + 2] = [_fusion(a, b, (a["texte"] + " " + b["texte"]).strip())]
        k = j
    return sortie


def morceaux_de(transcription: dict | None, duree: float) -> list:
    """Les phrases transcrites dans l'extrait, les plus longues coupées (au plus 15 s)."""
    phrases = sorted((p for p in (transcription or {}).get("phrases", [])
                      if p["texte"].strip() and p["fin"] > 0 and p["debut"] < duree),
                     key=lambda p: p["debut"])
    mots = (transcription or {}).get("mots", [])
    return [q for p in phrases for q in _scinder(
        {"debut": max(0.0, p["debut"]), "fin": min(duree, p["fin"]), "texte": p["texte"].strip()},
        mots)]


def decouper(transcription: dict | None, duree: float, locuteur=None) -> list:
    """Passages {debut, fin, texte} en secondes depuis le début de l'extrait, sans trou.

    `locuteur` (débat) : fonction (début, fin) -> qui parle sur ce morceau de phrase. Les
    passages sont alors coupés à chaque changement de locuteur et portent la clé « locuteur »."""
    morceaux = morceaux_de(transcription, duree)
    if not morceaux:
        return _fenetres(0.0, duree)
    if locuteur is not None:
        for q in morceaux:
            q["locuteur"] = locuteur(q["debut"], q["fin"])
            q["parole_par_locuteur"] = {q["locuteur"]: q["fin"] - q["debut"]}
    return _couvrir(_regrouper(morceaux), duree)


# --- Ce qui est dit ---------------------------------------------------------------------

def themes_de(texte: str) -> list:
    """Un ou deux thèmes reconnus par le lexique ; la forme la plus longue l'emporte."""
    texte = texte.lower().replace("’", "'")
    trouves = sorted((r.start(), r.start() - r.end(), nom)
                     for nom, motif in _MOTIFS for r in motif.finditer(texte))
    compte, premier, fin = Counter(), {}, -1
    for debut, moins_longueur, nom in trouves:
        if debut < fin:
            continue
        fin = debut - moins_longueur
        compte[nom] += 1
        premier.setdefault(nom, debut)
    ordre = sorted(compte, key=lambda nom: (-compte[nom], premier[nom]))
    if len(ordre) >= 2 and 2 * compte[ordre[1]] < compte[ordre[0]]:
        ordre = ordre[:1]
    return ordre[:2]


def _jetons(texte: str) -> list:
    return [j for j in parole.MOT.findall(texte.lower().replace("’", "'"))
            if len(j) > 3 and not j[0].isdigit() and not j.endswith("'")
            and j not in parole.VIDES and j not in parole.HESITATIONS and j not in AUTRES_VIDES]


def _decrire(passages: list) -> None:
    """Ajoute à chaque passage : thèmes, mots distinctifs, chiffre cité, sujet affiché."""
    jetons = [_jetons(p["texte"]) for p in passages]
    df = Counter(j for js in jetons for j in set(js))
    nb = len(passages)
    for p, js in zip(passages, jetons):
        tf = Counter(js)
        rang = sorted(tf, key=lambda j: (-tf[j] * math.log((1 + nb) / df[j]), js.index(j)))
        p["themes"] = themes_de(p["texte"])
        p["mots_distinctifs"] = rang[:3]
        p["chiffre"] = bool(parole.CHIFFRE.search(p["texte"]))
        p["sujet"] = ", ".join(p["themes"] or p["mots_distinctifs"])


# --- Ce que montrent les mesures --------------------------------------------------------

def _moyenne(x: np.ndarray, masque: np.ndarray) -> float:
    v = x[masque & np.isfinite(x)]
    return float(v.mean()) if v.size and v.size >= max(5, 0.2 * masque.sum()) else float("nan")


def _maximum(x: np.ndarray, masque: np.ndarray) -> float:
    v = x[masque & np.isfinite(x)]
    return float(v.max()) if v.size else float("nan")


def _arrondi(x: float, k: int = 1):
    return None if not np.isfinite(x) else round(float(x), k)


def _mesurer(p: dict, s: Signaux, fps: float, ecarts_tries: np.ndarray,
             dans_phrase: np.ndarray, ecoute: bool = False) -> dict:
    i0, i1 = p["image_debut"], p["image_fin"]
    masque = np.zeros(len(s.ok), bool)
    masque[i0:i1] = s.ok[i0:i1]
    # Le débit et les hésitations sont calculés sur des fenêtres glissantes qui débordent
    # sur les silences voisins : on ne les lit qu'à l'intérieur des phrases, et pas du tout
    # sur un passage sans parole transcrite. Pour qui écoute, ni voix ni parole.
    dit = bool(p["texte"]) and not ecoute
    parle = masque & dans_phrase if dit else np.zeros_like(masque)
    valeurs = {}
    for nom, z in s.details.items():
        if ecoute and nom in VOIX + PAROLE:
            valeurs[nom] = float("nan")
        elif nom == "Silence":
            valeurs[nom] = _maximum(z, masque) if dit else float("nan")
        else:
            valeurs[nom] = _moyenne(z, parle if nom in PAROLE else masque)
    ecart = _moyenne(s.ecart, masque)
    rang = float("nan")
    if np.isfinite(ecart) and ecarts_tries.size:
        rang = 100.0 * np.searchsorted(ecarts_tries, ecart) / ecarts_tries.size
    principal = {}
    for famille, noms in FAMILLES.items():
        presents = [(abs(valeurs[n]), n) for n in noms
                    if famille in s.groupes and np.isfinite(valeurs.get(n, np.nan))]
        if presents:
            nom = max(presents)[1]
            principal[famille] = {"signal": nom, "en_mots": _mot(nom, valeurs[nom]),
                                  "z": _arrondi(valeurs[nom])}
    forts = sorted(((n, z) for n, z in valeurs.items() if np.isfinite(z)),
                   key=lambda c: -abs(c[1]))[:3]
    with np.errstate(invalid="ignore"):
        debit = s.debit[parle & (s.debit > 0)]
    debit_habituel = s.base.get("debit_mots_par_seconde")
    pauses = s.pause[masque & np.isfinite(s.pause)] if dit else np.array([])
    return {
        "images_fiables_pct": round(100.0 * masque.sum() / max(i1 - i0, 1), 1),
        "images_fiables": int(masque.sum()),
        "ecart_moyen": _arrondi(ecart, 2),
        "ecart_max": _arrondi(_maximum(s.ecart, masque), 2),
        "rang_pct": _arrondi(rang, 0),
        "familles": {f: None if ecoute and f in ("Voix", "Parole")
                     else _arrondi(_moyenne(g, parle if f == "Parole" else masque), 2)
                     for f, g in s.groupes.items()},
        "principal": principal,
        "signaux": [{"nom": n, "en_mots": _mot(n, z), "z": round(z, 1)} for n, z in forts],
        "moments_atypiques": [k + 1 for k, mo in enumerate(s.moments) if i0 <= mo["image"] < i1],
        "figement_s": round(sum(max(0, min(f["fin"], i1) - max(f["image"], i0))
                                for f in s.figements) / fps, 1),
        "ecart_simultane": sorted({c for cv in s.convergences
                                   if cv["image"] < i1 and cv["fin"] > i0 for c in cv["canaux"]}),
        "debit_mots_s": _arrondi(float(debit.mean()) if debit.size else np.nan, 2),
        "debit_habituel_mots_s": debit_habituel,
        "silence_max_s": _arrondi(float(pauses.max()) if pauses.size else np.nan),
        "_valeurs": valeurs,
    }


# --- Orientation et lecture -------------------------------------------------------------

def _critere(sens, nom, signal, valeur, seuil, atteint, en_mots) -> dict:
    return {"sens": sens, "critere": nom, "signal": signal, "valeur": _arrondi(valeur),
            "seuil": seuil, "atteint": bool(atteint), "en_mots": en_mots}


def _criteres(mesures: dict, duree: float, ecoute: bool = False) -> list:
    v = mesures["_valeurs"]

    def le_plus(noms, signe):
        presents = [(signe * v[n], n) for n in noms if np.isfinite(v.get(n, np.nan))]
        return max(presents)[1] if presents else None

    def val(nom):
        return v.get(nom, np.nan) if nom else np.nan
    # Un moment atypique dans le passage : seuils divisés par deux, pour lui donner un sens.
    facteur = FACTEUR_MOMENT if mesures["moments_atypiques"] else 1.0
    sig, exp_, sil = (round(x * facteur, 2) for x in (SEUIL_SIGNAL, SEUIL_EXPRESSION,
                                                       SEUIL_SILENCE))
    with np.errstate(invalid="ignore"):
        bouge, fige, expr = le_plus(MOUVEMENT, 1), le_plus(MOUVEMENT, -1), le_plus(EXPRESSIVES, 1)
        part_figee = mesures["figement_s"] / max(duree, 1e-6)
        silence = val("Silence")
        silence_long = (silence >= sil
                        and (mesures["silence_max_s"] or 0) >= DUREE_SILENCE_LONG)
        liste = [
            _critere("s'anime", "plus de mouvement", bouge, val(bouge), sig,
                     val(bouge) >= sig, _mot(bouge, 1) if bouge else ""),
            _critere("s'anime", "voix plus aiguë", "Hauteur de la voix", val("Hauteur de la voix"),
                     sig, val("Hauteur de la voix") >= sig, "voix plus aiguë"),
            _critere("s'anime", "voix plus forte", "Énergie de la voix", val("Énergie de la voix"),
                     sig, val("Énergie de la voix") >= sig, "voix plus forte"),
            _critere("s'anime", "débit plus rapide", "Débit de parole", val("Débit de parole"),
                     sig, val("Débit de parole") >= sig, "débit plus rapide"),
            _critere("s'anime", "expressions plus marquées", expr, val(expr), exp_,
                     val(expr) >= exp_, _mot(expr, 1) if expr else ""),
            _critere("se retient", "figement ou mobilité en baisse", fige, val(fige),
                     -sig, part_figee >= PART_FIGEMENT or val(fige) <= -sig,
                     f"figement de {_nombre(mesures['figement_s'], False)} s"
                     if part_figee >= PART_FIGEMENT else _mot(fige, -1) if fige else ""),
            _critere("se retient", "regard détourné", "Regard détourné", val("Regard détourné"),
                     sig, val("Regard détourné") >= sig, "regard détourné"),
            _critere("se retient", "silence long", "Silence", silence, sil, silence_long,
                     f"silence de {_nombre(mesures['silence_max_s'] or 0, False)} s"),
            _critere("se retient", "débit plus lent", "Débit de parole", val("Débit de parole"),
                     -sig, val("Débit de parole") <= -sig, "débit plus lent"),
            _critere("se retient", "hésitations", "Hésitations", val("Hésitations"),
                     sig, val("Hésitations") >= sig, "plus d'hésitations"),
        ]
    liste[5]["figement_pct"] = round(100 * part_figee)
    if ecoute:
        liste = [c for c in liste if c["critere"] in CRITERES_ECOUTE]
    return liste


def _orienter(criteres: list, mesures: dict) -> str:
    # Trop peu d'images fiables (en part ou en nombre) : pas d'écart moyen, pas de classement.
    if mesures["images_fiables_pct"] < 100 * PART_FIABLE_MIN or mesures["ecart_moyen"] is None:
        return "non mesuré"
    anime = sum(c["atteint"] for c in criteres if c["sens"] == "s'anime")
    retient = sum(c["atteint"] for c in criteres if c["sens"] == "se retient")
    if not anime and not retient:
        return "habituel"
    if not retient or anime - retient >= MARGE_MIXTE:
        return "s'anime"
    if not anime or retient - anime >= MARGE_MIXTE:
        return "se retient"
    return "mixte"


def _citer(c: dict) -> str:
    texte = c["en_mots"]
    if c["critere"] in ("silence long",) or texte.startswith("figement"):
        return texte
    return f"{texte} ({_nombre(c['valeur'])})"


def _constat(p: dict, qui: str = "la personne", role: str | None = None) -> str:
    o, mes = p["orientation"], p["mesures"]
    if o == "non mesuré":
        return "Visage non mesurable sur ce passage."
    if o == "habituel":
        return "Rien d'inhabituel sur ce passage."
    atteints = [c for c in p["criteres"] if c["atteint"]]
    atteints.sort(key=lambda c: -abs(c["valeur"] or 0))
    if o == "mixte":
        retenus = [c for c in atteints if c["sens"] == "s'anime"][:2] \
            + [c for c in atteints if c["sens"] == "se retient"][:2]
    else:
        retenus = [c for c in atteints if c["sens"] == o][:3]
    liste = ", ".join(_citer(c) for c in retenus)
    suite = {"s'anime": f"{qui} s'anime", "se retient": f"{qui} se retient",
             "mixte": "signaux dans les deux sens"}[o]
    if role == "écoute" and o != "mixte":
        suite += " en écoutant"
    phrase = f"{liste[:1].upper()}{liste[1:]} : {suite}."
    if mes["ecart_moyen"] is not None:
        phrase += f" Écart {_nombre(mes['ecart_moyen'], False)}"
        if mes["rang_pct"] is not None:
            phrase += f", plus élevé que {mes['rang_pct']:.0f} % de la vidéo"
        phrase += "."
    return phrase


def _lire(p: dict, transcription: bool) -> str:
    if p["themes"]:
        sujet = "Sujet : " + ", ".join(p["themes"]) + ". "
    elif p["mots_distinctifs"]:
        sujet = "Mots marquants : " + ", ".join(p["mots_distinctifs"]) + ". "
    else:
        sujet = "Pas de parole transcrite. " if transcription else ""
    return sujet + p["constat"]


# --- Synthèse sur la vidéo --------------------------------------------------------------

def synthese(passages: list, s: Signaux) -> dict:
    """Par thème : temps de parole, écart, part au-dessus du seuil, orientation dominante."""
    themes = {}
    for nom in dict.fromkeys(t for p in passages for t in p["themes"]):
        lies = [p for p in passages if nom in p["themes"]]
        masque = np.zeros(len(s.ok), bool)
        temps = Counter()
        for p in lies:
            masque[p["image_debut"]:p["image_fin"]] = s.ok[p["image_debut"]:p["image_fin"]]
            temps[p["orientation"]] += p["duree_s"]
        total = sum(temps.values())
        mesure = masque & np.isfinite(s.ecart)
        mesures = {o: d for o, d in temps.items() if o != "non mesuré"}
        marques = {o: d for o, d in mesures.items() if o != "habituel"}
        temps_mesure = max(sum(mesures.values()), 1e-6)
        nb_mesures = sum(p["orientation"] != "non mesuré" for p in lies)
        themes[nom] = {
            "temps_s": round(total, 1),
            "temps_mesure_s": round(sum(mesures.values()), 1),
            "passages": len(lies),
            "passages_mesures": nb_mesures,
            "ecart_moyen": _arrondi(float(s.ecart[mesure].mean()) if mesure.any() else np.nan, 2),
            "au_dessus_du_seuil_pct": _arrondi(100.0 * float((s.ecart[mesure] > SEUIL_MOMENT)
                                                             .mean()) if mesure.any() else np.nan, 0),
            "orientation_dominante": max(mesures, key=mesures.get) if mesures else "non mesuré",
            "temps_par_orientation_s": {o: round(d, 1) for o, d in temps.items()},
            "temps_marque_pct": round(100.0 * sum(marques.values()) / temps_mesure),
            # Hors « habituel » : l'orientation la plus fréquente et sa part du temps mesuré.
            "orientation_marquee": max(marques, key=marques.get) if marques
            else "habituel" if mesures else "non mesuré",
            "orientation_marquee_pct": round(100.0 * max(marques.values(), default=0)
                                             / temps_mesure),
        }
    # Thèmes les plus marqués : part du temps de l'orientation marquée, puis écart moyen.
    # Seuls les thèmes assez longs (TEMPS_THEME_MIN s et PASSAGES_THEME_MIN passages mesurés)
    # y entrent ; les autres restent dans « themes » avec la raison.
    assez = []
    for n, t in themes.items():
        if t["temps_mesure_s"] >= TEMPS_THEME_MIN and t["passages_mesures"] >= PASSAGES_THEME_MIN:
            t["classe"] = True
            assez.append(n)
        else:
            t["classe"] = False
            t["hors_classement"] = (
                f"trop court pour le classement : {_nombre(t['temps_mesure_s'], False)} s "
                f"mesurées en {t['passages_mesures']} passage"
                f"{'s' if t['passages_mesures'] > 1 else ''} (minimum "
                f"{TEMPS_THEME_MIN:.0f} s et {PASSAGES_THEME_MIN} passages)")
    classement = sorted(assez, key=lambda n: (-themes[n]["orientation_marquee_pct"],
                                              -(themes[n]["ecart_moyen"] or 0)))

    def plus_marques(sens):
        liste = []
        for n in assez:
            part = themes[n]["temps_par_orientation_s"].get(sens, 0) / themes[n]["temps_mesure_s"]
            if part > 0:
                liste.append({"theme": n, "part_pct": round(100 * part),
                              "temps_s": themes[n]["temps_s"],
                              "ecart_moyen": themes[n]["ecart_moyen"]})
        return sorted(liste, key=lambda t: (-t["part_pct"], -(t["ecart_moyen"] or 0)))

    mesures = [p for p in passages if p["orientation"] != "non mesuré"]
    marques = sorted(mesures, key=lambda p: -p["mesures"]["ecart_moyen"])[:5]
    repartition = Counter(p["orientation"] for p in passages)
    return {
        "passages": len(passages),
        "repartition": {o: repartition.get(o, 0) for o in ORIENTATIONS},
        "themes": themes,
        "regle_du_classement": f"thèmes d'au moins {TEMPS_THEME_MIN:.0f} s et "
                               f"{PASSAGES_THEME_MIN} passages mesurés ; "
                               f"{len(themes) - len(assez)} thème(s) sur {len(themes)} "
                               "hors classement (voir « hors_classement »)",
        "classement": [{"theme": n, "orientation": themes[n]["orientation_marquee"],
                        "part_pct": themes[n]["orientation_marquee_pct"],
                        "ecart_moyen": themes[n]["ecart_moyen"], "temps_s": themes[n]["temps_s"]}
                       for n in classement],
        "plus_marques": {"s'anime": plus_marques("s'anime"),
                         "se retient": plus_marques("se retient")},
        "passages_marques": [{"temps": p["temps"], "debut_s": p["debut_s"], "fin_s": p["fin_s"],
                              "orientation": p["orientation"],
                              "ecart_moyen": p["mesures"]["ecart_moyen"],
                              "rang_pct": p["mesures"]["rang_pct"], "sujet": p["sujet"],
                              "lecture": p["lecture"]} for p in marques],
    }


def regle() -> dict:
    """La règle d'orientation en clair, avec ses seuils, pour le rapport."""
    s, e, sil = _nombre(SEUIL_SIGNAL), _nombre(SEUIL_EXPRESSION), _nombre(SEUIL_SILENCE)
    return {
        "unite": "écart signé à l'habitude de la personne (en dispersions), moyenné sur les "
                 "images fiables du passage ; pour le silence, le plus long du passage",
        "s'anime": [f"plus de mouvement de la tête ou du haut du visage >= {s}",
                    f"voix plus aiguë >= {s}", f"voix plus forte >= {s}",
                    f"débit plus rapide >= {s}",
                    f"expressions plus marquées (haut du visage, coins des lèvres) >= {e}"],
        "se retient": [f"figement sur au moins {PART_FIGEMENT:.0%} du passage, ou mobilité "
                       f"de la tête ou du haut du visage <= -{s[1:]}",
                       f"regard détourné >= {s}", f"silence long >= {sil} et plus long silence d'au moins "
                       f"{_nombre(DUREE_SILENCE_LONG, False)} s",
                       f"débit plus lent <= -{s[1:]}", f"hésitations >= {s}"],
        "moment_atypique": f"seuils multipliés par {_nombre(FACTEUR_MOMENT, False)} dans un "
                           "passage qui contient un moment atypique (le seuil appliqué est "
                           "écrit dans chaque critère) ; la durée minimale du silence long "
                           "n'est pas réduite",
        "parole": "sur un passage sans parole transcrite, débit, silence et hésitations ne "
                  "sont pas évalués ; ailleurs, débit et hésitations ne sont lus qu'à "
                  "l'intérieur des phrases",
        "classement": "habituel si aucun critère n'est atteint ; s'anime ou se retient si "
                      "les critères atteints sont d'un seul sens, ou si l'un des sens en "
                      f"compte au moins {MARGE_MIXTE} de plus ; mixte sinon ; non mesuré sous "
                      f"{PART_FIABLE_MIN:.0%} d'images fiables ou sans écart moyen calculable",
        "classement_des_themes": f"un thème n'entre au classement (« classement », "
                                 f"« plus_marques ») qu'avec au moins {TEMPS_THEME_MIN:.0f} s "
                                 f"et {PASSAGES_THEME_MIN} passages mesurés ; sinon il reste "
                                 "dans « themes » avec la mention « hors_classement »",
        "ligne_de_base": "une personne : habitude sur toute la vidéo ; débat : habitude de la "
                         "personne dans son rôle (quand elle parle, quand elle écoute), "
                         "figement compris, avec repli sur l'habitude globale si un rôle a "
                         f"moins de {TEMPS_MIN_BASE:.0f} s d'images fiables",
        "avertissement": "L'orientation décrit la direction d'un écart, pas sa cause. Seuils "
                         "réglés à la main, non validés sur des extraits annotés.",
    }


def passages_de_base(m: Mesures, transcription: dict | None, locuteur=None) -> list:
    """Passages découpés et décrits (ce qui est dit), sans les mesures. Avec `locuteur`
    (débat), chaque passage porte aussi « locuteur »."""
    passages = decouper(transcription, m.n / m.fps, locuteur)
    _decrire(passages)
    for p in passages:
        p["image_debut"] = min(m.n, int(round(p["debut"] * m.fps)))
        p["image_fin"] = min(m.n, int(round(p["fin"] * m.fps)))
    passages[-1]["image_fin"] = m.n
    sortie = []
    for p in passages:
        duree = (p["image_fin"] - p["image_debut"]) / m.fps
        q = {"temps": tc(m.debut + p["debut"]), "debut_s": round(m.debut + p["debut"], 2),
             "fin_s": round(m.debut + p["fin"], 2), "duree_s": round(duree, 1),
             "image_debut": p["image_debut"], "image_fin": p["image_fin"],
             "texte": p["texte"], "themes": p["themes"],
             "mots_distinctifs": p["mots_distinctifs"], "chiffre": p["chiffre"],
             "sujet": p["sujet"]}
        if locuteur is not None:
            q["locuteur"] = p.get("locuteur")
        sortie.append(q)
    return sortie


def _dans_phrases(m: Mesures, transcription: dict | None) -> np.ndarray:
    dans_phrase = np.zeros(m.n, bool)
    for phrase in (transcription or {}).get("phrases", []):
        dans_phrase[(m.t >= phrase["debut"]) & (m.t <= phrase["fin"])] = True
    return dans_phrase


def _evaluer(q: dict, s: Signaux, fps: float, ecarts_tries: np.ndarray,
             dans_phrase: np.ndarray, transcrit: bool, qui: str = "la personne",
             role: str | None = None) -> dict:
    """Ajoute à un passage ses mesures, ses critères, son orientation et sa lecture."""
    duree = (q["image_fin"] - q["image_debut"]) / fps
    ecoute = role in ROLES_ECOUTE
    mesures = _mesurer(q, s, fps, ecarts_tries, dans_phrase, ecoute)
    q["criteres"] = _criteres(mesures, duree, ecoute)
    q["orientation"] = _orienter(q["criteres"], mesures)
    del mesures["_valeurs"]
    q["mesures"] = mesures
    q["constat"] = _constat(q, qui, role)
    q["lecture"] = _lire(q, transcrit)
    return q


def croiser(m: Mesures, s: Signaux, transcription: dict | None = None) -> dict:
    """Passages, synthèse et règle. Temps en secondes vidéo (début de l'extrait compris)."""
    transcription = transcription if transcription is not None else s.transcription
    ecarts_tries = np.sort(s.ecart[np.isfinite(s.ecart)])
    dans_phrase = _dans_phrases(m, transcription)
    sortie = [_evaluer(q, s, m.fps, ecarts_tries, dans_phrase, bool(transcription))
              for q in passages_de_base(m, transcription)]
    return {"passages": sortie, "synthese": synthese(sortie, s), "regle": regle()}


def croiser_personne(m: Mesures, s: Signaux, choisis: list, transcription: dict | None,
                     transcrit: bool, qui: str) -> dict:
    """Croisement d'une personne d'un débat, avec sa propre ligne de base.

    `choisis` : [(numéro du passage commun, passage de base, rôle)], rôle « parle »,
    « écoute », « parole non attribuée », « sans parole » ou « non déterminé ». Pour qui
    écoute, seuls le visage, la mobilité et le regard comptent. `transcription` : la parole
    attribuée à cette personne."""
    ecarts_tries = np.sort(s.ecart[np.isfinite(s.ecart)])
    dans_phrase = _dans_phrases(m, transcription)
    passages = [_evaluer(dict(base, numero=k, role=role), s, m.fps, ecarts_tries, dans_phrase,
                         transcrit, qui, role) for k, base, role in choisis]
    return {"passages": passages,
            "synthese": {"en_parlant": synthese([p for p in passages if p["role"] == "parle"], s),
                         "en_ecoutant": synthese([p for p in passages if p["role"] == "écoute"],
                                                 s)},
            "regle": regle()}


def passage_vide(base: dict, constat: str, role: str | None = None) -> dict:
    """Un passage sans mesure (personne absente ou sans assez de données), pour l'affichage."""
    q = dict(base, role=role, criteres=[], orientation="non mesuré", constat=constat,
             lecture=constat)
    q["mesures"] = {"images_fiables_pct": 0.0, "images_fiables": 0, "ecart_moyen": None,
                    "ecart_max": None, "rang_pct": None, "familles": {}, "principal": {},
                    "signaux": [], "moments_atypiques": [], "figement_s": 0.0,
                    "ecart_simultane": [], "debit_mots_s": None, "debit_habituel_mots_s": None,
                    "silence_max_s": None}
    return q
