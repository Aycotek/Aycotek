"""Facescope : une vidéo en entrée, la vidéo annotée et ses mesures en sortie.

    python -m facescope interview.mp4
    python -m facescope interview.mp4 --debut 2:00 --duree 1:30 --base 0:05-0:35
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

import numpy as np

from . import audio, rendu, signaux
from .analyse import analyser

VERSION = "0.1"
LIMITES = [
    "Aucune mesure ne permet de dire qu'une personne ment : la recherche ne valide pas la "
    "détection du mensonge par le visage.",
    "Un écart signale un comportement inhabituel pour la personne dans cette vidéo, pas sa cause "
    "(question difficile, fatigue, lumière, montage, émotion sincère).",
    "Les unités d'action sont approchées par un modèle généraliste, pas codées par un expert FACS.",
    "L'expression affichée est une ressemblance à une configuration type, pas l'émotion ressentie.",
    "Une seule personne est suivie par plan : le visage dominant. Dans une interview à deux, "
    "la ligne de base peut mélanger les deux personnes.",
    "À 25 images par seconde, un mouvement de moins de 80 ms n'est vu que sur 1 ou 2 images.",
]


def _temps(texte: str) -> float:
    parties = [float(p) for p in texte.replace(",", ".").split(":")]
    return sum(v * 60 ** k for k, v in enumerate(reversed(parties)))


def _passage(texte: str) -> tuple:
    a, b = texte.split("-")
    return _temps(a), _temps(b)


def main() -> None:
    p = argparse.ArgumentParser(prog="facescope", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video")
    p.add_argument("-o", "--sortie", default="resultats", help="dossier de sortie")
    p.add_argument("--debut", type=_temps, default=0.0, help="début de l'extrait (ex. 1:30)")
    p.add_argument("--duree", type=_temps, help="durée de l'extrait (ex. 2:00)")
    p.add_argument("--base", type=_passage,
                   help="passage calme servant de référence, en temps vidéo (ex. 0:10-0:40)")
    p.add_argument("--max-visages", type=int, default=4)
    p.add_argument("--modele", help="chemin du fichier face_landmarker.task")
    p.add_argument("--sans-video", action="store_true", help="ne produit que les mesures")
    a = p.parse_args()

    os.makedirs(a.sortie, exist_ok=True)
    nom = os.path.splitext(os.path.basename(a.video))[0]
    racine = os.path.join(a.sortie, nom)

    print("1/3  Suivi du visage et mesures image par image…", file=sys.stderr)
    m = analyser(a.video, a.modele, a.max_visages, a.debut, a.duree)
    print("2/3  Voix et calcul des écarts…", file=sys.stderr)
    son = audio.extraire(a.video, a.debut, m.n / m.fps)
    base = (a.base[0] - a.debut, a.base[1] - a.debut) if a.base else None
    s = signaux.calculer(m, son, base)

    with open(racine + "_mesures.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["temps_s", "visage_suivi", "mesure_fiable", "parle", "ecart", "percentile",
                    *[f"ecart_{g.lower()}" for g in s.groupes], "lacet", "tangage", "roulis",
                    "clignements_min", "voix_hz", "voix_db",
                    *[e[0] for e in signaux.EXPRESSIONS], *signaux.CODES])

        def f3(v):
            return "" if not np.isfinite(v) else f"{v:.3f}"
        for i in range(m.n):
            w.writerow([f"{a.debut + m.t[i]:.3f}", int(m.valide[i]), int(s.ok[i]),
                        int(s.parle[i] and s.ok[i]), f3(s.ecart[i]), f3(s.percentile[i]),
                        *[f3(g[i]) for g in s.groupes.values()], *[f3(v) for v in m.angles[i]],
                        f3(s.clignements[i]), f3(s.f0[i]), f3(s.db[i]),
                        *[f3(v) for v in s.expressions[i]], *[f3(v) for v in s.au[i]]])

    def moment(mo):
        return {"temps": rendu.tc(a.debut + mo["t"]), "temps_s": round(a.debut + mo["t"], 2),
                "ecart": round(mo["ecart"], 2), "percentile": round(mo["percentile"], 1),
                "signaux": mo["signaux"]}
    rapport = {
        "outil": f"facescope {VERSION}",
        "video": os.path.basename(a.video),
        "extrait": {"debut_s": a.debut, "duree_s": round(m.n / m.fps, 2), "images": m.n,
                    "images_par_seconde": round(m.fps, 3), "plans": len(m.coupes) + 1},
        "avertissement": rendu.AVERTISSEMENT,
        "limites": LIMITES,
        "ligne_de_base": s.base,
        "moments_atypiques": [moment(mo) for mo in s.moments],
        "mouvements_brefs": [{"temps": rendu.tc(a.debut + b["t"]),
                              "temps_s": round(a.debut + b["t"], 2),
                              "duree_s": round(b["duree"], 2), "unite": b["code"],
                              "nom": b["nom"], "z": b["z"]} for b in s.brefs],
    }
    with open(racine + "_rapport.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    if not a.sans_video:
        print("3/3  Rendu de la vidéo annotée…", file=sys.stderr)
        rendu.rendre(m, s, racine + "_facescope.mp4", os.path.basename(a.video))

    print(f"\nExtrait de {m.n / m.fps:.0f} s, {len(m.coupes) + 1} plans, visage exploitable sur "
          f"{s.base['images_exploitables_pct']} % des images.")
    print(f"{len(s.moments)} moments atypiques, {len(s.brefs)} mouvements brefs.")
    for k, mo in enumerate(s.moments):
        causes = ", ".join(f"{x['nom']} ({x['z']:+.1f})" for x in mo["signaux"])
        print(f"  {k + 1}. {rendu.tc(a.debut + mo['t'])}  écart {mo['ecart']:.1f}  {causes}")
    print(f"Fichiers : {racine}_*")
    print(rendu.AVERTISSEMENT)


if __name__ == "__main__":
    main()
