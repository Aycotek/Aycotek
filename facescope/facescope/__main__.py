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

from . import audio, parole, rendu, rendu_vertical, signaux
from .analyse import analyser

VERSION = "0.3"
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
    "La transcription est automatique : elle peut contenir des erreurs et efface souvent les "
    "hésitations (« euh »).",
    "La transcription ne distingue pas les voix : la parole d'un journaliste est comptée avec "
    "celle de la personne suivie.",
    "Le bloc d'analyse (discours, véracité) vient d'un fichier rédigé à part : l'outil "
    "l'affiche, il ne vérifie pas les faits lui-même.",
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
    p.add_argument("--rendu", type=_passage,
                   help="ne rendre en vidéo qu'un passage (ex. 7:00-8:00) ; l'analyse porte sur tout")
    p.add_argument("--format", choices=["paysage", "vertical"], default="paysage",
                   help="paysage 16:9 (défaut) ou vertical 9:16 pour les réseaux sociaux")
    p.add_argument("--analyse", help="fichier JSON d'analyse (discours, véracité) à afficher")
    p.add_argument("--sans-parole", action="store_true", help="ne transcrit pas la parole")
    p.add_argument("--langue", default="fr", help="langue parlée (fr par défaut)")
    p.add_argument("--sans-video", action="store_true", help="ne produit que les mesures")
    a = p.parse_args()

    os.makedirs(a.sortie, exist_ok=True)
    nom = os.path.splitext(os.path.basename(a.video))[0]
    racine = os.path.join(a.sortie, nom)

    print("1/3  Suivi du visage et mesures image par image…", file=sys.stderr)
    m = analyser(a.video, a.modele, a.max_visages, a.debut, a.duree)
    print("2/3  Voix et calcul des écarts…", file=sys.stderr)
    son = audio.extraire(a.video, a.debut, m.n / m.fps)
    texte = None
    if not a.sans_parole:
        print("     Transcription de la parole…", file=sys.stderr)
        texte = parole.transcrire(a.video, a.debut, m.n / m.fps, a.langue,
                                  cache=f"{racine}_transcription_{int(a.debut)}_{m.n}.json")
    elements = []
    if a.analyse:
        with open(a.analyse, encoding="utf-8") as f:
            elements = json.load(f).get("elements", [])
    base = (a.base[0] - a.debut, a.base[1] - a.debut) if a.base else None
    s = signaux.calculer(m, son, base, texte)

    with open(racine + "_mesures.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["temps_s", "visage_suivi", "mesure_fiable", "parle", "ecart", "percentile",
                    *[f"ecart_{g.lower()}" for g in s.groupes], "mobilite_z", "lacet", "tangage", "roulis",
                    "clignements_min", "voix_hz", "voix_db",
                    *[e[0] for e in signaux.EXPRESSIONS], *signaux.CODES])

        def f3(v):
            return "" if not np.isfinite(v) else f"{v:.3f}"
        for i in range(m.n):
            w.writerow([f"{a.debut + m.t[i]:.3f}", int(m.valide[i]), int(s.ok[i]),
                        int(s.parle[i] and s.ok[i]), f3(s.ecart[i]), f3(s.percentile[i]),
                        *[f3(g[i]) for g in s.groupes.values()], f3(s.z_mobilite[i]),
                        *[f3(v) for v in m.angles[i]],
                        f3(s.clignements[i]), f3(s.f0[i]), f3(s.db[i]),
                        *[f3(v) for v in s.expressions[i]], *[f3(v) for v in s.au[i]]])

    def moment(mo):
        return {"temps": rendu.tc(a.debut + mo["t"]), "temps_s": round(a.debut + mo["t"], 2),
                "ecart": round(mo["ecart"], 2), "percentile": round(mo["percentile"], 1),
                "signaux": mo["signaux"]}
    alertes, lv = [], s.largeur_visage
    if not np.isfinite(lv):
        alertes.append("Aucun visage suivi dans cette vidéo.")
    elif lv < signaux.LARGEUR_MIN:
        alertes.append(f"Visage de {lv:.0f} pixels de large : trop petit pour être mesuré "
                       f"(minimum {signaux.LARGEUR_MIN}). Fournir une vidéo en 1080p ou un plan "
                       "plus serré.")
    elif lv < signaux.LARGEUR_FIABLE:
        alertes.append(f"Visage de {lv:.0f} pixels de large : mesure peu précise. Viser au moins "
                       f"{signaux.LARGEUR_FIABLE} pixels (vidéo en 720p ou 1080p).")
    rapport = {
        "outil": f"facescope {VERSION}",
        "video": os.path.basename(a.video),
        "extrait": {"debut_s": a.debut, "duree_s": round(m.n / m.fps, 2), "images": m.n,
                    "images_par_seconde": round(m.fps, 3), "plans": len(m.coupes) + 1},
        "avertissement": rendu.AVERTISSEMENT,
        "limites": LIMITES,
        "alertes": alertes,
        "ligne_de_base": s.base,
        "moments_atypiques": [moment(mo) for mo in s.moments],
        "figements": [{"temps": rendu.tc(a.debut + f["t"]), "temps_s": round(a.debut + f["t"], 2),
                       "duree_s": round(f["duree"], 1), "z": f["z"]} for f in s.figements],
        "ecarts_simultanes": [{"temps": rendu.tc(a.debut + c["t"]),
                               "temps_s": round(a.debut + c["t"], 2),
                               "duree_s": round(c["duree"], 1), "canaux": c["canaux"]}
                              for c in s.convergences],
        "parole": parole.lexique(texte),
        "analyse": elements,
        "transcription": [{"temps_s": round(a.debut + p["debut"], 2), "texte": p["texte"]}
                          for p in (texte or {}).get("phrases", [])],
        "mouvements_brefs": [{"temps": rendu.tc(a.debut + b["t"]),
                              "temps_s": round(a.debut + b["t"], 2),
                              "duree_s": round(b["duree"], 2), "unite": b["code"],
                              "nom": b["nom"], "z": b["z"]} for b in s.brefs],
    }
    with open(racine + "_rapport.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    if not a.sans_video:
        print("3/3  Rendu de la vidéo annotée…", file=sys.stderr)
        passage = None
        if a.rendu:
            passage = (max(0, int((a.rendu[0] - a.debut) * m.fps)),
                       min(m.n, int((a.rendu[1] - a.debut) * m.fps)))
        titre = os.path.basename(a.video)
        if a.format == "vertical":
            rendu_vertical.rendre(m, s, racine + "_facescope_vertical.mp4", titre, passage,
                                  elements)
        else:
            rendu.rendre(m, s, racine + "_facescope.mp4", titre, passage)

    print(f"\nExtrait de {m.n / m.fps:.0f} s, {len(m.coupes) + 1} plans, visage exploitable sur "
          f"{s.base['images_exploitables_pct']} % des images.")
    for alerte in alertes:
        print("ATTENTION : " + alerte)
    print(f"{len(s.moments)} moments atypiques, {len(s.figements)} figements, "
          f"{len(s.convergences)} écarts simultanés sur plusieurs canaux, "
          f"{len(s.brefs)} mouvements brefs.")
    for k, mo in enumerate(s.moments):
        causes = ", ".join(f"{x['nom']} ({x['z']:+.1f})" for x in mo["signaux"])
        print(f"  {k + 1}. {rendu.tc(a.debut + mo['t'])}  écart {mo['ecart']:.1f}  {causes}")
    print(f"Fichiers : {racine}_*")
    print(rendu.AVERTISSEMENT)


if __name__ == "__main__":
    main()
