"""Facescope : une vidéo en entrée, la vidéo annotée et ses mesures en sortie.

    python -m facescope interview.mp4
    python -m facescope interview.mp4 --debut 2:00 --duree 1:30 --base 0:05-0:35
    python -m facescope debat.mp4 --format vertical --noms "A=Prénom Nom,B=Prénom Nom"
    python -m facescope "https://www.youtube.com/watch?v=…" --demander-noms
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import sys
import time

import numpy as np

from . import (analyse, audio, croisement, identite, locuteurs, parole, personnes, rendu,
               rendu_vertical, signaux, telechargement)

VERSION = "0.7"
PORTEE = ("Les clés ligne_de_base, moments_atypiques, figements, ecarts_simultanes, "
          "croisement, mouvements_brefs et le fichier CSV portent, comme en 0.4, sur le visage "
          "dominant de chaque plan avec une seule ligne de base et toute la parole. Dans un "
          "débat, lire « personnes » : une ligne de base, des passages et une synthèse par "
          "personne.")
LIMITES = [
    "Aucune mesure ne permet de dire qu'une personne ment : la recherche ne valide pas la "
    "détection du mensonge par le visage.",
    "Un écart signale un comportement inhabituel pour la personne dans cette vidéo, pas sa cause "
    "(question difficile, fatigue, lumière, montage, émotion sincère).",
    "Les unités d'action sont approchées par un modèle généraliste, pas codées par un expert FACS.",
    "L'expression affichée est une ressemblance à une configuration type, pas l'émotion ressentie.",
    "Les personnes sont regroupées par ressemblance des visages (empreinte faciale) : deux "
    "personnes très semblables peuvent être réunies, une même personne vue de profil ou de loin "
    "peut rester dans « autres ». L'outil ne reconnaît personne : les noms viennent de "
    "l'utilisateur.",
    "Dans un débat, une personne reconnue qui n'est ni nommée par une photo ni assez parlante "
    "est comptée dans le public : elle n'est ni analysée ni étiquetée. Un intervenant qui parle "
    "très peu peut y tomber ; une photo de référence (--visages) le garde participant.",
    "Dans un débat, la parole est attribuée par la bouche (la personne à l'image dont la "
    "mâchoire bouge pendant les mots), puis par la voix (empreinte vocale comparée aux voix "
    "repérées par la bouche). Quand deux personnes parlent en même temps, le morceau peut rester "
    "« indéterminé » ; une interruption à l'intérieur d'une phrase n'est pas séparée ; une voix "
    "jamais vue parler à l'image reste « voix hors champ ».",
    "À 25 images par seconde, un mouvement de moins de 80 ms n'est vu que sur 1 ou 2 images.",
    "La transcription est automatique : elle peut contenir des erreurs et efface souvent les "
    "hésitations (« euh »).",
    "Avec une seule personne reconnue, toute la parole transcrite lui est comptée, y compris "
    "celle d'une voix hors champ (--debat pour la séparer).",
    "Les thèmes des passages sont reconnus par une liste de mots-clés : un sujet abordé sans "
    "ces mots n'est pas reconnu, et un mot-clé peut apparaître hors sujet.",
    "L'orientation d'un passage (s'anime, se retient, mixte, habituel) suit une règle simple "
    "aux seuils réglés à la main, non validée sur des extraits annotés. Elle décrit la direction "
    "d'un écart, pas sa cause.",
    "En parlant, « se retient » repose surtout sur les pauses, les hésitations et la baisse de "
    "mobilité : un silence long n'y compte qu'à partir d'une pause de 2 s.",
    "La vérification des faits vient d'un fichier rédigé à part (--analyse) : l'outil "
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
    p.add_argument("--sans-video", action="store_true",
                   help="pas de vidéo annotée : produit seulement le rapport JSON, la planche "
                        "des personnes et les mesures (CSV et cache), bien plus vite")
    p.add_argument("--noms", help="noms des personnes, par lettre (ex. \"A=Prénom Nom,B=Prénom "
                                  "Nom\") ; les lettres sont sur la planche *_personnes.jpg")
    p.add_argument("--visages", help="dossier de photos de référence nommées « Prénom Nom.jpg » : "
                                     "la personne la plus proche d'une photo prend son nom")
    p.add_argument("--recalculer", action="store_true",
                   help="refait l'analyse du visage même si le fichier *_mesures.npz existe")
    p.add_argument("--debat", action="store_true",
                   help="analyse par personne et attribution de la parole même si une seule "
                        "personne est reconnue (voix hors champ séparée)")
    p.add_argument("--sans-voix", action="store_true",
                   help="dans un débat, attribue la parole par la bouche seule, sans empreinte "
                        "vocale")
    p.add_argument("--dossier-videos",
                   help="où enregistrer une vidéo donnée par son adresse (défaut : dossier "
                        "« videos » à côté du dossier de sortie)")
    p.add_argument("--demander-noms", action="store_true",
                   help="après l'identification, ouvre la planche et demande en console le nom "
                        "des participants sans nom (sans effet si l'entrée n'est pas un terminal)")
    a = p.parse_args()
    if a.visages and not os.path.isdir(a.visages):
        raise SystemExit(f"--visages : dossier introuvable : {a.visages}")
    noms = identite.lire_noms(a.noms)

    os.makedirs(a.sortie, exist_ok=True)
    source = None
    if telechargement.est_url(a.video):
        dossier = a.dossier_videos or os.path.join(os.path.dirname(os.path.abspath(a.sortie)),
                                                    "videos")
        a.video, source = telechargement.telecharger(a.video.strip(), dossier)
    elif not os.path.isfile(a.video):
        raise SystemExit(f"Vidéo introuvable : {a.video}")
    nom = os.path.splitext(os.path.basename(a.video))[0]
    racine = os.path.join(a.sortie, nom)
    titre = os.path.basename(a.video)

    # Les mesures image par image sont gardées dans *_mesures.npz : une relance (noms, autre
    # passage rendu) ne refait pas l'analyse du visage.
    debut_chrono = time.time()
    cle = analyse.cle_cache(a.video, a.debut, a.duree, a.max_visages, a.modele)
    fichier_mesures = racine + "_mesures.npz"
    v = None if a.recalculer else analyse.charger(fichier_mesures, cle, a.video)
    if v is not None:
        print(f"1/4  Mesures relues dans {os.path.basename(fichier_mesures)} "
              "(--recalculer pour refaire l'analyse)", file=sys.stderr)
        source_mesures = "relues dans le fichier de mesures"
    else:
        print("1/4  Suivi des visages et mesures image par image…", file=sys.stderr)
        v = analyse.analyser(a.video, a.modele, a.max_visages, a.debut, a.duree)
        analyse.enregistrer(v, fichier_mesures, cle)
        source_mesures = "calculées"
    duree_mesures = time.time() - debut_chrono
    m = analyse.vue_dominante(v)

    print("2/4  Qui est qui…", file=sys.stderr)
    # Pistes coupées là où elles changent de personne : pour l'identité seulement (la vue du
    # visage dominant, ci-dessus, reste celle de la 0.4).
    v, coupures = identite.separer_pistes(v)
    ident = identite.regrouper(v)
    ident["details"]["pistes_coupees"] = [
        {"piste": c["piste"], "temps": rendu.tc(a.debut + c["image"] / m.fps),
         "temps_s": round(a.debut + c["image"] / m.fps, 2), "similarite": c["similarite"]}
        for c in coupures]
    photos = identite.empreintes_photos(a.visages, a.modele) if a.visages else []
    noms_et_photos = identite.nommer_photos(ident, photos)

    print("3/4  Voix, parole et calcul des écarts…", file=sys.stderr)
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
    croise = croisement.croiser(m, s, texte)
    multi = a.debat or len(ident["personnes"]) > 1
    son_brut = None
    if multi and texte and not a.sans_voix:
        son_brut = audio.brut(a.video, a.debut, m.n / m.fps)
        son_brut = son_brut if son_brut.size >= audio.FREQ else None
    titre_planche = f"{titre}  {rendu.tc(a.debut)} – {rendu.tc(a.debut + m.n / m.fps)}"

    def demander(ident_, parole_):
        """--demander-noms : planche provisoire ouverte, puis un nom par lettre en console."""
        if not any(not q["nom"] and q["id"] not in noms for q in ident_["personnes"]):
            return {}
        identite.planche(v, ident_, racine + "_personnes.jpg", titre_planche, parole_)
        print(f"\nPlanche des personnes : {racine}_personnes.jpg", file=sys.stderr)
        try:
            os.startfile(os.path.abspath(racine + "_personnes.jpg"))
        except (AttributeError, OSError):
            pass
        return identite.saisir_noms(ident_, noms,
                                    ecrire=lambda t: print(t, file=sys.stderr))

    interactif = a.demander_noms and _console_interactive()
    debat = personnes.analyser(v, ident, m, s, croise, son, base, texte, a.debat, son_brut,
                               noms, demander if interactif else None)
    noms_et_photos += debat.noms if debat else identite.nommer_lettres(ident, noms)
    identite.finaliser_compte_rendu(noms_et_photos)
    identite.planche(v, ident, racine + "_personnes.jpg", titre_planche,
                     {p.id: p.temps_parole_s for p in debat.personnes} if debat else {})

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
    for x in noms_et_photos:
        if not x["retenue"]:
            alertes.append(f"Nom non attribué ({x.get('photo') or x.get('noms')}) : {x['raison']}.")
    if debat:
        for pers in debat.personnes:
            if pers.s is None:
                alertes.append(f"Personne {pers.etiquette} : pas assez de données "
                               f"({pers.temps_fiable_s:.0f} s d'images fiables, il en faut "
                               f"{signaux.TEMPS_MIN_BASE:.0f}).")
        repartie = locuteurs.repartition(debat.morceaux)
        total = sum(repartie.values())
        hors = repartie.get(locuteurs.HORS_CHAMP, 0.0)
        if debat.mode == "une personne" and total and hors / total >= 0.25 \
                and repartie.get(debat.personnes[0].id, 0.0) / total >= 0.25:
            alertes.append(f"{100 * hors / total:.0f} % de la parole est dite pendant que la "
                           "bouche de la personne reconnue ne bouge pas : une voix hors champ "
                           "est peut-être comptée avec elle. Relancer avec --debat pour la "
                           "séparer.")
    rapport = {
        "outil": f"facescope {VERSION}",
        "video": os.path.basename(a.video),
        "source": source or {"fichier": os.path.abspath(a.video)},
        "extrait": {"debut_s": a.debut, "duree_s": round(m.n / m.fps, 2), "images": m.n,
                    "images_par_seconde": round(m.fps, 3), "plans": len(m.coupes) + 1},
        "avertissement": rendu.AVERTISSEMENT,
        "limites": LIMITES,
        "alertes": alertes,
        "ligne_de_base": s.base,
        "moments_atypiques": personnes.moments(s, a.debut),
        "figements": personnes.figements(s, a.debut),
        "ecarts_simultanes": personnes.ecarts_simultanes(s, a.debut),
        "parole": parole.lexique(texte),
        "croisement": croise,
        "analyse": elements,
        "transcription": [{"temps_s": round(a.debut + p["debut"], 2), "texte": p["texte"]}
                          for p in (texte or {}).get("phrases", [])],
        "mouvements_brefs": [{"temps": rendu.tc(a.debut + b["t"]),
                              "temps_s": round(a.debut + b["t"], 2),
                              "duree_s": round(b["duree"], 2), "unite": b["code"],
                              "nom": b["nom"], "z": b["z"]} for b in s.brefs],
        "portee": PORTEE,
        "mesures": {"source": source_mesures, "fichier": os.path.basename(fichier_mesures),
                    "duree_s": round(duree_mesures, 1)},
    }
    if debat:
        rapport.update(personnes.rapport(debat, ident, a.debut, noms_et_photos))
    else:
        rapport.update({"mode": "aucune personne reconnue", "personnes": [],
                        "identite": {"modele": identite.MODELE_EMPREINTE, **ident["details"],
                                     "noms_et_photos": noms_et_photos}})
    with open(racine + "_rapport.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    if not a.sans_video:
        print("4/4  Rendu de la vidéo annotée…", file=sys.stderr)
        passage = None
        if a.rendu:
            passage = (max(0, int((a.rendu[0] - a.debut) * m.fps)),
                       min(m.n, int((a.rendu[1] - a.debut) * m.fps)))
        if a.format == "vertical":
            rendu_vertical.rendre(m, s, racine + "_facescope_vertical.mp4", titre, passage,
                                  elements, croise, debat)
        else:
            rendu.rendre(m, s, racine + "_facescope.mp4", titre, passage)

    lignes = _resume(a, m, s, croise, debat, ident, coupures, alertes, racine, source_mesures,
                     duree_mesures)
    bilan = racine + "_bilan.txt"
    with open(bilan, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(_entete(a.video, source) + lignes) + "\n")
    print("\n".join(lignes[:-1] + [f"Bilan : {bilan}", lignes[-1]]))


def _console_interactive() -> bool:
    """Vrai si l'entrée est un terminal où quelqu'un peut taper. Sous Windows, isatty() est
    vrai aussi pour NUL (entrée redirigée vers le vide) : on vérifie que c'est une console."""
    try:
        if sys.stdin is None or not sys.stdin.isatty():
            return False
        if os.name != "nt":
            return True
        import ctypes
        import msvcrt
        mode = ctypes.c_uint32()
        poignee = msvcrt.get_osfhandle(sys.stdin.fileno())
        return bool(ctypes.windll.kernel32.GetConsoleMode(poignee, ctypes.byref(mode)))
    except (OSError, ValueError, AttributeError):
        return False


def _entete(video: str, source: dict | None) -> list:
    """Début du bilan : la source, la date de l'analyse, la version."""
    lignes = [f"FACESCOPE {VERSION} · BILAN"]
    if source:
        lignes.append(f"Source : {source.get('url')}")
        for cle, nom in (("titre", "Titre"), ("chaine", "Chaîne"), ("date", "Mise en ligne")):
            if source.get(cle):
                lignes.append(f"{nom} : {source[cle]}")
        lignes.append(f"Fichier : {os.path.abspath(video)}")
    else:
        lignes.append(f"Source : {os.path.abspath(video)}")
    lignes.append(f"Analyse du {datetime.datetime.now():%d/%m/%Y à %H:%M}, facescope {VERSION}.")
    return lignes


def _resume(a, m, s, croise, debat, ident, coupures, alertes, racine, source_mesures,
            duree_mesures) -> list:
    """Le résumé de fin, en lignes de texte : affiché en console et écrit dans le bilan."""
    lignes = []
    out = lignes.append
    out(f"\nExtrait de {m.n / m.fps:.0f} s, {len(m.coupes) + 1} plans, visage exploitable sur "
        f"{s.base['images_exploitables_pct']} % des images. Mesures du visage "
        f"{source_mesures} en {duree_mesures:.0f} s.")
    for alerte in alertes:
        out("ATTENTION : " + alerte)
    if debat and debat.mode == "débat":
        public = debat.public["personnes"] if debat.public else []
        out(f"Débat : {len(debat.personnes)} participants ("
            + ", ".join(f"{q.id}" + (f" = {q.nom}" if q.nom else "") for q in debat.personnes)
            + f"), public : {len(public)} personnes, {len(ident['autres']['pistes'])} autres "
            f"visages, {len(coupures)} pistes coupées. Planche : {racine}_personnes.jpg")
        lignes.extend(personnes.resume(debat, a.debut))
        out(f"\nFichiers : {racine}_*")
        out(rendu.AVERTISSEMENT)
        return lignes
    if debat:
        q = debat.personnes[0]
        out(f"Une personne reconnue : {q.id}" + (f" = {q.nom}" if q.nom else "")
            + f", {q.temps_image_s:.0f} s à l'image. Planche : {racine}_personnes.jpg")
    else:
        out("Aucune personne reconnue (visages absents, trop brefs ou jamais de face).")
    out(f"{len(s.moments)} moments atypiques, {len(s.figements)} figements, "
        f"{len(s.convergences)} écarts simultanés sur plusieurs canaux, "
        f"{len(s.brefs)} mouvements brefs.")
    for k, mo in enumerate(s.moments):
        causes = ", ".join(f"{x['nom']} ({x['z']:+.1f})" for x in mo["signaux"])
        out(f"  {k + 1}. {rendu.tc(a.debut + mo['t'])}  écart {mo['ecart']:.1f}  {causes}")
    synthese = croise["synthese"]
    out(f"\nCroisement : {synthese['passages']} passages ("
        + ", ".join(f"{o} {nb}" for o, nb in synthese["repartition"].items() if nb) + ").")
    if synthese["themes"] and not synthese["classement"]:
        out(f"  Aucun thème assez long pour un classement (minimum "
            f"{croisement.TEMPS_THEME_MIN:.0f} s et {croisement.PASSAGES_THEME_MIN} passages "
            "mesurés).")
    for sens in ("s'anime", "se retient"):
        themes = synthese["plus_marques"][sens][:3]
        if themes:
            out(f"  Thèmes où la personne {sens} le plus : "
                + ", ".join(f"{t['theme']} ({t['part_pct']} % du temps)" for t in themes))
    out("  Passages les plus marqués :")
    for p in synthese["passages_marques"]:
        out(f"    {p['temps']}  écart {p['ecart_moyen']:.1f}  {p['orientation']:<10}  "
            f"{p['sujet'] or '-'}")
    out(f"Fichiers : {racine}_*")
    out(rendu.AVERTISSEMENT)
    return lignes


if __name__ == "__main__":
    main()
