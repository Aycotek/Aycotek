"""Parole : transcription horodatée, débit, pauses, hésitations et lexique.

La transcription est facultative : sans le paquet faster-whisper, l'outil tourne
sans le canal « Parole ».
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter

import numpy as np

HESITATIONS = {"euh", "heu", "euhm", "hum", "hmm", "hm", "ben", "bah", "beh"}
NEGATIONS = {"ne", "n'", "pas", "jamais", "rien", "aucun", "aucune", "non"}
PRONOMS = {
    "je": {"je", "j'", "me", "m'", "moi", "mon", "ma", "mes"},
    "nous": {"nous", "notre", "nos", "on"},
    "vous": {"vous", "votre", "vos"},
    "ils": {"ils", "elles", "eux", "leur", "leurs", "ceux", "celles"},
}
VIDES = set("""
le la les l' un une des du de d' au aux et ou où mais donc or ni car que qu' qui quoi dont
ce cet cette ces c' se s' sa son ses leur leurs je j' tu il elle on nous vous ils elles me m'
te t' lui y en ne n' pas plus est sont a ont été être avoir à dans par pour sur avec sans
sous vers chez entre comme si tout tous toute toutes très bien aussi alors ainsi cela ça là
ici fait faire dit dire peut doit faut suis sommes êtes avez avons ai as était étaient sera
seront serait même mêmes autre autres quand parce puis encore déjà depuis lors celui celle
ceux celles mon ma mes ton ta tes notre nos votre vos eux aujourd'hui hui jusqu' lorsqu'
puisqu' quelqu' quelque quelques chaque après avant contre face trop peu cette leurs
""".split())
CHIFFRE = re.compile(r"\d|%|\b(deux|trois|quatre|cinq|six|sept|huit|neuf|dix|vingt|trente|"
                     r"quarante|cinquante|soixante|cents?|mille|dizaines?|centaines?|milliers?|"
                     r"millions?|milliards?|pour cent)\b", re.IGNORECASE)
AMORCE = "Euh, alors, hum, ben, je... je veux dire que, enfin, voilà."
MOT = re.compile(r"[a-zàâäçéèêëîïôöùûüœæ0-9-]+'?")


def transcrire(chemin: str, debut: float = 0.0, duree: float | None = None, langue: str = "fr",
               modele: str = "large-v3-turbo", cache: str | None = None) -> dict | None:
    """Renvoie {'mots': [{mot, debut, fin, proba}], 'phrases': [{texte, debut, fin}]} ou None."""
    if cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    try:
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        from faster_whisper import WhisperModel
    except ImportError:
        print("  (paquet faster-whisper absent : pas d'analyse de la parole)", file=sys.stderr)
        return None
    # Le son est décodé par ffmpeg et passé directement au modèle (16 kHz, mono).
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{debut:.3f}"]
    if duree:
        cmd += ["-t", f"{duree:.3f}"]
    cmd += ["-i", chemin, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"]
    son = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.int16)
    if son.size < 16000:
        return None
    moteur = WhisperModel(modele, device="cpu", compute_type="int8")
    segments, _ = moteur.transcribe(son.astype(np.float32) / 32768.0, language=langue,
                                    word_timestamps=True, vad_filter=True,
                                    condition_on_previous_text=False, initial_prompt=AMORCE)
    mots, phrases = [], []
    for s in segments:
        phrases.append({"texte": s.text.strip(), "debut": round(s.start, 2),
                        "fin": round(s.end, 2)})
        for w in s.words or []:
            mots.append({"mot": w.word.strip(), "debut": round(w.start, 2),
                         "fin": round(w.end, 2), "proba": round(w.probability, 3)})
    resultat = {"langue": langue, "modele": modele, "mots": mots, "phrases": phrases}
    if cache:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False)
    return resultat


def _norme(mot: str) -> str:
    return re.sub(r"[^\w'-]", "", mot.lower().replace("’", "'"))


def sur_images(tr: dict | None, t: np.ndarray):
    """Sur la grille des images : débit (mots/s), silence en cours (s), hésitations par minute."""
    n = len(t)
    vide = np.full(n, np.nan)
    if not tr or len(tr["mots"]) < 5:
        return vide, vide.copy(), vide.copy()
    d = np.array([m["debut"] for m in tr["mots"]])
    f = np.array([m["fin"] for m in tr["mots"]])
    normes = [_norme(m["mot"]) for m in tr["mots"]]
    marque = np.array([w in HESITATIONS or (i > 0 and w == normes[i - 1] and len(w) > 1)
                       for i, w in enumerate(normes)])
    centres = (d + f) / 2
    debit, pause, hesit = np.zeros(n), np.zeros(n), np.zeros(n)
    for i, ti in enumerate(t):
        a, b = np.searchsorted(centres, [ti - 2.5, ti + 2.5])
        debit[i] = (b - a) / 5.0
        a, b = np.searchsorted(centres, [ti - 10, ti + 10])
        hesit[i] = marque[a:b].sum() * 3.0
        k = np.searchsorted(d, ti)
        if 0 < k < len(d) and ti >= f[k - 1] and d[k] - f[k - 1] >= 0.25:
            pause[i] = d[k] - f[k - 1]
    return debit, pause, hesit


def silences(tr: dict | None) -> np.ndarray:
    """Durées des silences entre deux mots (au moins un quart de seconde)."""
    if not tr or len(tr["mots"]) < 2:
        return np.array([])
    ecarts = np.array([b["debut"] - a["fin"] for a, b in zip(tr["mots"][:-1], tr["mots"][1:])])
    return ecarts[ecarts >= 0.25]


def phrase_a(tr: dict | None, instant: float) -> str:
    """Phrase en cours à cet instant (ou la dernière terminée depuis moins de 1,5 s)."""
    if not tr:
        return ""
    for p in tr["phrases"]:
        if p["debut"] - 0.2 <= instant <= p["fin"] + 1.5:
            return p["texte"]
    return ""


def lexique(tr: dict | None) -> dict | None:
    """Chiffres clés du texte : volume, débit, mots fréquents, pronoms, phrases à vérifier."""
    if not tr or not tr["mots"]:
        return None
    jetons = [j for p in tr["phrases"] for j in MOT.findall(p["texte"].lower().replace("’", "'"))]
    if not jetons:
        return None
    duree = max(tr["mots"][-1]["fin"] - tr["mots"][0]["debut"], 1.0)
    pleins = [j for j in jetons if j not in VIDES and len(j) > 3 and not j[0].isdigit()]
    normes = [_norme(m["mot"]) for m in tr["mots"]]
    pauses = silences(tr)

    def part(groupe):
        return round(100.0 * sum(j in groupe for j in jetons) / len(jetons), 1)
    return {
        "mots": len(jetons),
        "debit_mots_par_minute": round(60.0 * len(tr["mots"]) / duree),
        "silences_de_plus_d_une_seconde": int((pauses >= 1.0).sum()),
        "silence_le_plus_long_s": round(float(pauses.max()), 1) if pauses.size else 0.0,
        "hesitations": int(sum(w in HESITATIONS for w in normes)),
        "repetitions": int(sum(i > 0 and w == normes[i - 1] and len(w) > 1
                               for i, w in enumerate(normes))),
        "pronoms_pct": {nom: part(groupe) for nom, groupe in PRONOMS.items()},
        "negations_pct": part(NEGATIONS),
        "mots_frequents": Counter(pleins).most_common(15),
        "phrases_chiffrees": [{"temps_s": p["debut"], "texte": p["texte"]}
                              for p in tr["phrases"] if CHIFFRE.search(p["texte"])],
    }
