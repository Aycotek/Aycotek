"""Passe 3 : la vidéo d'origine avec son encadré de mesures (1920 x 1080)."""
from __future__ import annotations

import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .analyse import Mesures
from .signaux import (AFFICHEES, CODES, EXPRESSIONS, LARGEUR_FIABLE, SEUIL_BREF, SEUIL_MOMENT,
                      UNITES, Signaux)

L, H = 1920, 1080
VX, VY, VL, VH = 0, 56, 1380, 776          # zone de la vidéo
PX0, PX1 = 1404, 1896                      # bords intérieurs du panneau
CX0, CX1, CY0, CY1 = 30, 1350, 876, 1000   # courbe d'écart
ZOOM_PX = 240

FOND, PANNEAU, TRAIT = (14, 17, 22), (21, 26, 33), (44, 51, 62)
TEXTE, DISCRET = (230, 234, 240), (139, 149, 165)
VERT, AMBRE, ROUGE = (63, 184, 175), (242, 181, 68), (229, 96, 77)
BLEU = (96, 165, 250)
AVERTISSEMENT = ("Cet outil mesure des mouvements. Il n'indique pas si la personne ment "
                 "ni ce qu'elle pense.")

_POLICES = {
    False: ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"],
    True: ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
           "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
}
_cache = {}


def police(taille: int, gras: bool = False):
    cle = (taille, gras)
    if cle not in _cache:
        for chemin in _POLICES[gras]:
            if os.path.exists(chemin):
                _cache[cle] = ImageFont.truetype(chemin, taille)
                break
        else:
            _cache[cle] = ImageFont.load_default(taille)
    return _cache[cle]


def tc(secondes: float) -> str:
    return f"{int(secondes // 60)}:{secondes % 60:04.1f}"


def couleur(z: float):
    if not np.isfinite(z):
        return DISCRET
    return VERT if abs(z) < SEUIL_MOMENT else AMBRE if abs(z) < SEUIL_BREF else ROUGE


def _barre(d, x0, y, x1, valeur, teinte, h=8):
    d.rectangle([x0, y, x1, y + h], fill=TRAIT)
    if np.isfinite(valeur) and valeur > 0.01:
        d.rectangle([x0, y, x0 + (x1 - x0) * min(valeur, 1.0), y + h], fill=teinte)


def _droite(d, x, y, texte, fonte, teinte):
    d.text((x - d.textlength(texte, font=fonte), y), texte, font=fonte, fill=teinte)


def _fond(m: Mesures, s: Signaux, titre: str) -> Image.Image:
    """Tout ce qui ne change pas d'une image à l'autre."""
    img = Image.new("RGB", (L, H), FOND)
    d = ImageDraw.Draw(img)
    d.rectangle([VL, 0, L, H], fill=PANNEAU)
    d.text((30, 14), "FACESCOPE", font=police(22, True), fill=TEXTE)
    d.text((196, 20), titre[:70], font=police(15), fill=DISCRET)

    def section(y, nom, legende):
        d.text((PX0, y), nom, font=police(14, True), fill=TEXTE)
        d.text((PX0, y + 20), legende, font=police(12), fill=DISCRET)

    section(284, "EXPRESSION AFFICHÉE",
            "ressemblance à une configuration type, pas l'émotion ressentie")
    for e, (nom, _, _) in enumerate(EXPRESSIONS):
        d.text((PX0, 328 + 26 * e), nom, font=police(14), fill=TEXTE)
    section(498, "MOUVEMENTS DU VISAGE",
            "unités d'action FACS (approchées) - couleur = écart à sa ligne de base")
    libelles = dict((c, lib) for c, lib, _ in UNITES)
    for r, code in enumerate(AFFICHEES):
        d.text((PX0, 542 + 23 * r), code, font=police(12, True), fill=DISCRET)
        d.text((PX0 + 46, 541 + 23 * r), libelles[code], font=police(13), fill=TEXTE)
    d.text((PX0, 834), "VOIX", font=police(14, True), fill=TEXTE)
    d.text((PX0, 900), "ÉCART À SA LIGNE DE BASE", font=police(14, True), fill=TEXTE)
    d.text((PX0 + 226, 902), "1 = habituel pour cette personne", font=police(12), fill=DISCRET)

    # Courbe d'écart sur toute la durée.
    d.text((CX0, 846), "ÉCART À SA LIGNE DE BASE AU FIL DE LA VIDÉO",
           font=police(13, True), fill=TEXTE)
    _droite(d, CX1, 847, "▲ moments atypiques     ▬ figement     ┆ changements de plan",
            police(12), DISCRET)
    d.rectangle([CX0, CY0, CX1, CY1], fill=PANNEAU)
    n, larg = m.n, CX1 - CX0
    haut = max(4.0, float(np.nanpercentile(s.ecart, 99.5)) if np.isfinite(s.ecart).any() else 4.0)

    def y_de(v):
        return CY1 - (CY1 - CY0 - 6) * min(v, haut) / haut

    colonnes = np.full(larg + 1, np.nan)
    limites = np.linspace(0, n, larg + 2).astype(int)
    for x in range(larg + 1):
        seg = s.ecart[limites[x]:max(limites[x + 1], limites[x] + 1)]
        if np.isfinite(seg).any():
            colonnes[x] = np.nanmax(seg)
    for c in m.coupes:
        x = CX0 + larg * c / max(n - 1, 1)
        for y in range(CY0, CY1, 6):
            d.line([x, y, x, y + 2], fill=TRAIT)
    y2 = y_de(SEUIL_MOMENT)
    for x in range(CX0, CX1, 10):
        d.line([x, y2, x + 4, y2], fill=DISCRET)
    d.text((CX1 + 6, y2 - 7), "2", font=police(11), fill=DISCRET)
    for x in range(larg):
        a, b = colonnes[x], colonnes[x + 1]
        if np.isfinite(a) and np.isfinite(b):
            d.line([CX0 + x, y_de(a), CX0 + x + 1, y_de(b)], fill=couleur(max(a, b)), width=2)
    for f in s.figements:
        d.rectangle([CX0 + larg * f["image"] / max(n - 1, 1), CY1 - 5,
                     CX0 + larg * f["fin"] / max(n - 1, 1), CY1], fill=BLEU)
    for k, mo in enumerate(s.moments):
        x = CX0 + larg * mo["image"] / max(n - 1, 1)
        d.polygon([(x - 6, CY0 - 2), (x + 6, CY0 - 2), (x, CY0 + 8)], fill=AMBRE)
        d.text((x + 8, CY0 + 2), str(k + 1), font=police(11, True), fill=AMBRE)
    duree = m.n / m.fps
    for f in (0, .25, .5, .75, 1):
        txt = tc(m.debut + duree * f)
        x = CX0 + larg * f
        d.text((x - (d.textlength(txt, font=police(11)) if f == 1 else 0), CY1 + 6), txt,
               font=police(11), fill=DISCRET)
    d.text((CX0, 1040), AVERTISSEMENT, font=police(14), fill=DISCRET)
    return img


def rendre(m: Mesures, s: Signaux, sortie: str, titre: str, passage: tuple | None = None) -> None:
    """Écrit la vidéo annotée. `passage` = (image de début, image de fin) pour n'en rendre
    qu'une partie : la courbe du bas et la ligne de base portent toujours sur tout l'extrait."""
    i0, i1 = passage or (0, m.n)
    statique = _fond(m, s, titre)
    ech = min(VL / m.largeur, VH / m.hauteur)
    vl, vh = int(m.largeur * ech) // 2 * 2, int(m.hauteur * ech) // 2 * 2
    ox, oy = VX + (VL - vl) // 2, VY + (VH - vh) // 2
    k_au = {c: i for i, c in enumerate(CODES)}

    etiquette = [None] * m.n          # mouvement bref affiché pendant 1,5 s
    for b in s.brefs:
        txt = f"Mouvement bref : {b['code']} {b['nom']} ({b['duree']:.2f} s)".replace(".", ",")
        for i in range(b["image"], min(m.n, b["image"] + int(1.5 * m.fps))):
            etiquette[i] = txt
    fige = np.zeros(m.n, bool)
    for f in s.figements:
        fige[f["image"]:f["fin"]] = True
        txt = ("Figement : tête et haut du visage moins mobiles que d'habitude "
               f"({f['duree']:.1f} s)").replace(".", ",")
        for i in range(f["image"], f["fin"]):
            etiquette[i] = txt
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
    f13, f14, f12, f12g = police(13), police(14), police(12), police(12, True)

    for i in range(i0, i1):
        lu, image = cap.read()
        if not lu:
            break
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        toile = statique.copy()
        toile.paste(Image.fromarray(cv2.resize(rgb, (vl, vh), interpolation=cv2.INTER_AREA)),
                    (ox, oy))
        d = ImageDraw.Draw(toile)
        _droite(d, VL - 30, 19, f"{tc(m.debut + m.t[i])} / {tc(m.debut + duree)}"
                f"    plan {plan[i]}", police(15), TEXTE)
        suivi, fiable = bool(m.valide[i]), bool(s.ok[i])

        if suivi:
            x0, y0, x1, y1 = (m.boite[i] * ech + [ox, oy, ox, oy]).tolist()
            c, t = (VERT if fiable else DISCRET), 22
            for (px, py, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1),
                                     (x1, y1, -1, -1)):
                d.line([px, py, px + sx * t, py], fill=c, width=3)
                d.line([px, py, px, py + sy * t], fill=c, width=3)
            cx, cy, cote = m.cadre[i]
            e = ZOOM_PX / max(cote, 1.0)
            mat = np.float32([[e, 0, ZOOM_PX / 2 - cx * e], [0, e, ZOOM_PX / 2 - cy * e]])
            zoom = cv2.warpAffine(rgb, mat, (ZOOM_PX, ZOOM_PX), flags=cv2.INTER_LINEAR)
            toile.paste(Image.fromarray(zoom), (PX0, 20))
        else:
            d.rectangle([PX0, 20, PX0 + ZOOM_PX, 20 + ZOOM_PX], fill=FOND)
            d.text((PX0 + 22, 122), "Pas de visage exploitable", font=f14, fill=DISCRET)
            d.text((PX0 + 22, 144), "(plan large ou transition)", font=f12, fill=DISCRET)
        d.rectangle([PX0, 20, PX0 + ZOOM_PX, 20 + ZOOM_PX], outline=TRAIT)

        # Colonne de chiffres à droite du zoom.
        def ligne(r, nom, valeur, teinte=TEXTE):
            d.text((PX0 + 264, 24 + 48 * r), nom, font=f12, fill=DISCRET)
            d.text((PX0 + 264, 41 + 48 * r), valeur, font=police(16, True), fill=teinte)

        if suivi:
            lacet, tangage, roulis = m.angles[i]
            ligne(0, "Tête (lacet / tangage / roulis)",
                  f"{lacet:+.0f}° / {tangage:+.0f}° / {roulis:+.0f}°")
        else:
            ligne(0, "Tête (lacet / tangage / roulis)", "-", DISCRET)
        cl = s.clignements[i]
        ligne(1, "Clignements", f"{cl:.0f} par minute" if np.isfinite(cl) else "-")
        ligne(2, "Parole", "parle" if (s.parle[i] and fiable) else "ne parle pas"
              if fiable else "-")
        precise = fiable and s.largeur_visage >= LARGEUR_FIABLE
        ligne(3, "Mesure", "fiable" if precise else "basse résolution" if fiable
              else "limitée" if suivi else "aucune", VERT if precise else AMBRE)
        zm = s.z_mobilite[i] if fiable else np.nan
        ligne(4, "Mobilité", "figée" if fige[i] else "-" if not np.isfinite(zm)
              else "forte" if zm > SEUIL_MOMENT else "habituelle",
              BLEU if fige[i] else AMBRE if np.isfinite(zm) and zm > SEUIL_MOMENT else TEXTE)

        for e_, _ in enumerate(EXPRESSIONS):
            v = s.expressions[i, e_] if fiable else np.nan
            y = 328 + 26 * e_
            _barre(d, PX0 + 190, y + 5, PX1 - 56, v, VERT)
            _droite(d, PX1, y, f"{100 * v:.0f} %" if np.isfinite(v) else "-", f13, TEXTE)
        for r, code in enumerate(AFFICHEES):
            k = k_au[code]
            v = s.intensite[i, k] if fiable else np.nan
            z = s.z_au[i, k] if fiable else np.nan
            y = 542 + 23 * r
            _barre(d, PX0 + 262, y + 4, PX1 - 56, v, couleur(z))
            _droite(d, PX1, y, f"{z:+.1f}" if np.isfinite(z) else "-", f12g, couleur(z))

        f0, db = s.f0[i], s.db[i]
        d.text((PX0, 858), "Hauteur", font=f12, fill=DISCRET)
        d.text((PX0 + 60, 855), f"{f0:.0f} Hz" if np.isfinite(f0) else "-",
               font=police(16, True), fill=TEXTE)
        d.text((PX0 + 190, 858), "Énergie", font=f12, fill=DISCRET)
        d.text((PX0 + 250, 855), f"{db:.0f} dB" if np.isfinite(db) else "-",
               font=police(16, True), fill=TEXTE)

        ec, pc = s.ecart[i], s.percentile[i]
        d.text((PX0, 922), f"{ec:.1f}".replace(".", ",") if np.isfinite(ec) else "-",
               font=police(40, True), fill=couleur(ec))
        if np.isfinite(pc):
            d.text((PX0 + 120, 930), f"plus élevé que {pc:.0f} % de la vidéo", font=f13,
                   fill=TEXTE)
            _barre(d, PX0 + 120, 954, PX1, pc / 100, couleur(ec), h=6)
        x = PX0
        for nom, serie in s.groupes.items():
            g = serie[i]
            d.text((x, 982), nom, font=f12, fill=DISCRET)
            d.text((x + d.textlength(nom + " ", font=f12), 980),
                   f"{g:.1f}".replace(".", ",") if np.isfinite(g) else "-",
                   font=police(14, True), fill=couleur(g))
            x += 492 // len(s.groupes)
        if etiquette[i]:
            d.text((PX0, 1022), etiquette[i], font=f13, fill=BLEU if fige[i] else AMBRE)

        xc = CX0 + (CX1 - CX0) * i / max(m.n - 1, 1)
        d.line([xc, CY0 - 4, xc, CY1 + 2], fill=TEXTE, width=2)
        ff.stdin.write(toile.tobytes())
        if (i + 1 - i0) % 250 == 0:
            print(f"  rendu : {i + 1 - i0} / {i1 - i0} images", file=sys.stderr, flush=True)

    cap.release()
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg a échoué pendant l'encodage de la vidéo.")
