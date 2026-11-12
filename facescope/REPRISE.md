# Reprise du projet Facescope

Note de passation écrite le 12 novembre 2026, pour reprendre le travail dans une autre
session sans rien redécouvrir. Le détail d'usage est dans [README.md](README.md), les
sources scientifiques dans [RECHERCHE.md](RECHERCHE.md).

## Le projet en une phrase

Une vidéo d'un responsable politique en entrée ; en sortie, la même vidéo entourée de
mesures (visage, voix, parole) et d'un bloc d'analyse du discours et des faits, au format
paysage ou vertical 9:16 pour les réseaux sociaux.

## Décisions prises

- **Pas de détecteur de mensonge.** La recherche ne le valide pas (voir RECHERCHE.md).
  L'outil n'affiche jamais « il ment » ni « il pense X ».
- **La cible est la déstabilisation** : plusieurs canaux (visage, mobilité, regard, voix,
  parole) qui s'écartent en même temps de l'habitude de la personne. Pas « sourire = content ».
- **L'outil mesure, l'analyse se rédige à part.** Le fond (discours, véracité) vient d'un
  fichier JSON que le rendu affiche au bon moment. Aujourd'hui ce fichier est écrit à la
  main, avec recherche de sources.
- **Chaque mesure est comparée à la personne elle-même** (médiane et dispersion dans la
  vidéo), jamais à une norme générale.
- Le plan « gros modèle à 2 500 mesures » a été écarté tant qu'il n'y a pas d'exemples
  annotés : on commence petit, on mesure la précision, on grossit ensuite.

## Où est le code

- Dépôt `Aycotek/Aycotek`, dossier `facescope/`.
- Branche de travail : `claude/facial-expression-truthfulness-analysis-dnnalj`.
- Pull request n° 8, en brouillon : versions 0.2 et 0.3. La branche par défaut
  (`feat/dynamic-planet-zoom`) ne contient que la version 0.1 tant que la n° 8 n'est pas
  fusionnée.

| Fichier | Rôle |
|---|---|
| `facescope/analyse.py` | Plans, recherche des visages par tuiles, suivi par zoom, 52 coefficients par image |
| `facescope/audio.py` | Hauteur et énergie de la voix |
| `facescope/parole.py` | Transcription horodatée, débit, silences, hésitations, lexique |
| `facescope/signaux.py` | Écarts à la ligne de base, figements, moments atypiques, écarts simultanés |
| `facescope/rendu.py` | Rendu paysage 1920 x 1080 |
| `facescope/rendu_vertical.py` | Rendu vertical 1080 x 1920, analyse en haut, vidéo dessous |
| `facescope/__main__.py` | Commande et rapport |

## Lancer

```bash
pip install -r requirements.txt        # + ffmpeg ; sous Linux : libegl1 libgles2
python -m facescope video.mp4 --format vertical --analyse analyse.json --rendu 3:15-4:45
```

Au premier lancement, deux modèles sont téléchargés : le visage (3,7 Mo, Google) et la
transcription (1,6 Go, Hugging Face).

## Ce qui a été testé

- Film libre Tears of Steel (12 min, 172 plans) : suivi validé sur les changements de plan.
- Trois vidéos d'Emmanuel Macron en 640 x 360 :
  - allocution du 18 octobre 2026 (8 min 30, visage de 75 px) : exploitable à 97,6 %,
    8 moments atypiques, 3 figements, 6 écarts simultanés, 1 336 mots transcrits ;
  - allocution de 5 min (visage de 70 px) : exploitable à 96 % ;
  - déclaration au pupitre (visage de 53 px) : refusée, visage trop petit.
- Un fichier d'analyse de 16 éléments a été rédigé pour l'allocution du 18 octobre
  (verdicts sourcés). Il n'est pas dans le dépôt : il a été remis à Arthur et doit être
  relu avant toute publication, car il a été écrit à partir de résumés de recherche, sans
  lecture des articles complets.

## Ce qu'on a appris

- **La résolution est le premier frein.** Il faut un visage d'au moins 120 pixels, donc
  du 720p ou du 1080p. En 360p la voix est stable d'une vidéo à l'autre (131 et 132 Hz),
  pas le visage.
- **Une allocution lue ne déstabilise personne** : zéro hésitation, et les écarts du visage
  tombent sur les phrases appuyées. Le bon terrain est l'interview aux questions non préparées.
- Le modèle de visage (MediaPipe) laisse 5 mouvements sur 17 à zéro (AU6, 9, 10, 15, 20).
  La lecture des expressions types est la partie la plus faible.
- La transcription efface souvent les « euh » et ne distingue pas les voix : un silence
  entre le journaliste et l'invité est compté comme une pause.
- L'indice global est une moyenne sur les familles : ajouter « Parole » le fait baisser
  quand la parole est régulière. Seuils (2 pour un moment, 1 pour un figement) réglés à la
  main sur deux vidéos.

## Contraintes rencontrées dans la session cloud

- YouTube renvoie les serveurs vers sa page anti-robot : pas de téléchargement possible,
  même réseau ouvert. Seule la fiche publique d'une vidéo (titre, chaîne) est lisible.
- L'environnement « Oui » autorise YouTube (4 adresses) et Hugging Face (5 adresses).
  Tout autre site est bloqué pour la lecture de pages ; la recherche web fonctionne.
- Dépôt de fichiers limité à 30 Mo. Le connecteur Google Drive ne sait pas transmettre
  une vidéo.
- Le conteneur est temporaire : paquets et modèles sont à réinstaller à chaque session.
- Dans une session sur l'ordinateur d'Arthur, ces limites tombent : les vidéos HD sont
  lues sur le disque, et Claude in Chrome peut ouvrir les articles complets.

## Données pour entraîner et évaluer

- **BAH** (ICLR 2026) : 300 personnes à la webcam, 1 427 vidéos, 10,6 heures, passages
  d'hésitation marqués par des experts, transcriptions horodatées. Le plus proche de la
  cible. Accès à demander par Arthur : https://github.com/LIVIAETS/bah-dataset
- **StressID** : stress provoqué, avec signaux physiologiques. Licence propriétaire.
- **MELD** : écarté (répliques jouées de la série Friends, étiquetées en émotions).
- Aucun jeu de données public ne porte sur des responsables politiques.

## À faire, dans l'ordre

1. Relecture par Arthur du fichier d'analyse du 18 octobre, sources ouvertes une à une.
2. Tester sur une interview en 720p ou plus, avec des questions non préparées.
3. Reconnaître qui est qui (ligne de base par personne, voix séparées) pour les
   interviews à deux.
4. Produire le fichier d'analyse automatiquement (extraction des affirmations, recherche
   de sources), toujours avec relecture humaine.
5. Constituer 20 à 30 extraits politiques annotés par des humains (« perd-il sa contenance
   ici ? ») et mesurer la précision de l'outil dessus. Sans cela, aucun pourcentage affiché
   n'est défendable.
6. Comparer MediaPipe à un moteur plus précis pour le visage (OpenFace 3.0, LibreFace).
7. Ajouter des tests automatisés et factoriser le tracé de la courbe, dupliqué entre les
   deux rendus.

## Points de vigilance avant publication

- Diffamation si un verdict est faux ou mal sourcé.
- Droits des chaînes sur les images reprises.
- Règlement européen sur l'IA pour la reconnaissance des émotions : non vérifié en détail.
- Garder la mention « Cet outil mesure des mouvements. Il n'indique pas si la personne
  ment ni ce qu'elle pense. »
