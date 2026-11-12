"""Prosodie de la voix : hauteur (F0) et énergie, 100 mesures par seconde."""
from __future__ import annotations

import subprocess
import warnings

import numpy as np

FREQ = 16000
PAS = 160          # 10 ms
FENETRE = 640      # 40 ms
F0_MIN, F0_MAX = 75.0, 400.0


def extraire(chemin: str, debut: float = 0.0, duree: float | None = None) -> dict | None:
    """Renvoie {'f0': Hz ou NaN, 'db': dBFS, 'pas': secondes} ou None s'il n'y a pas de son."""
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{debut:.3f}"]
    if duree:
        cmd += ["-t", f"{duree:.3f}"]
    cmd += ["-i", chemin, "-vn", "-ac", "1", "-ar", str(FREQ), "-f", "s16le", "-"]
    brut = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(brut, np.int16).astype(np.float32) / 32768.0
    if x.size < FENETRE * 4:
        return None

    nb = 1 + (x.size - FENETRE) // PAS
    idx = np.arange(FENETRE)[None, :] + PAS * np.arange(nb)[:, None]
    trames = x[idx]
    db = 20 * np.log10(np.sqrt((trames ** 2).mean(axis=1)) + 1e-9)

    # Autocorrélation normalisée (via FFT) pour estimer la hauteur de la voix.
    fen = trames * np.hanning(FENETRE)[None, :]
    fen = fen - fen.mean(axis=1, keepdims=True)
    spectre = np.fft.rfft(fen, 2 * FENETRE, axis=1)
    ac = np.fft.irfft(spectre * np.conj(spectre), axis=1)[:, :FENETRE]
    ac = ac / np.maximum(ac[:, :1], 1e-12)
    lag_min, lag_max = int(FREQ / F0_MAX), int(FREQ / F0_MIN)
    zone = ac[:, lag_min:lag_max]
    pic = zone.argmax(axis=1)
    force = zone[np.arange(nb), pic]
    f0 = FREQ / (pic + lag_min).astype(float)

    seuil_db = max(np.percentile(db, 95) - 30.0, -55.0)
    voise = (force > 0.5) & (db > seuil_db)
    f0[~voise] = np.nan
    # Filtre médian court pour retirer les sauts d'octave isolés.
    if nb >= 5 and np.isfinite(f0).any():
        pile = np.stack([np.roll(f0, d) for d in (-2, -1, 0, 1, 2)])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            f0 = np.where(np.isnan(f0), np.nan, np.nanmedian(pile, axis=0))
    return {"f0": f0, "db": db, "pas": PAS / FREQ}


def sur_images(audio: dict | None, t: np.ndarray, demi: float = 0.5):
    """Ramène la voix sur la grille des images vidéo (médiane sur +/- demi seconde)."""
    n = len(t)
    f0, db = np.full(n, np.nan), np.full(n, np.nan)
    if audio is None:
        return f0, db
    pas, nb = audio["pas"], len(audio["db"])
    for i, ti in enumerate(t):
        a, b = max(0, int((ti - demi) / pas)), min(nb, int((ti + demi) / pas) + 1)
        if b - a < 5:
            continue
        seg = audio["f0"][a:b]
        voise = np.isfinite(seg)
        if voise.mean() >= 0.2:
            f0[i] = np.median(seg[voise])
        db[i] = audio["db"][a:b].mean()
    return f0, db
