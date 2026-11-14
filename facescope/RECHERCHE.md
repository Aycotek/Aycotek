# Ce que dit la recherche

Synthèse faite le 12 novembre 2026. Chaque point renvoie à sa source. Quand un chiffre
vient d'une source secondaire, c'est écrit.

## 1. On ne détecte pas le mensonge sur un visage

- **Les humains font à peine mieux que le hasard.** La méta-analyse de Bond et DePaulo
  (2006, *Personality and Social Psychology Review*) regroupe 206 documents et
  24 483 juges : environ 54 % de bonnes réponses, contre 50 % au hasard. Les
  professionnels (police, etc.) ne font pas mieux que les autres.
  [PubMed](https://pubmed.ncbi.nlm.nih.gov/16859438/)
- **Les indices du mensonge sont faibles.** DePaulo et al. (2003, *Psychological Bulletin*,
  129(1), 74-118) passent en revue 158 indices. Chiffres repris de sources secondaires :
  effet médian d'environ d = 0,10 ; les rares indices non verbaux qui ressortent
  (tension, voix plus aiguë, d ≈ 0,2) restent petits et varient beaucoup d'une étude à
  l'autre. [Fiche de l'article](https://scholars.duke.edu/publication/660134)
- **Les micro-expressions ne sont pas un détecteur.** Burgoon (2018, *Frontiers in
  Psychology*) : elles sont rares et pas réservées aux menteurs. Elle cite Porter et
  ten Brinke (2008) : sur environ 700 expressions analysées, 2 % seulement étaient des
  micro-expressions (chiffre rapporté par Burgoon, non vérifié dans l'article d'origine).
  [Article](https://www.frontiersin.org/article/10.3389/fpsyg.2018.01672/full)
- **Un visage ne donne pas l'émotion ressentie.** Barrett et al. (2019, *Psychological
  Science in the Public Interest*) : les mouvements du visage associés à une émotion ne
  sont pas un indicateur fiable de cette émotion, ils dépendent du contexte, de la
  personne et de la culture. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6640856)
- **La synergologie est classée parmi les pseudosciences** par une revue critique parue
  dans la *Revue québécoise de psychologie* (2018, vol. 39, n° 2).
  [Article](https://www.erudit.org/fr/revue/rqpsy/2018/v39/n2/1051231ar.pdf)

## 2. Les détecteurs automatiques ne font pas mieux

Les modèles publiés (unités d'action + réseau de neurones) annoncent de bons scores, mais
sur de très petits jeux de données, souvent le même (procès filmés). Dès qu'on change de
jeu de données, la performance chute : c'est le point faible relevé par Dinges et al.
(2024, *Neural Computing and Applications*).
[Article](https://link.springer.com/content/pdf/10.1007/s00521-024-09811-x.pdf) ·
[Exemple de modèle à base d'unités d'action](https://arxiv.org/abs/2105.13659v1)

Aucun de ces modèles n'a été validé sur des responsables politiques en interview.

## 3. Fabien Olicard

Je n'ai pas pu regarder ses vidéos : YouTube n'est pas accessible depuis l'environnement
où ce travail a été fait. Ce que j'ai trouvé par écrit : il se présente comme mentaliste
(observation, lecture à froid), dit qu'on ne peut pas lire les pensées et qu'on peut
seulement déduire certaines informations de l'observation.
[Brut](https://www.brut.media/fr/videos/c-est-quoi-le-mentalisme). C'est du spectacle
appuyé sur de la psychologie, pas une méthode validée de détection du mensonge.

## 4. Ce qui reste solide, et ce que l'outil en fait

| Ce qui est mesurable | Ce que l'outil affiche |
|---|---|
| Les mouvements du visage (système FACS d'Ekman et Friesen) | Unités d'action approchées, image par image |
| La ressemblance à une configuration type (sourire, froncement…) | « Expression affichée », jamais « émotion ressentie » |
| L'écart d'une personne par rapport à son propre comportement habituel | Indice d'écart et moments atypiques |
| La voix (hauteur, énergie) | Hauteur et énergie quand la personne parle |

Un écart dit « ici, il se passe quelque chose d'inhabituel ». Il ne dit pas quoi.
La seule façon fiable de savoir si une affirmation est fausse reste de la vérifier.

## 5. Droit (à faire valider par un juriste)

- Règlement européen sur l'IA, article 5(1)(f) : la reconnaissance des émotions est
  interdite au travail et dans l'enseignement.
  [Texte](https://ai-act-service-desk.ec.europa.eu/fr/ai-act/article-5). L'usage visé ici
  n'est pas dans ces deux cas.
- Non vérifié dans cette recherche : le classement des systèmes de reconnaissance des
  émotions (annexe III), les obligations de transparence (article 50), le RGPD, et le
  risque de diffamation si on publie « X ment » à partir d'un score.

## 6. Les logiciels qui existent déjà

| Outil | Ce qu'il fait bien | Ce qu'il fait mal |
|---|---|---|
| OpenFace 3.0 (CMU, 2025, libre pour la recherche) | Unités d'action, regard, émotion dans un seul outil, sur processeur | Score F1 d'environ 60 % sur les unités d'action face à des codeurs humains (chiffre repris de résumés de l'article, à vérifier) |
| FaceReader (Noldus, payant) | Le seul outil commercial avec des études de validation publiées | Validé surtout sur des expressions posées ; en difficulté sur les expressions de faible intensité et les images de basse qualité |
| AFFDEX (Affectiva / iMotions, payant) | Entraîné sur de très grands volumes de visages filmés en conditions réelles | Précision très variable selon l'émotion et le jeu de données (Stöckli et al.) |
| Azure Face (Microsoft) | - | Microsoft a retiré la reconnaissance des émotions en 2022, faute de consensus scientifique |

Sources : [OpenFace 3.0](https://arxiv.org/abs/2506.02891v1) ·
[validation de FaceReader 7](https://pmc.ncbi.nlm.nih.gov/articles/PMC6797095) ·
[Stöckli et al.](https://boris.unibe.ch/117417/7/St%C3%B6ckli%20et%20al.%202018.pdf) ·
[retrait chez Microsoft](https://www.engadget.com/microsoft-retires-facial-recognition-ai-emotion-detection-183010078.html)

Ce que ça veut dire pour nous : même les meilleurs outils se trompent souvent sur le simple
fait de savoir quel muscle bouge, et ils sont les plus faibles exactement sur notre cible
(visages fermés, expressions discrètes, vidéos compressées). Le gain ne viendra pas d'un
meilleur lecteur d'émotions mais de trois choses : comparer la personne à elle-même, croiser
le visage avec la voix et la parole, et mesurer la précision sur des extraits annotés par
des humains.

## 7. Données pour mesurer la déstabilisation

StressID (NeurIPS 2023) est le jeu de données public le plus proche : 65 participants,
11 tâches, plus de 39 heures, vidéo du visage, son et signaux physiologiques, avec
l'auto-évaluation du stress. Licence propriétaire : les conditions d'accès sont sur la page
du projet et n'ont pas été vérifiées ici.
[Fiche NeurIPS](https://neurips.cc/virtual/2023/poster/73454) ·
[Présentation EURECOM](https://www.eurecom.edu/en/node/4900665)

Aucun jeu de données public ne porte sur des responsables politiques en interview.
