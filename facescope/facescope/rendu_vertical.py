"""Rendu vertical 9:16 (1080 x 1920) pour les réseaux sociaux.

De haut en bas : en-tête, bandeau (zoom et mesures de base), bloc d'analyse, vidéo au
format d'origine, courbe d'écart, mesures détaillées. Le bloc d'analyse est alimenté par
un fichier rédigé à part (discours, véracité) ; sans fichier, il résume les mesures.
"""
from __future__ import annotations

import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

from . import parole
from .analyse import Mesures
from .rendu import (AMBRE, AVERTISSEMENT, BLEU, DISCRET, FOND, PANNEAU, ROUGE, TEXTE, TRAIT,
                    VERT, _barre, _droite, couleur, police, tc)
from .signaux import (AFFICHEES, CODES, EXPRESSIONS, LARGEUR_FIABLE, SEUIL_MOMENT, UNITES,
                      Signaux)

L, H = 1080, 1920
M = 36                                       # marge latérale
BY0, BY1 = 88, 248                           # bandeau : zoom et mesures de base
AY0, AY1 = 256, 640                          # bloc d'analyse
VY, VH = 648, 608                            # vidéo
CX0, CX1, CY0, CY1 = M, L - M, 1296, 1376    # courbe d'écart
DY = 1410                                    # colonnes de mesures
EY = 1706                                    # bloc « écart à sa ligne de base »
ZOOM_PX = 144
COL2 = 560                                   # début de la colonne de droite
VERDICTS = {"exact": VERT, "confirmé": VERT, "inexact": ROUGE, "faux": ROUGE,
            "trompeur": AMBRE, "imprécis": AMBRE, "contesté": AMBRE, "à nuancer": AMBRE,
            "partiel": AMBRE, "incohérence": AMBRE, "non vérifiable": DISCRET}


def _couper(d, texte, fonte, largeur, max_lignes) -> list:
    """Découpe un texte en lignes qui tiennent dans la largeur, avec « … » s'il déborde."""
    lignes, courante, deborde = [], "", False
    # Espaces insécables : un guillemet ou un deux-points ne reste jamais seul en bout de ligne.
    for avant, apres in (("« ", "« "), (" »", " »"), (" :", " :"),
                         (" ?", " ?"), (" !", " !"), (" ;", " ;")):
        texte = texte.replace(avant, apres)
    for mot in texte.split(" "):
        if not mot:
            continue
        essai = (courante + " " + mot).strip()
        if d.textlength(essai, font=fonte) <= largeur:
            courante = essai
            continue
        lignes.append(courante)
        courante = mot
        if len(lignes) == max_lignes:
            deborde = True
            break
    if not deborde and courante:
        lignes.append(courante)
    if deborde:
        lignes[-1] = lignes[-1].rstrip(" .,;:") + "…"
    return lignes


def tracer_courbe(d, m: Mesures, s: Signaux, analyse: list, debut: float) -> None:
    """Indice d'écart sur toute la durée, avec plans, moments, figements et analyses."""
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
    for k, mo in enumerate(s.moments):
        x = x_de(mo["image"])
        d.polygon([(x - 7, CY0 - 3), (x + 7, CY0 - 3), (x, CY0 + 9)], fill=AMBRE)
        d.text((x + 9, CY0 + 8), str(k + 1), font=police(15, True), fill=AMBRE)
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


def _fond(m: Mesures, s: Signaux, titre: str, analyse: list) -> Image.Image:
    """Tout ce qui ne change pas d'une image à l'autre."""
    img = Image.new("RGB", (L, H), FOND)
    d = ImageDraw.Draw(img)
    d.text((M, 22), "FACESCOPE", font=police(34, True), fill=TEXTE)
    d.text((282, 34), titre[:34], font=police(20), fill=DISCRET)
    d.rectangle([0, BY0, L, BY1], fill=PANNEAU)
    d.rectangle([0, AY0, L, AY1], fill=PANNEAU)
    d.text((M, AY0 + 16), "ANALYSE", font=police(24, True), fill=TEXTE)

    d.text((M, CY0 - 28), "ÉCART À SA LIGNE DE BASE AU FIL DE LA VIDÉO", font=police(18, True),
           fill=TEXTE)
    _droite(d, L - M, CY0 - 26, "▲ moment atypique   ▬ figement   ▬ écart sur plusieurs canaux",
            police(14), DISCRET)
    tracer_courbe(d, m, s, analyse, m.debut)

    d.text((M, DY), "EXPRESSION AFFICHÉE", font=police(22, True), fill=TEXTE)
    d.text((M, DY + 28), "ressemblance, pas l'émotion ressentie", font=police(16), fill=DISCRET)
    for e, (nom, _, _) in enumerate(EXPRESSIONS):
        d.text((M, DY + 56 + 31 * e), nom, font=police(21), fill=TEXTE)
    d.text((COL2, DY), "MOUVEMENTS DU VISAGE", font=police(22, True), fill=TEXTE)
    libelles = dict((c, lib) for c, lib, _ in UNITES)
    for r, code in enumerate(AFFICHEES):
        y = DY + 35 + 21.5 * r
        d.text((COL2, y + 2), code, font=police(15, True), fill=DISCRET)
        d.text((COL2 + 58, y), libelles[code], font=police(17), fill=TEXTE)

    d.text((M, EY + 4), "ÉCART À SA LIGNE DE BASE", font=police(22, True), fill=TEXTE)
    _droite(d, L - M, EY + 8, "1 = habituel pour cette personne", police(16), DISCRET)
    for k, ligne in enumerate(_couper(d, AVERTISSEMENT, police(18), L - 2 * M, 2)):
        d.text((M, 1852 + 24 * k), ligne, font=police(18), fill=DISCRET)
    return img


def _dessiner_analyse(d, actif, phrase, lecture) -> None:
    """Bloc d'analyse : ce qui est dit, puis le verdict, l'explication et la source."""
    x = M + 150
    verdict = str(actif.get("verdict", "")) if actif else ""
    if verdict:
        teinte = VERDICTS.get(verdict.lower(), BLEU)
        larg = d.textlength(verdict.upper(), font=police(20, True)) + 28
        d.rounded_rectangle([x, AY0 + 12, x + larg, AY0 + 48], 7, fill=teinte)
        d.text((x + 14, AY0 + 18), verdict.upper(), font=police(20, True), fill=FOND)
    titre = actif.get("titre", "") if actif else "Lecture des mesures"
    for ligne in _couper(d, titre, police(30, True), L - 2 * M, 1):
        d.text((M, AY0 + 58), ligne, font=police(30, True), fill=TEXTE)

    if phrase:
        d.rectangle([M, AY0 + 108, M + 4, AY0 + 164], fill=TRAIT)
        for k, ligne in enumerate(_couper(d, "« " + phrase + " »", police(22), L - 2 * M - 20, 2)):
            d.text((M + 20, AY0 + 106 + 30 * k), ligne, font=police(22), fill=DISCRET)

    texte, teinte = (actif.get("texte", ""), TEXTE) if actif else lecture
    for k, ligne in enumerate(_couper(d, texte, police(26), L - 2 * M, 4)):
        d.text((M, AY0 + 180 + 36 * k), ligne, font=police(26), fill=teinte)
    if actif and actif.get("source"):
        d.text((M, AY1 - 34), ("Source : " + actif["source"])[:105], font=police(18),
               fill=DISCRET)


def rendre(m: Mesures, s: Signaux, sortie: str, titre: str, passage: tuple | None = None,
           analyse: list | None = None) -> None:
    analyse = sorted(analyse or [], key=lambda e: e["debut"])
    i0, i1 = passage or (0, m.n)
    statique = _fond(m, s, titre, analyse)
    ech = min(L / m.largeur, VH / m.hauteur)
    vl, vh = int(m.largeur * ech) // 2 * 2, int(m.hauteur * ech) // 2 * 2
    ox, oy = (L - vl) // 2, VY + (VH - vh) // 2
    k_au = {c: i for i, c in enumerate(CODES)}
    fige = np.zeros(m.n, bool)
    for f in s.figements:
        fige[f["image"]:f["fin"]] = True
    plan = np.searchsorted(np.array(m.coupes), np.arange(m.n), side="right") + 1

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
    f16, f18, f20, f21 = police(16), police(18), police(20), police(21)
    g22, g24 = police(22, True), police(24, True)

    for i in range(i0, i1):
        lu, image = cap.read()
        if not lu:
            break
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        toile = statique.copy()
        toile.paste(Image.fromarray(cv2.resize(rgb, (vl, vh), interpolation=cv2.INTER_AREA)),
                    (ox, oy))
        d = ImageDraw.Draw(toile)
        instant = m.debut + m.t[i]
        _droite(d, L - M, 30, f"{tc(instant)} / {tc(m.debut + duree)}   plan {plan[i]}",
                police(22), TEXTE)
        suivi, fiable = bool(m.valide[i]), bool(s.ok[i])

        # Bandeau : zoom sur le visage et mesures de base.
        if suivi:
            x0, y0, x1, y1 = (m.boite[i] * ech + [ox, oy, ox, oy]).tolist()
            teinte, t = (VERT if fiable else DISCRET), 18
            for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1),
                                     (x1, y1, -1, -1)):
                d.line([px, py, px + sx * t, py], fill=teinte, width=3)
                d.line([px, py, px, py + sy * t], fill=teinte, width=3)
            cx, cy, cote = m.cadre[i]
            e = ZOOM_PX / max(cote, 1.0)
            mat = np.float32([[e, 0, ZOOM_PX / 2 - cx * e], [0, e, ZOOM_PX / 2 - cy * e]])
            toile.paste(Image.fromarray(cv2.warpAffine(rgb, mat, (ZOOM_PX, ZOOM_PX))),
                        (M, BY0 + 8))
        else:
            d.rectangle([M, BY0 + 8, M + ZOOM_PX, BY0 + 8 + ZOOM_PX], fill=FOND)
            d.text((M + 10, BY0 + 70), "Pas de visage", font=f18, fill=DISCRET)
        d.rectangle([M, BY0 + 8, M + ZOOM_PX, BY0 + 8 + ZOOM_PX], outline=TRAIT)

        def case(colonne, rang, nom, valeur, teinte=TEXTE):
            x, y = (210, 520, 800)[colonne], BY0 + 14 + 72 * rang
            d.text((x, y), nom, font=f16, fill=DISCRET)
            d.text((x, y + 22), valeur, font=g24, fill=teinte)

        if suivi:
            lacet, tangage, roulis = m.angles[i]
            case(0, 0, "Tête (lacet / tangage / roulis)",
                 f"{lacet:+.0f}° / {tangage:+.0f}° / {roulis:+.0f}°")
        else:
            case(0, 0, "Tête (lacet / tangage / roulis)", "-", DISCRET)
        cl = s.clignements[i]
        case(1, 0, "Clignements", f"{cl:.0f} par minute" if np.isfinite(cl) else "-")
        zm = s.z_mobilite[i] if fiable else np.nan
        case(2, 0, "Mobilité", "figée" if fige[i] else "-" if not np.isfinite(zm)
             else "forte" if zm > SEUIL_MOMENT else "habituelle",
             BLEU if fige[i] else AMBRE if np.isfinite(zm) and zm > SEUIL_MOMENT else TEXTE)
        case(0, 1, "Parole", "parle" if (s.parle[i] and fiable) else "ne parle pas"
             if fiable else "-")
        debit = s.debit[i]
        case(1, 1, "Débit", f"{debit:.1f} mots/s".replace(".", ",")
             if np.isfinite(debit) and debit > 0 else "-")
        precise = fiable and s.largeur_visage >= LARGEUR_FIABLE
        case(2, 1, "Mesure", "fiable" if precise else "basse résolution" if fiable
             else "limitée" if suivi else "aucune", VERT if precise else AMBRE)

        # Bloc d'analyse : l'élément en cours, sinon la lecture automatique des mesures.
        actif = None
        for e in analyse:
            if e["debut"] <= instant <= e.get("fin", e["debut"] + 12):
                actif = e
        hauts = [nom for nom, serie in s.groupes.items()
                 if np.isfinite(serie[i]) and serie[i] > SEUIL_MOMENT]
        if len(hauts) >= 2:
            lecture = ("Écart simultané sur plusieurs canaux : " + ", ".join(hauts).lower()
                       + ". C'est un endroit où regarder de plus près, pas une preuve.", AMBRE)
        elif fige[i]:
            lecture = ("Figement : la tête et le haut du visage bougent moins que d'habitude.",
                       BLEU)
        else:
            lecture = ("Rien d'inhabituel sur ce passage.", DISCRET)
        _dessiner_analyse(d, actif, parole.phrase_a(s.transcription, m.t[i]), lecture)

        xc = CX0 + (CX1 - CX0) * i / max(m.n - 1, 1)
        d.line([xc, CY0 - 4, xc, CY1 + 2], fill=TEXTE, width=2)

        # Colonnes de mesures.
        for e_, _ in enumerate(EXPRESSIONS):
            v = s.expressions[i, e_] if fiable else np.nan
            y = DY + 56 + 31 * e_
            _barre(d, 262, y + 9, 440, v, VERT, h=10)
            _droite(d, 520, y, f"{100 * v:.0f} %" if np.isfinite(v) else "-", f21, TEXTE)
        f0, db, y = s.f0[i], s.db[i], DY + 250
        d.text((M, y + 6), "Voix", font=f16, fill=DISCRET)
        d.text((M + 44, y), f"{f0:.0f} Hz" if np.isfinite(f0) else "-", font=g22, fill=TEXTE)
        d.text((M + 150, y + 6), "Énergie", font=f16, fill=DISCRET)
        d.text((M + 218, y), f"{db:.0f} dB" if np.isfinite(db) else "-", font=g22, fill=TEXTE)
        pause = s.pause[i]
        if np.isfinite(pause) and pause >= 1.0:
            d.text((M + 330, y + 4), f"silence {pause:.1f} s".replace(".", ","), font=f18,
                   fill=AMBRE)
        for r, code in enumerate(AFFICHEES):
            k = k_au[code]
            v = s.intensite[i, k] if fiable else np.nan
            z = s.z_au[i, k] if fiable else np.nan
            y = DY + 35 + 21.5 * r
            _barre(d, COL2 + 300, y + 7, L - M - 62, v, couleur(z), h=9)
            _droite(d, L - M, y + 1, f"{z:+.1f}" if np.isfinite(z) else "-", police(16, True),
                    couleur(z))

        ec, pc = s.ecart[i], s.percentile[i]
        d.text((M, EY + 28), f"{ec:.1f}".replace(".", ",") if np.isfinite(ec) else "-",
               font=police(52, True), fill=couleur(ec))
        if np.isfinite(pc):
            d.text((180, EY + 38), f"plus élevé que {pc:.0f} % de la vidéo", font=f20, fill=TEXTE)
            _barre(d, 180, EY + 70, L - M, pc / 100, couleur(ec), h=8)
        x = M
        for nom, serie in s.groupes.items():
            g = serie[i]
            d.text((x, EY + 98), nom, font=f16, fill=DISCRET)
            d.text((x + d.textlength(nom + " ", font=f16), EY + 93),
                   f"{g:.1f}".replace(".", ",") if np.isfinite(g) else "-", font=g22,
                   fill=couleur(g))
            x += (L - 2 * M) // len(s.groupes)

        ff.stdin.write(toile.tobytes())
        if (i + 1 - i0) % 250 == 0:
            print(f"  rendu : {i + 1 - i0} / {i1 - i0} images", file=sys.stderr, flush=True)

    cap.release()
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg a échoué pendant l'encodage de la vidéo.")
