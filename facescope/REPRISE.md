# Reprise du projet Facescope

Note de passation écrite le 12 novembre 2026, mise à jour le 14 novembre 2026 (version
0.4) puis le 16 novembre 2026 (version 0.5, débat ; version 0.6, public, habitude par rôle,
classement des thèmes), pour reprendre le travail dans une autre session sans rien redécouvrir. Le détail
d'usage est dans [README.md](README.md), les sources scientifiques dans
[RECHERCHE.md](RECHERCHE.md).

## Le projet en une phrase

Une vidéo d'un responsable politique en entrée ; en sortie, la même vidéo entourée de
mesures (visage, voix, parole) et d'un bloc d'analyse qui croise ce qui est dit avec ce
que montrent les mesures, au format paysage ou vertical 9:16 pour les réseaux sociaux.
Le but, formulé par Arthur : aider le public à voir, pendant un débat, sur quels sujets
un candidat s'écarte de son habitude, et dans quel sens.

## Décisions prises

- **Pas de détecteur de mensonge.** La recherche ne le valide pas (voir RECHERCHE.md).
  L'outil n'affiche jamais « il ment » ni « il pense X ».
- **La cible est la déstabilisation** : plusieurs canaux (visage, mobilité, regard, voix,
  parole) qui s'écartent en même temps de l'habitude de la personne. Pas « sourire = content ».
- **L'outil croise lui-même, la vérification des faits se rédige à part.** Depuis la 0.4,
  le croisement (sujet du passage, écarts par canal, orientation, phrase de lecture) est
  calculé à chaque vidéo, sur l'ordinateur, sans réseau ni service d'IA. La véracité vient
  toujours d'un fichier JSON facultatif (`--analyse`), écrit à la main avec recherche de
  sources.
- **Décrire, ne pas interpréter.** L'outil n'écrit jamais « il ment », « il pense », « ça
  le dérange ». Il dit « la personne s'anime » ou « se retient » (direction de l'écart),
  avec les nombres qui y conduisent ; la cause reste au spectateur.
- **Chaque mesure est comparée à la personne elle-même** (médiane et dispersion dans la
  vidéo), jamais à une norme générale.
- Le plan « gros modèle à 2 500 mesures » a été écarté tant qu'il n'y a pas d'exemples
  annotés : on commence petit, on mesure la précision, on grossit ensuite.

## Où est le code

- Dépôt `Aycotek/Aycotek`, dossier `facescope/`.
- Branche par défaut : `feat/dynamic-planet-zoom`. La pull request n° 8 (versions 0.2 et
  0.3) y est fusionnée.
- Versions 0.4 (croisement, bloc d'analyse agrandi), 0.5 (étape débat) et 0.6 (habitude par
  rôle, public écarté, pistes coupées, silence long à partir de 2 s, son traité par blocs) :
  publiées ensemble sur la branche `facescope-0.6` (pull request vers `feat/dynamic-planet-zoom`).

| Fichier | Rôle |
|---|---|
| `facescope/analyse.py` | Plans, recherche des visages par tuiles, suivi par zoom, 52 coefficients par image |
| `facescope/audio.py` | Hauteur et énergie de la voix |
| `facescope/parole.py` | Transcription horodatée, débit, silences, hésitations, lexique |
| `facescope/signaux.py` | Écarts à la ligne de base, figements, moments atypiques, écarts simultanés ; expose aussi l'écart signé de chaque signal (`details`) |
| `facescope/croisement.py` | Passages de 4 à 15 s, thèmes par mots-clés, écarts par passage, orientation, lecture, synthèse par thème |
| `facescope/rendu.py` | Rendu paysage 1920 x 1080 (inchangé en 0.4) |
| `facescope/rendu_vertical.py` | Rendu vertical 1080 x 1920 : bloc d'analyse de 800 px, vidéo pleine largeur, courbe, bande des mesures brutes |
| `facescope/__main__.py` | Commande et rapport (clé `croisement`) |

## Ce que la version 0.4 ajoute

- **Croisement automatique** (`croisement.py`, fonctions pures) : la transcription est
  découpée en passages de 4 à 15 s ; chaque passage reçoit un ou deux thèmes parmi quinze
  (lexique de mots-clés écrit à la main), sinon ses mots distinctifs ; ses écarts sur les
  images fiables (global, par canal, signaux les plus forts avec leur signe, moments,
  figement, écart simultané, débit, silence) ; une orientation (s'anime, se retient, mixte,
  habituel, non mesuré) avec chaque critère, sa valeur et son seuil ; une phrase de lecture.
  Synthèse par thème et passages les plus marqués. La règle est écrite en tête du module et
  recopiée dans le rapport (`croisement.regle`).
- **Rendu vertical refait** : en-tête fin, bloc d'analyse de 800 px (pastille
  d'orientation, écart et rang, sujet, citation, tableau des cinq canaux, lecture, puis
  élément `--analyse` ou sujets les plus marqués, légende), vidéo 1080 x 608, courbe avec
  le passage affiché encadré, bande compacte des mesures brutes. Le bloc est dessiné une
  fois par passage : il ne clignote pas.
- **Rapport et console** : clé `croisement` dans le JSON, synthèse affichée en fin
  d'exécution. Le format paysage et le CSV ne changent pas.

## Ce que la version 0.5 ajoute (16 novembre 2026, non commitée)

Le débat : qui est qui, qui parle, une analyse par personne. Détail des règles et seuils
dans README.md (« Débat : qui est qui, qui parle »).

| Fichier | Rôle en 0.5 |
|---|---|
| `analyse.py` | Garde tous les visages suivis (`Visages`), calcule les empreintes faciales pendant le suivi ; `vue_dominante` (exactement la 0.4) et `vue_personne` ; cache `*_mesures.npz` ; téléchargement contrôlé par SHA-256 |
| `identite.py` (nouveau) | Modèle SFace, regroupement des pistes en personnes, noms (`--noms`, `--visages`), planche `*_personnes.jpg` |
| `locuteurs.py` (nouveau) | Qui parle : bouche, puis voix (WeSpeaker, fbank Kaldi réécrit en numpy) ; tours de parole et transcription par personne |
| `personnes.py` (nouveau) | Mode « une personne » (= 0.4) ou « débat » ; vue, signaux, croisement et synthèse par personne ; personne lue et autres personnes par passage ; rapport et console |
| `signaux.py` | `fiable` et `bouche_en_mouvement` sortis de `calculer` ; option `voix` (images où la parole est attribuée à la personne) ; `TEMPS_MIN_BASE` = 20 s |
| `parole.py` | Débit et hésitations rapportés au temps de parole de la personne, silences coupés aux changements de tour (seulement si la transcription porte des « tours ») |
| `croisement.py` | Passages coupés aux changements de locuteur ; `croiser_personne` (rôle parle / écoute, critères réduits au visage, à la mobilité et au regard pour qui écoute) ; `passage_vide` |
| `rendu_vertical.py` | Personne lue et rôle, lignes des autres personnes, étiquettes sur les visages, courbe de la personne lue, sujets de la personne lue |
| `audio.py` | `brut` : le son à 16 kHz pour l'empreinte vocale |
| `__main__.py` | Options `--noms`, `--visages`, `--recalculer`, `--debat`, `--sans-voix` ; clés `portee`, `mesures`, `mode`, `personnes`, `autres_visages`, `identite`, `locuteurs` |

`rendu.py` (paysage) n'a pas changé : il reste centré sur le visage dominant de chaque plan.

Modèles ajoutés (téléchargés dans `~/.cache/facescope`, adresse figée à un commit,
SHA-256 contrôlé à chaque lancement) :
- SFace 2021dec, OpenCV Zoo, 38,7 Mo, Apache 2.0 (données d'entraînement non nommées
  par le dépôt) ;
- WeSpeaker ResNet34-LM, Hugging Face (organisation Wespeaker), 26,5 Mo, CC BY 4.0
  (citer WeSpeaker en cas de publication ; entraîné sur VoxCeleb).

Testé le 15 novembre 2026 :
- Maréchal / Villepin (`EE7i6JbRCAQ`, 7:00-10:30, 13 plans, écran partagé, plans
  larges) : 4 personnes (A Maréchal, B Villepin, C et D deux personnes du public
  derrière eux), 4 autres visages ; une personne par groupe, aucune coupée en deux.
  Photos de référence prises hors de l'extrait : A et B nommés (similarité 0,63 et 0,79).
  Parole contrôlée sur 14 morceaux (images et texte) : 12 justes, 2 « indéterminé »
  (parole croisée), 0 faux. Mesures 5 min 46 sans cache, relance 13 s avec.
- Lisnard / Roussel (`tbTk-dHEQnw`, 7:00-10:00) : A Lisnard, B le modérateur, C Roussel,
  27 visages lointains en « autres » ; les questions du modérateur hors champ lui sont
  attribuées par la voix ; relu sur la transcription, pas d'erreur vue.
- Non-régression contre la copie 0.4 (allocution, 3:30 + 25 s, 1:00-3:00, 3:00-5:00) :
  moments atypiques, orientations, toutes les clés de la 0.4 et le CSV identiques ; seuls
  `outil` et `limites` changent.
- Cas limites : vidéo sans visage, extrait d'une image, extraits de 3 et 8 s, `--sans-parole`,
  `--sans-video` : pas d'erreur ; sous 20 s, « pas assez de données ».

Fragile : seuils de regroupement (0,6) et de parole (bouche 0,5 / 0,2, voix 0,5 / 0,2)
réglés sur ces deux extraits ; parole croisée ; lettres qui changent d'un extrait à
l'autre ; rendu paysage non adapté au débat.

## Ce que la version 0.6 corrige (16 novembre 2026, non commitée)

Trois défauts vus sur le débat Maréchal–Villepin entier (`EE7i6JbRCAQ`, 50 min, 0.5 dans
`facescope-analyses\resultats\debat_entier`, 0.6 dans `resultats\essais\debat_entier_06`,
même cache de mesures : `FORMAT_MESURES` inchangé). Copie du code 0.5 avant ces
changements : `facescope-analyses\sauvegardes\facescope-0.5`.

1. **Écoute toujours « en retrait ».** Cause : une seule habitude par personne, parole et
   écoute confondues ; on bouge moins en écoutant, donc l'écoute tombait sous l'habitude
   (figement, mobilité en baisse). Règle : `signaux.calculer(..., par_role=True)` compare
   chaque image à l'habitude de la personne dans son rôle (ses tours de parole / le reste),
   pour le visage, la mobilité, le figement, le regard et les clignements ; repli sur
   l'habitude globale sous `TEMPS_MIN_BASE` (20 s) d'images fiables dans un rôle, signalé
   (`ligne_de_base.par_role`). Mode une personne inchangé.
2. **Thèmes très courts en tête du classement.** Cause : seuil de 8 s de parole, sans
   minimum de passages, avec repli sur tous les thèmes si aucun ne passait. Règle :
   `TEMPS_THEME_MIN` = 30 s mesurées et `PASSAGES_THEME_MIN` = 3 passages mesurés (30 s =
   deux passages de 15 s : aucun passage seul ne fait plus de la moitié du thème), plus de
   repli ; un thème trop court garde `classe: false` et `hors_classement`. Console, clés
   `classement` / `plus_marques`, bloc du rendu vertical (« aucun sujet assez long »).
3. **Public compté comme des personnes, plans de Villepin dans le présentateur.**
   - Cause des plans mêlés : deux pistes (18:08.0 et 35:08.3) commencées sur un visage
     continuaient sur l'autre, sans coupe de plan détectée (même décor, même cadrage) ;
     empreintes consécutives à -0,02 et 0,15 au changement. Correction :
     `identite.separer_pistes` coupe une piste quand la similarité moyenne 3 x 3 empreintes
     tombe sous 0,25 (minimum local), à l'image où le cadre saute le plus ; vignette reprise
     dans la vidéo pour les morceaux qui n'en ont pas. Puis réaffectation dans
     `regrouper` (0,1 d'avance, pas de chevauchement). Les mesures ne changent pas (la vue
     du visage dominant est prise avant la coupe).
   - Public : participant = nommé par une photo, ou au moins max(5 s, 1 % de la parole
     attribuée) quand tout le monde est candidat (`personnes.SEUIL_PAROLE_S`,
     `PART_PAROLE`) ; les autres = `public` (rapport, planche), sans lettre, sans analyse,
     sans étiquette, sans parole (attribution refaite entre participants, mêmes empreintes
     vocales). `--noms` s'applique aux lettres des participants.

Ajouts : `--sans-video` documentée (rapport, planche, CSV, cache ; existait déjà) ; clés
`participants`, `public`, `identite.pistes_coupees`, `identite.reaffectations`,
`croisement.synthese.regle_du_classement`.

Résultats sur le débat entier (0.5 → 0.6, `--visages`, sans vidéo, 2 min avec cache) :
- personnes : 11 (A Villepin, B Maréchal, G présentateur, 8 du public) → 3 participants
  (A Villepin, B Maréchal, C présentateur) et un public de 8 personnes (63 min à l'image) ;
  23 pistes coupées, aucune réaffectation ; les vignettes de C ne montrent plus que le
  présentateur.
- parole : Villepin 1 293 → 1 402 s, Maréchal 1 048 → 1 170 s, présentateur 75 → 77 s,
  indéterminé 280 → 80 s, hors champ 32 → 15 s, public 17 s → 0.
- en écoutant, « se retient » : Villepin 73/123 → 21/141, Maréchal 50/134 → 19/149.
- en parlant, « se retient » monte (Villepin 25/176 → 46/193, Maréchal 10/155 → 32/171)
  et « s'anime » baisse pour Villepin (40 → 26). Contrôle (code 0.6 avec une habitude
  unique, `resultats\essais\debat_entier_06\controle_sans_role`) : la nouvelle attribution
  seule donne déjà 36 et 19 « se retient » en parlant (silences et hésitations de la
  parole réattribuée) et laisse l'écoute à 73 et 48 ; l'habitude par rôle ajoute les
  figements et baisses de mobilité en parlant (Villepin 0 → 11, Maréchal 4 → 17 passages)
  et retire des « expressions plus marquées » (Villepin 31 → 9).

Non-régression du mode une personne (allocution entière, 8 min 30, code 0.5 contre 0.6,
même cache) : passages, orientations, moments, figements, CSV identiques ; seuls changent
le classement des thèmes (point 2 : 8 thèmes classés → 5), `outil`, `limites` et les
nouvelles clés.

Fragile (0.6) : seuil de participant réglé sur un seul débat entier (un intervenant qui
parle moins de 1 % tombe dans le public sauf photo) ; seuil de coupure de piste réglé sur
le même débat ; davantage de « se retient » en parlant, non relu passage par passage.

## Lancer

```bash
pip install -r requirements.txt        # + ffmpeg ; sous Linux : libegl1 libgles2
python -m facescope video.mp4 --format vertical --analyse analyse.json --rendu 3:15-4:45
```

Au premier lancement, quatre modèles sont téléchargés : le visage (3,7 Mo, Google), la
transcription (1,6 Go, Hugging Face), l'empreinte faciale (38,7 Mo, OpenCV Zoo) et
l'empreinte vocale (26,5 Mo, Hugging Face).

## Ce qui a été testé

- Film libre Tears of Steel (12 min, 172 plans) : suivi validé sur les changements de plan.
- Trois vidéos d'Emmanuel Macron en 640 x 360 :
  - allocution du 18 octobre 2026 (8 min 30, visage de 75 px) : exploitable à 97,6 %,
    8 moments atypiques, 3 figements, 6 écarts simultanés, 1 336 mots transcrits ;
  - allocution de 5 min (visage de 70 px) : exploitable à 96 % ;
  - déclaration au pupitre (visage de 53 px) : refusée, visage trop petit.
- Version 0.4, le 14 novembre 2026, sur l'ordinateur d'Arthur : extraits de 25 s en
  vertical (allocution 3:30-3:55 avec et sans `--analyse`, interview Ki7dqVhvY6g
  2:30-2:55) et le même extrait d'interview en paysage. Cet extrait montre en fait une
  déclaration de Sébastien Lecornu devant le ministère de l'Intérieur, six personnes à
  l'image : ce n'est pas une interview à questions. Images de contrôle relues : rien ne
  se chevauche, rien n'est coupé sans « … », le bloc ne change pas au sein d'un passage.
  Sorties dans `G:\rendu vidéo\facescope-analyses\resultats\essais`. Aucune vidéo entière
  n'a été rendue en 0.4.
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
- Réglage de l'orientation (0.4), sur l'allocution entière (58 passages, 8 moments
  atypiques) et 4 minutes de Ki7dqVhvY6g (27 passages). Moyennés sur un passage, les
  écarts sont petits : écart global médian 0,8 à 0,9, rarement au-dessus de 1,5. Les
  sourcils extérieurs (AU2) ont une distribution très asymétrique dans l'allocution
  (souvent à zéro, levés sur les mots appuyés) : leur moyenne dépasse 1,5 sur la moitié
  des passages, d'où un seuil à part pour les expressions.
  - Premier réglage (1 pour les signaux simples, 3 pour les expressions et le silence) :
    trop sensible, 31 passages sur 56 mesurés hors « habituel » dans une allocution lue
    (25 habituel, 17 s'anime, 9 se retient, 5 mixte, 2 non mesurés), et des « s'anime »
    pour une voix à +1 avec un écart moyen de 0,9.
  - Réglage retenu après relecture : 1,5 pour les signaux simples, 5 pour les
    expressions, 4 pour le silence, seuils divisés par deux dans un passage qui contient
    un moment atypique. Aucun jeu de seuils seul ne gardait à la fois moins d'un tiers de
    passages hors « habituel » et les 8 passages à moment atypique signalés ; la division
    par deux le permet. Allocution : 40 habituel, 6 s'anime, 5 se retient, 5 mixte,
    2 non mesurés (16 sur 56 mesurés, 29 %, les 8 moments signalés). Interview :
    20 habituel, 5 se retient, 2 s'anime (26 %).
  - Silence long (0.6) : il faut en plus que le plus long silence du passage dure au moins
    2 s (`DUREE_SILENCE_LONG`, jamais divisée par deux) ; l'écart du silence a un plancher
    de 0,2 s et des pauses de 1,3 s l'atteignaient (25 passages de Villepin sur 193).
- Le débit (fenêtre de 5 s) et les hésitations (fenêtre de 20 s) débordent sur les
  silences voisins : un passage sans parole recevait un débit et pouvait sortir « se
  retient ». Ils ne sont plus lus qu'à l'intérieur des phrases, et pas du tout sur un
  passage sans parole transcrite.
- Sur les 4 minutes de calibration de l'interview (2:00 à 6:00), le visage suivi fait 66
  pixels en médiane et la parole n'est repérée par la mâchoire que sur 0,3 % des images :
  le canal voix y est presque vide, donc l'orientation y a été vérifiée sans la voix. Sur l'extrait 2:30-2:55 (visage de 93 pixels), la voix est mesurée normalement.
  Les hésitations restent à zéro sur les deux vidéos (la transcription efface les « euh »).

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
3. Fait en 0.5 (qui est qui, qui parle, ligne de base par personne) ; reste à le valider
   sur plus de débats et à adapter le rendu paysage.
4. Produire le fichier de vérification des faits automatiquement (extraction des
   affirmations, recherche de sources), toujours avec relecture humaine.
5. Constituer 20 à 30 extraits politiques annotés par des humains (« perd-il sa contenance
   ici ? », « s'anime-t-il ? ») et mesurer la précision de l'outil dessus, orientation
   comprise. Sans cela, aucun pourcentage affiché n'est défendable et les seuils de
   l'orientation restent provisoires.
6. Comparer MediaPipe à un moteur plus précis pour le visage (OpenFace 3.0, LibreFace).
7. Ajouter des tests automatisés et factoriser le tracé de la courbe, dupliqué entre les
   deux rendus.

## Points de vigilance avant publication

- Diffamation si un verdict est faux ou mal sourcé.
- Droits des chaînes sur les images reprises.
- Règlement européen sur l'IA pour la reconnaissance des émotions : non vérifié en détail.
- Garder la mention « Cet outil mesure des mouvements. Il n'indique pas si la personne
  ment ni ce qu'elle pense. »
