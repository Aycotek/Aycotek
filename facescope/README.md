# Facescope

Une vidéo en entrée. En sortie : la même vidéo avec un encadré qui mesure, image par
image, ce que fait le visage de la personne qui parle.

**Ce que l'outil fait.** Il suit le visage, zoome dessus, mesure les mouvements des
muscles, de la tête, du regard et la voix, puis signale les moments où la personne
s'écarte de son propre comportement habituel.

**Ce que l'outil ne fait pas.** Il ne dit pas si la personne ment ni ce qu'elle pense.
La recherche ne valide pas la détection du mensonge par le visage (voir
[RECHERCHE.md](RECHERCHE.md)). Un moment atypique est un endroit où regarder de plus près
et où vérifier ce qui a été dit, rien de plus.

## Installation

```bash
pip install -r requirements.txt
# + ffmpeg ; sous Linux : apt-get install -y ffmpeg libegl1 libgles2
```

## Utilisation

```bash
python -m facescope interview.mp4
python -m facescope interview.mp4 --debut 2:00 --duree 1:30     # un extrait
python -m facescope interview.mp4 --base 0:10-0:40              # passage calme de référence
```

Trois fichiers sont créés dans `resultats/` :

| Fichier | Contenu |
|---|---|
| `*_facescope.mp4` | La vidéo annotée (1920 x 1080, son d'origine) |
| `*_rapport.json` | Moments atypiques, mouvements brefs, ligne de base, limites |
| `*_mesures.csv` | Toutes les mesures, une ligne par image |

Compter environ deux fois la durée de la vidéo (mesuré : 45 s traitées en 1 min 30 sur 4 cœurs).

![Exemple de rendu](docs/exemple.jpg)

## Comment ça marche

1. **Plans.** Les changements de plan sont détectés ; le suivi repart de zéro à chacun.
2. **Recherche.** Les visages sont cherchés sur l'image entière, puis par tuiles pour
   trouver les visages lointains.
3. **Zoom.** Chaque visage connu est recadré serré avant analyse. Le visage dominant de
   chaque plan est retenu.
4. **Muscles.** 52 coefficients par image (MediaPipe Face Landmarker), regroupés en
   17 unités d'action proches du système FACS.
5. **Voix.** Hauteur et énergie, comptées seulement quand la personne suivie parle.
6. **Écart.** Chaque signal est comparé à la médiane de la personne dans la vidéo
   (ou dans le passage `--base`). L'indice vaut environ 1 quand tout est habituel ;
   au-dessus de 2, le moment est signalé.

## Lire l'encadré

- **Expression affichée** : ressemblance à une configuration type (sourire, surprise,
  froncement, tristesse, dégoût, peur). Ce n'est pas l'émotion ressentie.
- **Mouvements du visage** : longueur de barre = intensité, couleur = écart à la ligne de
  base (vert habituel, orange au-dessus de 2, rouge au-dessus de 3,5).
- **Écart à sa ligne de base** : l'indice global, son rang dans la vidéo, et le détail
  par famille (visage, tête, regard, voix).
- **Mouvement bref** : une unité d'action qui s'active moins d'une demi-seconde.
- **Courbe du bas** : l'indice sur toute la durée, avec les changements de plan et les
  moments les plus atypiques.

## Limites connues

- Une seule personne suivie par plan. Dans une interview à deux, la ligne de base peut
  mélanger le candidat et le journaliste. Tant que ce n'est pas réglé, travailler sur des
  extraits où une seule personne est à l'image.
- Les unités d'action sont approchées par un modèle généraliste, pas codées par un expert.
- À 25 images par seconde, un mouvement de moins de 80 ms n'est vu que sur 1 ou 2 images.
  La compression des vidéos en ligne dégrade encore ce niveau de détail.
- Testé sur un film de fiction (Tears of Steel), pas encore sur une vraie interview
  politique. La précision des mesures n'a pas été comparée à un codage humain.
- Pas encore de transcription ni de vérification des affirmations.

## Suite prévue

1. Reconnaître qui est qui d'un plan à l'autre (ligne de base par personne).
2. Transcrire la parole et aligner le texte sur les moments atypiques.
3. Extraire les affirmations vérifiables et les confronter à des sources.

## Crédits

Image d'exemple : *Tears of Steel*, (CC) Blender Foundation, mango.blender.org, licence
CC BY 3.0.
