"""Rendu vertical 9:16 (1080 x 1920) pour les réseaux sociaux.

De haut en bas : en-tête, bloc d'analyse (croisement de ce qui est dit et de ce que
montrent les mesures, passage par passage), vidéo pleine largeur, courbe d'écart, bande
des mesures brutes, avertissement. Le bloc d'analyse reste fixe pendant tout un passage ;
en bas du bloc s'affiche l'élément du fichier d'analyse actif, sinon les sujets les plus
marqués de la personne lue.

Avec plusieurs personnes (débat), le bloc lit une personne par passage : celle qui parle si
elle est à l'image, sinon le plus grand visage. Il donne son rôle (parle, écoute) et, sous
le tableau des canaux, une ligne par autre personne à l'image. Les visages portent leur
lettre ou leur nom ; la courbe et la bande des mesures suivent la personne lue.
"""
from __future__ import annotations

import re
import subprocess
import sys
from types import SimpleNamespace

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .analyse import Mesures
from .croisement import NOTABLE, ROLES_ECOUTE, croiser, passage_vide
from .locuteurs import HORS_CHAMP, INDETERMINE
from .rendu import (AMBRE, AVERTISSEMENT, BLEU, DISCRET, FOND, PANNEAU, ROUGE, TEXTE, TRAIT,
                    VERT, _barre, _droite, couleur, police, tc)
from .signaux import EXPRESSIONS, LARGEUR_FIABLE, SEUIL_MOMENT, Signaux, glissant

L, H = 1080, 1920
M = 36                                       # marge latérale
AY0, AY1 = 68, 868                           # bloc d'analyse (800 px)
VY, VH = 876, 608                            # vidéo pleine largeur
CX0, CX1, CY0, CY1 = M, L - M, 1524, 1592    # courbe d'écart
BY0, BY1 = 1640, 1830                        # bande des mesures brutes
ZOOM_PX = 144
COLONNES = [204, 528, 812, L - M]            # cases de la bande des mesures
# Ordonnées dans le bloc d'analyse (relatives au haut du bloc).
Y_CANAUX, PAS_CANAL = 278, 34                # cinq lignes de canaux
Y_AUTRES, PAS_AUTRE = 450, 28                # une ligne par autre personne à l'image (2 au plus)
PAS_LECTURE = 30
Y_TRAIT, Y_BAS = 580, 590                    # séparation, puis bas du bloc
VIOLET = (167, 139, 250)
VERDICTS = {"exact": VERT, "confirmé": VERT, "inexact": ROUGE, "faux": ROUGE,
            "trompeur": AMBRE, "imprécis": AMBRE, "contesté": AMBRE, "à nuancer": AMBRE,
            "partiel": AMBRE, "incohérence": AMBRE, "non vérifiable": DISCRET}
TEINTES = {"s'anime": AMBRE, "se retient": BLEU, "mixte": VIOLET, "habituel": DISCRET,
           "non mesuré": TRAIT}
CANAUX = ["Visage", "Mobilité", "Regard", "Voix", "Parole"]
ROLES = {"parle": "PARLE", "écoute": "ÉCOUTE", "sans parole": "SANS PAROLE",
         "parole non attribuée": "PAROLE NON ATTRIBUÉE", "non déterminé": ""}
LEGENDE = ["S'anime : peut traduire de l'intérêt ou de la conviction. Se retient : peut "
           "traduire de la gêne ou de la prudence.", "L'outil montre l'écart, pas sa cause."]


def _tenir(d, texte, fonte, largeur) -> str:
    """Une ligne qui tient dans la largeur, raccourcie avec « … » si besoin."""
    if d.textlength(texte, font=fonte) <= largeur:
        return texte
    mots = texte.split(" ")
    while len(mots) > 1 and d.textlength(" ".join(mots).rstrip(" .,;:") + "…",
                                         font=fonte) > largeur:
        mots.pop()
    texte = " ".join(mots).rstrip(" .,;:")
    while texte and d.textlength(texte + "…", font=fonte) > largeur:
        texte = texte[:-1].rstrip(" .,;:")
    return texte + "…"


def _couper(d, texte, fonte, largeur, max_lignes) -> list:
    """Découpe un texte en lignes qui tiennent dans la largeur, avec « … » s'il déborde."""
    # Espaces insécables : un guillemet ou un deux-points ne reste jamais seul en bout de ligne.
    for avant, apres in (("« ", "«\u00a0"), (" »", "\u00a0»"), (" :", "\u00a0:"),
                         (" ?", "\u00a0?"), (" !", "\u00a0!"), (" ;", "\u00a0;"),
                         ("n° ", "n°\u00a0")):
        texte = texte.replace(avant, apres)
    # Un nombre ne se sépare pas de son unité (« 78 % », « 2,1 s »).
    texte = re.sub(r"(\d) (?=%|s\b|min\b|Hz\b|dB\b)", "\\1\u00a0", texte)
    lignes, courante = [], ""
    for mot in texte.split(" "):
        if not mot:
            continue
        essai = (courante + " " + mot).strip()
        if not courante or d.textlength(essai, font=fonte) <= largeur:
            courante = essai
            continue
        if len(lignes) == max_lignes - 1:
            return lignes + [_tenir(d, essai, fonte, largeur)]
        lignes.append(_tenir(d, courante, fonte, largeur))
        courante = mot
    return lignes + [_tenir(d, courante, fonte, largeur)] if courante else lignes


def _nombre(x, signe=False) -> str:
    return (f"{x:+.1f}" if signe else f"{x:.1f}").replace(".", ",")


def _duree(secondes: float) -> str:
    secondes = int(round(secondes))
    return f"{secondes} s" if secondes < 60 else f"{secondes // 60} min {secondes % 60:02d} s"


def _encre(orientation: str):
    """Couleur d'une orientation écrite en texte sur le panneau (le gris foncé y est illisible)."""
    return DISCRET if orientation == "non mesuré" else TEINTES[orientation]


def _pastille(d, x, y, texte, fonte, fond, encre, h) -> float:
    """Étiquette arrondie ; renvoie l'abscisse de son bord droit."""
    larg = d.textlength(texte, font=fonte) + 28
    d.rounded_rectangle([x, y, x + larg, y + h], 8, fill=fond)
    d.text((x + 14, y + h / 2), texte, font=fonte, fill=encre, anchor="lm")
    return x + larg


def tracer_courbe(d, m: Mesures, s, analyse: list, debut: float) -> None:
    """Indice d'écart sur toute la durée, avec plans, moments, figements et analyses.
    Un moment peut porter son étiquette (« A2 ») ; sinon il est numéroté."""
    d.rectangle([CX0, CY0, CX1, CY1], fill=PANNEAU)
    n, larg = m.n, CX1 - CX0
    haut = max(4.0, float(np.nanpercentile(s.ecart, 99.5)) if np.isfinite(s.ecart).any() else 4.0)

    def y_de(v):
        return CY1 - (CY1 - CY0 - 6) * min(v, haut) / haut

    def x_de(image):
        return CX0 + larg * image / max(n - 1, 1)

    # Une valeur par pixel : moyenne sur au moins 2 secondes, pour une courbe lisible.
    limites = np.linspace(0, n, larg + 2).astype(int)
    demi = int(m.fps)
    colonnes = np.full(larg + 1, np.nan)
    for x in range(larg + 1):
        seg = s.ecart[max(limites[x] - demi, 0):max(limites[x + 1], limites[x] + 1) + demi]
        if np.isfinite(seg).mean() >= 0.5:
            colonnes[x] = np.nanmean(seg)
    for c in m.coupes:
        for y in range(CY0, CY1, 6):
            d.line([x_de(c), y, x_de(c), y + 2], fill=TRAIT)
    y2 = y_de(SEUIL_MOMENT)
    for x in range(CX0, CX1, 10):
        d.line([x, y2, x + 4, y2], fill=DISCRET)
    for x in range(larg):
        a, b = colonnes[x], colonnes[x + 1]
        if np.isfinite(a) and np.isfinite(b):
            d.line([CX0 + x, y_de(a), CX0 + x + 1, y_de(b)], fill=couleur(max(a, b)), width=2)
    for f in s.figements:
        d.rectangle([x_de(f["image"]), CY1 - 6, x_de(f["fin"]), CY1], fill=BLEU)
    for c in s.convergences:
        d.rectangle([x_de(c["image"]), CY0, x_de(c["fin"]), CY0 + 6], fill=ROUGE)
    fin_etiquette = -1e9
    for k, mo in enumerate(sorted(s.moments, key=lambda mo: mo["image"])):
        x = x_de(mo["image"])
        d.polygon([(x - 7, CY0 - 3), (x + 7, CY0 - 3), (x, CY0 + 9)], fill=AMBRE)
        etiquette = mo.get("etiquette", str(k + 1))
        if x + 9 >= fin_etiquette + 4:               # pas d'étiquettes superposées
            d.text((x + 9, CY0 + 8), etiquette, font=police(15, True), fill=AMBRE)
            fin_etiquette = x + 9 + d.textlength(etiquette, font=police(15, True))
    for e in analyse:
        x = x_de((e["debut"] - debut) * m.fps)
        if CX0 <= x <= CX1:
            teinte = VERDICTS.get(str(e.get("verdict", "")).lower(), BLEU)
            d.rectangle([x - 3, CY1 + 3, x + 3, CY1 + 9], fill=teinte)
    duree = m.n / m.fps
    for f in (0, .5, 1):
        txt = tc(debut + duree * f)
        larg_txt = d.textlength(txt, font=police(16))
        d.text((CX0 + larg * f - (larg_txt if f == 1 else larg_txt / 2 if f else 0), CY1 + 12),
               txt, font=police(16), fill=DISCRET)


def _fond(m: Mesures, courbe, titre: str, analyse: list, debat) -> Image.Image:
    """Tout ce qui ne change pas d'une image à l'autre."""
    img = Image.new("RGB", (L, H), FOND)
    d = ImageDraw.Draw(img)
    d.text((M, 14), "FACESCOPE", font=police(30, True), fill=TEXTE)
    x = M + d.textlength("FACESCOPE", font=police(30, True)) + 20
    place = L - M - d.textlength("00:00.0 / 00:00.0   plan 000", font=police(22)) - 24 - x
    d.text((x, 22), _tenir(d, titre, police(18), place), font=police(18), fill=DISCRET)
    d.rectangle([0, AY0, L, AY1], fill=PANNEAU)

    entete = "ÉCART AU FIL DE LA VIDÉO"
    if debat is not None and debat.mode == "débat":
        entete = "ÉCART DE LA PERSONNE LUE"
    d.text((M, CY0 - 28), entete, font=police(18, True), fill=TEXTE)
    _droite(d, L - M, CY0 - 26, "▲ moment atypique   ▬ figement   ▬ écart sur plusieurs canaux"
            "   □ passage affiché", police(14), DISCRET)
    tracer_courbe(d, m, courbe, analyse, m.debut)

    d.rectangle([0, BY0, L, BY1], fill=PANNEAU)
    for k, ligne in enumerate(_couper(d, AVERTISSEMENT, police(18), L - 2 * M, 2)):
        d.text((M, 1852 + 24 * k), ligne, font=police(18), fill=DISCRET)
    return img


def _canal(famille: str, p: dict) -> str:
    """Le signal principal d'un canal, en mots."""
    mes = p["mesures"]
    if not mes["familles"]:
        return "-"
    if p.get("role") in ROLES_ECOUTE and famille in ("Voix", "Parole"):
        return "non compté (écoute)"
    if famille not in mes["familles"]:
        return "pas de transcription"
    if famille == "Parole" and not p["texte"]:
        return "pas de parole"
    pr = mes["principal"].get(famille)
    if pr is None or pr["z"] is None:
        return "non mesuré"
    if abs(pr["z"]) < NOTABLE:
        return "habituel"
    if pr["signal"] == "Silence" and pr["z"] > 0 and mes["silence_max_s"]:
        return f"silence de {_nombre(mes['silence_max_s'])} s ({_nombre(pr['z'], True)})"
    return f"{pr['en_mots']} {_nombre(pr['z'], True)}"


def _repere(p: dict, lettre: str = "") -> list:
    """Moment atypique, écart simultané, figement : ce que la courbe signale sur le passage.
    Dans un débat, les moments portent la lettre de la personne, comme sur la courbe."""
    mes, reperes = p["mesures"], []
    if mes["moments_atypiques"]:
        numeros = ", ".join(f"{lettre}{k}" for k in mes["moments_atypiques"])
        reperes.append((("moment atypique " if lettre else "moment atypique n° ") + numeros,
                        AMBRE))
    if mes["ecart_simultane"]:
        reperes.append(("écart simultané : " + ", ".join(mes["ecart_simultane"]).lower(), ROUGE))
    if mes["figement_s"] >= 1:
        reperes.append((f"figement de {_nombre(mes['figement_s'])} s", BLEU))
    return reperes[:2]


def _bas_du_bloc(d, actif: dict | None, synth: dict | None, titre: str) -> None:
    """L'élément du fichier d'analyse en cours, sinon les sujets les plus marqués de la
    personne lue."""
    y0 = Y_BAS
    if actif:
        verdict, x = str(actif.get("verdict", "")), M
        if verdict:
            x = _pastille(d, M, y0, verdict.upper(), police(20, True),
                          VERDICTS.get(verdict.lower(), BLEU), FOND, 36) + 16
        d.text((x, y0 + 18), _tenir(d, actif.get("titre", ""), police(24, True), L - M - x),
               font=police(24, True), fill=TEXTE, anchor="lm")
        for k, ligne in enumerate(_couper(d, actif.get("texte", ""), police(21), L - 2 * M, 3)):
            d.text((M, y0 + 46 + 27 * k), ligne, font=police(21), fill=TEXTE)
        if actif.get("source"):
            d.text((M, y0 + 128), _tenir(d, "Source : " + actif["source"], police(16), L - 2 * M),
                   font=police(16), fill=DISCRET)
        return
    f22, g22 = police(22), police(22, True)
    if synth is None:
        d.text((M, y0 + 2), _tenir(d, titre, police(18, True), L - 2 * M), font=police(18, True),
               fill=DISCRET)
        return
    themes = synth["classement"][:3]
    if themes:
        d.text((M, y0 + 2), _tenir(d, titre, police(18, True), L - 2 * M),
               font=police(18, True), fill=DISCRET)
        for k, t in enumerate(themes):
            y = y0 + 36 + 32 * k
            nom = f"{k + 1}. {t['theme'][:1].upper()}{t['theme'][1:]}"
            d.text((M, y), _tenir(d, nom, g22, 640 - M - 16), font=g22, fill=TEXTE)
            d.text((640, y), t["orientation"], font=g22, fill=_encre(t["orientation"]))
            _droite(d, L - M, y + 3, f"{t['part_pct']} % du temps · {_duree(t['temps_s'])}",
                    police(18), DISCRET)
        return
    marques = synth["passages_marques"][:3]
    if synth.get("themes"):
        # Des thèmes, mais aucun assez long (TEMPS_THEME_MIN s, PASSAGES_THEME_MIN passages).
        qui = titre.split(" · ", 1)[1] if " · " in titre else ""
        titre = ("AUCUN SUJET ASSEZ LONG · PASSAGES LES PLUS MARQUÉS" if marques
                 else "AUCUN SUJET ASSEZ LONG POUR ÊTRE CLASSÉ") + (f" · {qui}" if qui else "")
    else:
        titre = titre.replace("SUJETS", "PASSAGES") if marques else "AUCUN PASSAGE MESURÉ"
    d.text((M, y0 + 2), _tenir(d, titre, police(18, True), L - 2 * M), font=police(18, True),
           fill=DISCRET)
    for k, p in enumerate(marques):
        y = y0 + 36 + 32 * k
        d.text((M, y), p["temps"], font=g22, fill=TEXTE)
        d.text((M + 120, y), _tenir(d, p["sujet"] or "-", f22, 640 - M - 136), font=f22,
               fill=TEXTE)
        d.text((640, y), p["orientation"], font=g22, fill=_encre(p["orientation"]))
        _droite(d, L - M, y + 3, f"écart {_nombre(p['ecart_moyen'])}", police(18), DISCRET)


def _ligne_autre(d, y, nom: str, p: dict | None) -> None:
    """« B écoute : se retient, regard détourné +2,1 » : une autre personne à l'image."""
    f21, g21 = police(21), police(21, True)
    x = M
    d.text((x, y), _tenir(d, nom, g21, 300), font=g21, fill=TEXTE)
    x += d.textlength(_tenir(d, nom, g21, 300), font=g21) + 8
    role = (p or {}).get("role") or ""
    role = {"parle": "parle", "écoute": "écoute", "sans parole": "à l'image",
            "parole non attribuée": "à l'image", "non déterminé": "à l'image"}.get(role,
                                                                                  "à l'image")
    d.text((x, y), role + " :", font=f21, fill=DISCRET)
    x += d.textlength(role + " :", font=f21) + 8
    if p is None:
        d.text((x, y), "non mesuré", font=f21, fill=DISCRET)
        return
    o = p["orientation"]
    if o == "non mesuré" and p["constat"].startswith("Pas assez"):
        d.text((x, y), "pas assez de données", font=f21, fill=DISCRET)
        return
    d.text((x, y), o, font=g21, fill=_encre(o))
    x += d.textlength(o, font=g21)
    atteints = sorted((c for c in p["criteres"] if c["atteint"] and c["valeur"] is not None),
                      key=lambda c: -abs(c["valeur"]))
    if o in ("s'anime", "se retient", "mixte") and atteints:
        c = atteints[0]
        detail = c["en_mots"] if c["en_mots"].startswith(("figement", "silence")) \
            else f"{c['en_mots']} {_nombre(c['valeur'], True)}"
        d.text((x, y), _tenir(d, ", " + detail, f21, L - M - x), font=f21, fill=TEXTE)


def _entete(d, lue, role: str | None, locuteur: str | None, debat) -> None:
    """« ANALYSE  Personne B  ÉCOUTE A » en haut du bloc, l'heure du passage à droite."""
    g22 = police(22, True)
    d.text((M, 14), "ANALYSE", font=g22, fill=TEXTE)
    if debat is None:
        return
    x = M + d.textlength("ANALYSE", font=g22) + 18
    fin = L - M - d.textlength("passage 00:00.0 – 00:00.0", font=police(18)) - 24
    if lue is None:
        d.text((x, 14), _tenir(d, "aucune personne reconnue à l'image", police(22), fin - x),
               font=police(22), fill=DISCRET)
        return
    nom = lue.nom or f"Personne {lue.id}"
    texte_role = ROLES.get(role or "", "")
    if role == "écoute" and locuteur:
        texte_role += " " + (HORS_CHAMP.upper() if locuteur == HORS_CHAMP
                             else debat.nom(locuteur).upper())
    place_role = d.textlength(texte_role, font=police(18, True)) + 28 + 14 if texte_role else 0
    nom = _tenir(d, nom, g22, max(fin - x - place_role, 120))
    d.text((x, 14), nom, font=g22, fill=VERT)
    x += d.textlength(nom, font=g22) + 14
    if texte_role:
        _pastille(d, x, 10, _tenir(d, texte_role, police(18, True), fin - x - 28),
                  police(18, True), TRAIT, TEXTE, 30)


def _bloc(p: dict, actif: dict | None, synth: dict | None, titre_bas: str, transcrit: bool,
          lue=None, autres=(), debat=None) -> Image.Image:
    """Le bloc d'analyse d'un passage : il ne change pas tant que le passage dure."""
    img = Image.new("RGB", (L, AY1 - AY0), PANNEAU)
    d = ImageDraw.Draw(img)
    mes, o = p["mesures"], p["orientation"]
    _entete(d, lue, p.get("role"), p.get("locuteur"), debat)
    _droite(d, L - M, 16, f"passage {tc(p['debut_s'])} – {tc(p['fin_s'])}", police(18), DISCRET)

    # Orientation, écart moyen du passage et son rang dans la vidéo.
    x = _pastille(d, M, 46, o.upper(), police(30, True), TEINTES[o],
                  TEXTE if o == "non mesuré" else FOND, 54)
    if mes["ecart_moyen"] is not None:
        valeur = _nombre(mes["ecart_moyen"])
        d.text((x + 22, 73), valeur, font=police(44, True), fill=couleur(mes["ecart_moyen"]),
               anchor="lm")
        x += 22 + d.textlength(valeur, font=police(44, True)) + 18
        d.text((x, 50), "écart moyen du passage", font=police(18), fill=DISCRET)
        if mes["rang_pct"] is not None:
            d.text((x, 74), f"plus élevé que {mes['rang_pct']:.0f} % de la vidéo",
                   font=police(20), fill=TEXTE)
        x += d.textlength("plus élevé que 100 % de la vidéo", font=police(20)) + 24
    lettre = lue.id if lue is not None and debat is not None and debat.mode == "débat" else ""
    for k, (texte, teinte) in enumerate(_repere(p, lettre)):
        _droite(d, L - M, 50 + 24 * k, _tenir(d, texte, police(18), L - M - x), police(18),
                teinte)

    # Ce qui est dit : sujet, chiffre cité, citation.
    label = "MOTS MARQUANTS" if not p["themes"] and p["mots_distinctifs"] else "SUJET"
    d.text((M, 132), label, font=police(16, True), fill=DISCRET, anchor="lm")
    x = M + d.textlength(label, font=police(16, True)) + 16
    fin = L - M
    if p["chiffre"]:
        _droite(d, L - M, 122, "cite un chiffre", police(18), AMBRE)
        fin -= d.textlength("cite un chiffre", font=police(18)) + 20
    sujet = p["sujet"] or ("pas de parole transcrite" if transcrit else "pas de transcription")
    d.text((x, 132), _tenir(d, sujet[:1].upper() + sujet[1:], police(28, True), fin - x),
           font=police(28, True), fill=TEXTE if p["sujet"] else DISCRET, anchor="lm")
    if p["texte"]:
        lignes = _couper(d, "« " + p["texte"] + " »", police(22), L - 2 * M - 20, 3)
        d.rectangle([M, 164, M + 4, 160 + 28 * len(lignes)], fill=TRAIT)
        for k, ligne in enumerate(lignes):
            d.text((M + 20, 160 + 28 * k), ligne, font=police(22), fill=TEXTE)

    # Ce que montrent les mesures : un canal par ligne.
    d.text((M, 254), "ÉCART PAR CANAL", font=police(16, True), fill=DISCRET)
    d.text((228, 254), "1 = habituel, repère à 2", font=police(16), fill=DISCRET)
    d.text((610, 254), "SIGNAL PRINCIPAL", font=police(16, True), fill=DISCRET)
    for r, famille in enumerate(CANAUX):
        y = Y_CANAUX + PAS_CANAL * r
        g = mes["familles"].get(famille)
        g = np.nan if g is None else g
        d.text((M, y), famille, font=police(22, True), fill=TEXTE)
        _barre(d, 228, y + 8, 500, g / 4, couleur(g), h=12)
        xr = 228 + (500 - 228) * SEUIL_MOMENT / 4
        d.line([xr, y + 4, xr, y + 23], fill=DISCRET, width=2)
        _droite(d, 580, y, "-" if not np.isfinite(g) else _nombre(g), police(22, True),
                couleur(g))
        d.text((610, y), _tenir(d, _canal(famille, p), police(22), L - M - 610),
               font=police(22), fill=TEXTE)

    # Les autres personnes à l'image, une ligne chacune (deux au plus).
    for k, (nom, q) in enumerate(list(autres)[:2]):
        _ligne_autre(d, Y_AUTRES + PAS_AUTRE * k, nom, q)
    nb_autres = min(len(autres), 2)

    # Lecture du passage (le sujet est déjà écrit plus haut) : trois lignes, deux s'il y a
    # deux autres personnes, toujours au-dessus du trait de séparation.
    y_lecture = Y_AUTRES + (PAS_AUTRE * nb_autres + 4 if nb_autres else 6)
    max_lignes = max(1, min(3, (Y_TRAIT - 8 - 24 - y_lecture) // PAS_LECTURE + 1))
    for k, ligne in enumerate(_couper(d, p["constat"], police(24), L - 2 * M, max_lignes)):
        d.text((M, y_lecture + PAS_LECTURE * k), ligne, font=police(24),
               fill=DISCRET if o in ("habituel", "non mesuré") else TEXTE)
    d.line([M, Y_TRAIT, L - M, Y_TRAIT], fill=TRAIT, width=1)
    _bas_du_bloc(d, actif, synth, titre_bas)
    for k, ligne in enumerate(LEGENDE):
        d.text((M, 750 + 20 * k), _tenir(d, ligne, police(16), L - 2 * M), font=police(16),
               fill=DISCRET)
    return img


def _courbe_lue(m: Mesures, debat):
    """Écart de la personne lue, passage par passage, et ses repères (débat)."""
    ecart = np.full(m.n, np.nan)
    lue = np.full(m.n, "", dtype=object)
    for g in debat.passages:
        p = debat.personne(g["lue"])
        if p is not None and p.s is not None:
            ecart[g["image_debut"]:g["image_fin"]] = p.s.ecart[g["image_debut"]:g["image_fin"]]
            lue[g["image_debut"]:g["image_fin"]] = p.id
    moments, figements, convergences = [], [], []
    for p in debat.personnes:
        if p.s is None:
            continue
        for k, mo in enumerate(p.s.moments):
            if lue[mo["image"]] == p.id:
                moments.append(dict(mo, etiquette=f"{p.id}{k + 1}"))
        figements += [f for f in p.s.figements if lue[f["image"]] == p.id]
        convergences += [c for c in p.s.convergences if lue[c["image"]] == p.id]
    return SimpleNamespace(ecart=ecart, moments=moments, figements=figements,
                           convergences=convergences)


def _visages(d, debat, i, ech, ox, oy, lue, m: Mesures, s: Signaux, legacy: bool) -> None:
    """Cadres des visages, avec la lettre ou le nom de la personne."""
    v = debat.v
    poses = []
    for k in range(v.piste.shape[1]):
        pid = int(v.piste[i, k])
        if pid < 0:
            continue
        b = v.boite[i, k]
        if legacy:      # une personne : seul le visage suivi en 0.4 est encadré
            if not m.valide[i] or not np.allclose(b, m.boite[i]):
                continue
        qui = debat.piste_personne.get(pid)
        personne = debat.personne(qui)
        x0, y0, x1, y1 = (b * ech + [ox, oy, ox, oy]).tolist()
        principal = legacy or (lue is not None and qui == lue.id)
        if principal:
            fiable = s.ok[i] if legacy else (lue.s is not None and lue.s.ok[i])
            teinte, t, largeur = (VERT if fiable else DISCRET), 18, 3
        else:
            teinte, t, largeur = (DISCRET if personne else TRAIT), 12, 2
        for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1),
                                 (x1, y1, -1, -1)):
            d.line([px, py, px + sx * t, py], fill=teinte, width=largeur)
            d.line([px, py, px, py + sy * t], fill=teinte, width=largeur)
        if personne is None:
            continue
        fonte = police(18, True)
        texte = _tenir(d, personne.etiquette, fonte, max(x1 - x0 + 60, 120))
        larg = d.textlength(texte, font=fonte) + 16
        lx = min(max(x0, 2), L - 2 - larg)
        ly = y0 - 30
        if ly < VY + 2 or any(_recouvre((lx, ly, lx + larg, ly + 26), r) for r in poses):
            ly = min(y1 + 4, VY + VH - 28)
        poses.append((lx, ly, lx + larg, ly + 26))
        d.rounded_rectangle([lx, ly, lx + larg, ly + 26], 6,
                            fill=VERT if principal else TRAIT)
        d.text((lx + 8, ly + 13), texte, font=fonte, fill=FOND if principal else TEXTE,
               anchor="lm")


def _recouvre(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def rendre(m: Mesures, s: Signaux, sortie: str, titre: str, passage: tuple | None = None,
           analyse: list | None = None, croisement: dict | None = None, debat=None) -> None:
    analyse = sorted(analyse or [], key=lambda e: e["debut"])
    croisement = croisement or croiser(m, s)
    passages, synth = croisement["passages"], croisement["synthese"]
    if debat is not None:
        passages = debat.passages
    numero = np.zeros(m.n, int)
    for k, p in enumerate(passages):
        numero[p["image_debut"]:p["image_fin"]] = k
    i0, i1 = passage or (0, m.n)
    multi = debat is not None and debat.mode == "débat"
    courbe = _courbe_lue(m, debat) if multi else s
    statique = _fond(m, courbe, titre, analyse, debat)
    ech = min(L / m.largeur, VH / m.hauteur)
    vl, vh = int(m.largeur * ech) // 2 * 2, int(m.hauteur * ech) // 2 * 2
    ox, oy = (L - vl) // 2, VY + (VH - vh) // 2
    # Expression affichée : moyenne sur une seconde, pour un nom qui ne clignote pas.
    lisses = {}

    def expressions_de(sig):
        if id(sig) not in lisses:
            lisses[id(sig)] = np.stack([glissant(sig.expressions[:, e], sig.ok, m.fps)
                                        for e in range(len(EXPRESSIONS))], axis=1)
        return lisses[id(sig)]
    plan = np.searchsorted(np.array(m.coupes), np.arange(m.n), side="right") + 1

    def lecture(k):
        """Personne lue, son passage, les autres personnes à l'image, la synthèse du bas."""
        if debat is None:
            return None, passages[k], [], synth, "SUJETS LES PLUS MARQUÉS DE LA VIDÉO"
        g = debat.passages[k]
        lue = debat.personne(g["lue"])
        autres = []
        for qui in g["autres"]:
            q = debat.personne(qui)
            autres.append((q.etiquette, q.passages.get(k)))
        if lue is None:
            return None, passage_vide(g, "Aucune personne reconnue à l'image sur ce passage."), \
                autres, None, "AUCUNE PERSONNE RECONNUE À L'IMAGE"
        p = lue.passages.get(k) or passage_vide(dict(g, numero=k),
                                                "Personne trop peu visible sur ce passage.")
        if lue.croise is None:
            return lue, p, autres, None, f"PAS ASSEZ DE DONNÉES POUR {lue.etiquette.upper()}"
        if not multi:                 # une personne : la synthèse de la vidéo, comme en 0.4
            return lue, p, autres, synth, "SUJETS LES PLUS MARQUÉS DE LA VIDÉO"
        parlant = lue.croise["synthese"]["en_parlant"]
        if parlant["classement"] or parlant["passages_marques"]:
            return lue, p, autres, parlant, \
                f"SUJETS LES PLUS MARQUÉS · {lue.etiquette.upper()} EN PARLANT"
        return lue, p, autres, lue.croise["synthese"]["en_ecoutant"], \
            f"SUJETS LES PLUS MARQUÉS · {lue.etiquette.upper()} EN ÉCOUTANT"

    cap = cv2.VideoCapture(m.chemin)
    for _ in range(int(round(m.debut * m.fps)) + i0):
        cap.grab()
    duree, duree_rendu = m.n / m.fps, (i1 - i0) / m.fps
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{L}x{H}", "-r", f"{m.fps:.6f}", "-i", "-",
           "-ss", f"{m.debut + i0 / m.fps:.3f}", "-t", f"{duree_rendu:.3f}", "-i", m.chemin,
           "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
           "-t", f"{duree_rendu:.3f}", "-movflags", "+faststart", sortie]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    f16, f18, g24 = police(16), police(18), police(24, True)
    cle, bloc, lu = None, None, None

    for i in range(i0, i1):
        ok_lu, image = cap.read()
        if not ok_lu:
            break
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        toile = statique.copy()
        toile.paste(Image.fromarray(cv2.resize(rgb, (vl, vh), interpolation=cv2.INTER_AREA)),
                    (ox, oy))
        d = ImageDraw.Draw(toile)
        instant = m.debut + m.t[i]
        _droite(d, L - M, 18, f"{tc(instant)} / {tc(m.debut + duree)}   plan {plan[i]}",
                police(22), TEXTE)

        # Bloc d'analyse : dessiné une fois par passage et par élément d'analyse actif.
        actif = None
        for k, e in enumerate(analyse):
            if e["debut"] <= instant <= e.get("fin", e["debut"] + 12):
                actif = k
        if (numero[i], actif) != cle:
            cle = (numero[i], actif)
            lu, p_lu, autres, synth_lu, titre_bas = lecture(numero[i])
            bloc = _bloc(p_lu, None if actif is None else analyse[actif], synth_lu, titre_bas,
                         bool(s.transcription), lu, autres, debat)
        toile.paste(bloc, (0, AY0))

        # Courbe : passage affiché et position courante.
        p = passages[numero[i]]
        xa = CX0 + (CX1 - CX0) * p["image_debut"] / max(m.n - 1, 1)
        xb = CX0 + (CX1 - CX0) * max(p["image_fin"] - 1, p["image_debut"]) / max(m.n - 1, 1)
        d.rectangle([xa, CY0, xb, CY1], outline=DISCRET)
        xc = CX0 + (CX1 - CX0) * i / max(m.n - 1, 1)
        d.line([xc, CY0 - 4, xc, CY1 + 2], fill=TEXTE, width=2)

        # Mesures de la personne lue (débat), sinon du visage suivi comme en 0.4.
        if multi:
            mm, ss = (lu.m, lu.s) if lu is not None else (None, None)
        else:
            mm, ss = m, s
        suivi = bool(mm is not None and mm.valide[i])
        fiable = bool(ss is not None and ss.ok[i])
        if debat is not None:
            _visages(d, debat, i, ech, ox, oy, lu, m, s, legacy=not multi)
        elif suivi:
            x0, y0, x1, y1 = (mm.boite[i] * ech + [ox, oy, ox, oy]).tolist()
            teinte, t = (VERT if fiable else DISCRET), 18
            for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1),
                                     (x1, y1, -1, -1)):
                d.line([px, py, px + sx * t, py], fill=teinte, width=3)
                d.line([px, py, px, py + sy * t], fill=teinte, width=3)

        # Bande des mesures brutes : zoom sur le visage et six cases.
        if suivi:
            cx, cy, cote = mm.cadre[i]
            e = ZOOM_PX / max(cote, 1.0)
            mat = np.float32([[e, 0, ZOOM_PX / 2 - cx * e], [0, e, ZOOM_PX / 2 - cy * e]])
            toile.paste(Image.fromarray(cv2.warpAffine(rgb, mat, (ZOOM_PX, ZOOM_PX))),
                        (M, BY0 + 16))
        else:
            d.rectangle([M, BY0 + 16, M + ZOOM_PX, BY0 + 16 + ZOOM_PX], fill=FOND)
            d.text((M + 10, BY0 + 78), "Pas de visage", font=f18, fill=DISCRET)
        d.rectangle([M, BY0 + 16, M + ZOOM_PX, BY0 + 16 + ZOOM_PX], outline=TRAIT)

        def case(colonne, rang, nom, valeur, teinte=TEXTE):
            x, y = COLONNES[colonne], BY0 + 18 + 80 * rang
            d.text((x, y), nom, font=f16, fill=DISCRET)
            d.text((x, y + 22), _tenir(d, valeur, g24, COLONNES[colonne + 1] - x - 16),
                   font=g24, fill=teinte)

        v = expressions_de(ss)[i] if fiable else np.full(len(EXPRESSIONS), np.nan)
        if np.isfinite(v).any():
            k = int(np.nanargmax(v))
            case(0, 0, "Expression affichée (ressemblance)",
                 f"{EXPRESSIONS[k][0]} {100 * v[k]:.0f} %" if v[k] >= 0.1 else "neutre")
        else:
            case(0, 0, "Expression affichée (ressemblance)", "-", DISCRET)
        cl = ss.clignements[i] if ss is not None else np.nan
        case(1, 0, "Clignements", f"{cl:.0f} par minute" if np.isfinite(cl) else "-")
        f0, db = (ss.f0[i], ss.db[i]) if ss is not None else (np.nan, np.nan)
        voix = ([f"{f0:.0f} Hz"] if np.isfinite(f0) else []) \
            + ([f"{db:.0f} dB"] if np.isfinite(db) else [])
        case(2, 0, "Voix", " · ".join(voix) or "-")
        if suivi:
            lacet, tangage, roulis = mm.angles[i]
            case(0, 1, "Tête (lacet / tangage / roulis)",
                 f"{lacet:+.0f}° / {tangage:+.0f}° / {roulis:+.0f}°")
        else:
            case(0, 1, "Tête (lacet / tangage / roulis)", "-", DISCRET)
        debit = ss.debit[i] if ss is not None else np.nan
        case(1, 1, "Débit", f"{_nombre(debit)} mots/s"
             if np.isfinite(debit) and debit > 0 else "-")
        precise = fiable and ss.largeur_visage >= LARGEUR_FIABLE
        case(2, 1, "Mesure", "fiable" if precise else "basse résolution" if fiable
             else "limitée" if suivi else "aucune", VERT if precise else AMBRE)

        ff.stdin.write(toile.tobytes())
        if (i + 1 - i0) % 250 == 0:
            print(f"  rendu : {i + 1 - i0} / {i1 - i0} images", file=sys.stderr, flush=True)

    cap.release()
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg a échoué pendant l'encodage de la vidéo.")
