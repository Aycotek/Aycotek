// --- Nouvelle base de données de l'univers ---
const universeData = [
  // 1. Galaxie de l'Innovation & Développement
  {
    id: 'g1-inno-dev',
    name: "Nébuleuse de l'Innovation",
    type: 'on-path',
    position: { x: '15%', y: '40%' },
    description: "Une nébuleuse bouillonnante où les idées naissent des gaz cosmiques et se transforment en prototypes stellaires. C'est le berceau de toute nouvelle création.",
    valueProposition: "Réduction du temps de mise sur le marché, création de nouvelles sources de revenus, avantage concurrentiel durable.",
    solarSystems: [
      {
        id: 'ss1-ideation',
        name: 'Système de l\'Idéation',
        description: 'Ici, les concepts sont des comètes filant dans tous les sens avant d\'être capturés par un puits gravitationnel.',
        planets: [
          {
            id: 'p1-veille',
            name: 'Planète de la Veille Concurrentielle',
            description: 'Une planète recouverte de capteurs qui analysent en permanence les signaux émis par les autres galaxies.',
            validationRules: "Le rapport de veille doit être validé par le 'Conseil des Stratèges' avant d'entrer en phase de prototypage.",
            lifecycle: 'Données valides pendant 1 cycle galactique (3 mois).',
            satellites: [
              { id: 's1-analyse-marche', name: 'Satellite d\'Analyse de Marché', description: 'Analyse les besoins non comblés des populations galactiques.' },
              { id: 's1-veille-techno', name: 'Satellite de Veille Technologique', description: 'Détecte les nouvelles technologies émergentes.' },
            ]
          },
          {
            id: 'p2-brainstorming',
            name: 'Planète du Brainstorming Perpétuel',
            description: 'Une géante gazeuse où les tempêtes d\'idées sont constantes et fertiles.',
            validationRules: "Toute idée doit récolter l'approbation d'au moins 3 clans d'ingénieurs différents pour être matérialisée.",
            lifecycle: 'Une idée non développée est réabsorbée par l\'atmosphère après 2 rotations.',
            satellites: [
              { id: 's2-atelier-creatif', name: 'Lune des Ateliers Créatifs', description: 'Organise des sessions de créativité structurées.' },
              { id: 's2-boite-idees', name: 'Astéroïde "Boîte à Idées"', description: 'Capture les idées spontanées de tout l\'équipage.' },
            ]
          }
        ]
      }
    ]
  },
  // 2. Galaxie du Perfectionnement & Commercialisation
  {
    id: 'g2-market',
    name: 'Galaxie de la Commercialisation',
    type: 'on-path',
    position: { x: '40%', y: '60%' },
    description: 'Une galaxie spirale où les prototypes sont polis pour devenir des produits phares et où les stratégies sont déployées pour conquérir de nouveaux marchés stellaires.',
    valueProposition: "Augmentation des parts de marché, croissance du chiffre d'affaires, amélioration de l'image de marque.",
    solarSystems: [
      {
        id: 'ss2-marketing',
        name: 'Système du Marketing Stratosphérique',
        description: 'Un système binaire où le produit et son marché tournent l\'un autour de l\'autre en parfaite harmonie.',
        planets: [
          {
            id: 'p3-packaging',
            name: 'Planète du Perfectionnement',
            description: 'Ici, les produits bruts sont affinés, testés et emballés dans des matériaux résistants aux voyages hyperspatiaux.',
            validationRules: "Un produit doit passer 50 tests de résistance en chambre de simulation avant d'être validé pour la production de masse.",
            lifecycle: 'Les spécifications produit sont revues à chaque alignement planétaire.',
            satellites: [
              { id: 's3-beta-test', name: 'Lune des Bêta-Testeurs', description: 'Une communauté d\'experts qui teste les produits en conditions réelles.' },
              { id: 's3-design-ux', name: 'Station Orbitale du Design (UX)', description: 'Améliore l\'expérience utilisateur jusqu\'à la perfection.' },
            ]
          },
          {
            id: 'p4-strategie-com',
            name: 'Planète de la Communication',
            description: 'Émet des signaux puissants à travers l\'univers pour faire connaître les nouveaux produits.',
            validationRules: "Chaque message doit être approuvé par l'Alliance des Communicants et respecter la charte éthique intergalactique.",
            lifecycle: 'Une campagne de communication dure 42 jours standards.',
            satellites: [
              { id: 's4-reseaux-sociaux', name: 'Nébuleuse des Réseaux Sociaux', description: 'Diffuse l\'information à grande vitesse.' },
              { id: 's4-relations-presse', name: 'Comète des Relations Presse', description: 'Porte la bonne nouvelle aux confins de l\'univers connu.' },
            ]
          }
        ]
      }
    ]
  },
  // 3. Galaxie de la Planification & Production
  {
    id: 'g3-prod',
    name: 'Amas de la Production',
    type: 'on-path',
    position: { x: '65%', y: '35%' },
    description: "Un amas globulaire dense où les plans se transforment en matière. Les usines-mondes y tournent à plein régime pour assembler les produits à grande échelle.",
    valueProposition: "Optimisation des coûts, garantie de la qualité, respect des délais de livraison.",
    solarSystems: [
        {
            id: 'ss3-supply-chain',
            name: 'Système de la Chaîne Logistique',
            description: 'Assure un flux constant de ressources entre les planètes minières et les usines-mondes.',
            planets: [
                {
                    id: 'p5-planification',
                    name: 'Planète de la Planification',
                    description: 'Le cerveau du système, où les algorithmes prédictifs calculent les besoins de production pour les 10 prochains cycles.',
                    validationRules: "Le Plan Directeur de Production doit être validé par le triumvirat Logistique, Production et Finance.",
                    lifecycle: 'Le plan est ajusté en temps réel mais gelé 1 cycle avant exécution.',
                    satellites: [
                        { id: 's5-prevision-demande', name: 'Satellite Oracle', description: 'Analyse les tendances de consommation.' },
                        { id: 's5-gestion-stock', name: 'Lune-Entrepôt', description: 'Gère les niveaux de matières premières et de produits finis.' },
                    ]
                },
                {
                    id: 'p6-assemblage',
                    name: 'Usine-Monde "Forge Alpha"',
                    description: 'Une planète entièrement dédiée à l\'assemblage automatisé.',
                    validationRules: "Chaque lot produit subit un contrôle qualité par un drone inspecteur. Taux de défaut toléré : 0.01%.",
                    lifecycle: 'Les chaînes de production sont reconfigurées toutes les 500 000 unités.',
                    satellites: [
                        { id: 's6-controle-qualite', name: 'Station de Contrôle Qualité', description: 'Vérifie la conformité de chaque produit.' },
                        { id: 's6-maintenance', name: 'Flotte de Maintenance', description: 'Entretient les robots d\'assemblage.' },
                    ]
                }
            ]
        }
    ]
  },
  // 4. Galaxie du Service Client & Support
  {
    id: 'g4-support',
    name: 'Galaxie du Support Client',
    type: 'on-path',
    position: { x: '85%', y: '55%' },
    description: "Une galaxie accueillante où des flottes de vaisseaux de service sont prêtes à aider les utilisateurs, à résoudre les problèmes et à recueillir les précieux retours.",
    valueProposition: "Fidélisation client, amélioration continue des produits grâce aux retours, support technique réactif.",
    solarSystems: [
        {
            id: 'ss4-assistance',
            name: 'Système de l\'Assistance',
            description: 'Un havre de paix où toutes les demandes trouvent une réponse.',
            planets: [
                {
                    id: 'p7-helpdesk',
                    name: 'Planète Help-Desk',
                    description: 'Un centre de communication intergalactique actif 24/7.',
                    validationRules: "Un ticket de support de niveau 1 doit recevoir une première réponse en moins d'une heure standard.",
                    lifecycle: 'Les tickets non résolus sont automatiquement escaladés après 24 heures.',
                    satellites: [
                        { id: 's7-base-connaissance', name: 'Bibliothèque Orbitale (FAQ)', description: 'Contient les réponses à toutes les questions fréquentes.' },
                        { id: 's7-support-n1', name: 'Escadrille de Support N1', description: 'Gère les requêtes de premier niveau.' },
                    ]
                },
                {
                    id: 'p8-amelioration',
                    name: 'Planète du Feedback Continu',
                    description: 'Analyse tous les retours clients pour alimenter la Nébuleuse de l\'Innovation.',
                    validationRules: "Toute suggestion d'amélioration doit être catégorisée et transmise à la R&D si elle est mentionnée par plus de 100 utilisateurs.",
                    lifecycle: 'Les rapports de feedback sont synthétisés et envoyés à la galaxie G1 tous les mois.',
                    satellites: [
                        { id: 's8-enquetes-satisfaction', name: 'Sonde de Satisfaction (CSAT)', description: 'Mesure le contentement des clients.' },
                        { id: 's8-analyse-retours', name: 'Laboratoire d\'Analyse des Retours', description: 'Transforme les commentaires en données exploitables.' },
                    ]
                }
            ]
        }
    ]
  },
  // --- Galaxies Hors Chemin ---
  {
    id: 'g5-strategie',
    name: 'Singularité Stratégique',
    type: 'off-path',
    position: { x: '50%', y: '10%' },
    description: "Un point unique et massif qui influence la trajectoire de toutes les autres galaxies. Les grandes décisions et la vision à long terme y sont forgées.",
    valueProposition: "Aligne l'ensemble des processus sur une vision commune, assure la pérennité de l'entreprise.",
    solarSystems: [
      {
        id: 'ss5-vision',
        name: 'Système de la Vision à Long Terme',
        description: 'Définit les grands objectifs pour les siècles à venir.',
        planets: [
          {
            id: 'p9-objectifs',
            name: 'Planète des Objectifs Clés',
            description: 'Définit les OKR (Objectives and Key Results) pour l\'ensemble de la flotte.',
            validationRules: "Les objectifs doivent être approuvés par le Haut Conseil Intergalactique.",
            lifecycle: 'Les objectifs sont définis annuellement.',
            satellites: [
              { id: 's9-kpi', name: 'Lune des KPIs', description: 'Suit la performance en temps réel.' }
            ]
          }
        ]
      }
    ]
  },
  {
    id: 'g6-iso',
    name: 'Anomalie Réglementaire ISO 27001',
    type: 'off-path',
    position: { x: '25%', y: '85%' },
    description: "Un champ de force complexe qui régit les lois de la sécurité de l'information. Tout vaisseau ou produit doit être certifié pour pouvoir naviguer librement.",
    valueProposition: "Garantit la confiance des clients et partenaires, réduit les risques liés à la sécurité de l'information.",
    solarSystems: [
      {
        id: 'ss6-conformite',
        name: 'Système de la Conformité',
        description: 'Un système où chaque processus est audité en permanence.',
        planets: [
          {
            id: 'p10-audit',
            name: 'Planète des Audits',
            description: 'Scanne en permanence tous les processus pour détecter les non-conformités.',
            validationRules: "Un audit doit être mené par une entité externe certifiée.",
            lifecycle: 'La certification est renouvelée tous les 3 ans standards.',
            satellites: [
              { id: 's10-gestion-risques', name: 'Satellite de Gestion des Risques', description: 'Identifie et évalue les menaces.' },
              { id: 's10-documentation', name: 'Archive de Documentation', description: 'Conserve toutes les preuves de conformité.' }
            ]
          }
        ]
      }
    ]
  }
];

// --- Initialisation de l'application ---
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('universe-container');
    const infoPanel = document.getElementById('info-panel');
    const panelContent = document.getElementById('panel-content');
    const closePanelBtn = document.getElementById('close-panel');
    const searchBar = document.getElementById('search-bar');
    const searchResults = document.getElementById('search-results');

    function renderUniverse() {
        // Vider le conteneur au cas où
        container.innerHTML = '';

        // Créer le conteneur SVG pour le chemin
        const svgNS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('id', 'path-container');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');

        const path = document.createElementNS(svgNS, 'path');
        path.setAttribute('id', 'travel-path');

        svg.appendChild(path);
        container.appendChild(svg);

        const pathPoints = [];

        // Afficher chaque galaxie
        universeData.forEach(galaxy => {
            const galaxyEl = document.createElement('div');
            galaxyEl.id = galaxy.id;
            galaxyEl.className = 'galaxy';
            galaxyEl.style.left = galaxy.position.x;
            galaxyEl.style.top = galaxy.position.y;

            const labelEl = document.createElement('div');
            labelEl.className = 'galaxy-label';
            labelEl.textContent = galaxy.name;
            galaxyEl.appendChild(labelEl);

            container.appendChild(galaxyEl);

            if (galaxy.type === 'on-path') {
                // Convertir les pourcentages en pixels pour le chemin SVG
                const rect = container.getBoundingClientRect();
                const x = parseFloat(galaxy.position.x) / 100 * rect.width;
                const y = parseFloat(galaxy.position.y) / 100 * rect.height;
                pathPoints.push({x, y});
            }
        });

        // Dessiner le chemin
        // Trier les points par coordonnée x pour s'assurer que le chemin va de gauche à droite
        pathPoints.sort((a, b) => a.x - b.x);

        // Construire l'attribut 'd' pour le chemin SVG
        let pathD = '';
        if (pathPoints.length > 0) {
            pathD = `M ${pathPoints[0].x} ${pathPoints[0].y}`;
            for (let i = 1; i < pathPoints.length; i++) {
                const p1 = pathPoints[i-1];
                const p2 = pathPoints[i];
                // Ajout de points de contrôle pour une courbe douce (Bézier cubique)
                const cp1x = p1.x + (p2.x - p1.x) / 2;
                const cp1y = p1.y;
                const cp2x = p1.x + (p2.x - p1.x) / 2;
                const cp2y = p2.y;
                pathD += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
            }
        }
        path.setAttribute('d', pathD);
    }

    function startJourney() {
        const ship = document.createElement('div');
        ship.id = 'wikicovage';
        container.appendChild(ship);

        const path = document.getElementById('travel-path');
        if (!path) return;

        const pathLength = path.getTotalLength();

        // Positionner le vaisseau au début avant de commencer l'animation
        const startPoint = path.getPointAtLength(0);
        const nextPointForAngle = path.getPointAtLength(1);
        const startAngle = Math.atan2(nextPointForAngle.y - startPoint.y, nextPointForAngle.x - startPoint.x);
        ship.style.transform = `translate(${startPoint.x}px, ${startPoint.y}px) translate(-50%, -50%) rotate(${startAngle}rad)`;
        let startTime = null;
        const duration = 15000; // 15 secondes pour le voyage complet

        function animate(timestamp) {
            if (!startTime) startTime = timestamp;
            const elapsedTime = timestamp - startTime;

            // Calculer la progression, en s'assurant qu'elle ne dépasse pas la durée
            const progress = Math.min(elapsedTime / duration, 1);
            const distance = progress * pathLength;

            const point = path.getPointAtLength(distance);
            const nextPoint = path.getPointAtLength(distance + 1 < pathLength ? distance + 1 : pathLength);

            // Calculer l'angle de rotation
            const angle = Math.atan2(nextPoint.y - point.y, nextPoint.x - point.x);

            // Appliquer la transformation
            ship.style.transform = `translate(${point.x}px, ${point.y}px) translate(-50%, -50%) rotate(${angle}rad)`;

            // Continuer l'animation jusqu'à la fin
            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                // Optionnel: faire quelque chose à la fin, comme faire clignoter le vaisseau
                ship.style.boxShadow = '0 0 25px #ffdd00, 0 0 50px #ffffff';
            }
        }

        requestAnimationFrame(animate);
    }

    // Lancer le rendu et l'animation
    renderUniverse();
    startJourney();
    window.addEventListener('resize', () => {
        renderUniverse();
        startJourney();
    });

    // --- Logique d'interactivité ---

    function updateInfoPanel(data) {
        let content = '';
        // Détecte s'il s'agit d'une galaxie en vérifiant la présence de `solarSystems`
        if (data.solarSystems) {
            content = `
                <h2 class="text-2xl font-bold text-cyan-400 mb-2">${data.name}</h2>
                <p class="text-sm text-gray-400 mb-4">Galaxie / Macro-Processus</p>
                <div class="mb-6">
                    <h3 class="font-semibold mb-2 text-gray-200">Description Cosmique</h3>
                    <p class="text-gray-300">${data.description}</p>
                </div>
                <div class="mb-6">
                    <h3 class="font-semibold mb-2 text-gray-200">Valeur Apportée</h3>
                    <p class="text-yellow-300 italic">"${data.valueProposition}"</p>
                </div>
            `;
        }
        // Des 'else if' pourront être ajoutés ici pour les systèmes, planètes, etc.

        panelContent.innerHTML = content;
        infoPanel.classList.add('visible');
    }

    // Ajout des listeners sur les galaxies
    document.querySelectorAll('.galaxy').forEach(galaxyEl => {
        galaxyEl.addEventListener('click', () => {
            const galaxyData = universeData.find(g => g.id === galaxyEl.id);
            if (galaxyData) {
                document.querySelectorAll('.galaxy.highlight').forEach(el => el.classList.remove('highlight'));
                galaxyEl.classList.add('highlight');
                updateInfoPanel(galaxyData);
            }
        });
    });

    closePanelBtn.addEventListener('click', () => {
        infoPanel.classList.remove('visible');
        document.querySelectorAll('.galaxy.highlight').forEach(el => el.classList.remove('highlight'));
    });


    // --- Logique de la recherche ---
    searchBar.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        document.querySelectorAll('.highlight').forEach(el => el.classList.remove('highlight'));

        if (query.length < 2) {
            searchResults.innerHTML = '';
            searchResults.classList.add('hidden');
            return;
        }

        const results = [];
        universeData.forEach(galaxy => {
            const context = { galaxy };
            if (galaxy.name.toLowerCase().includes(query)) {
                results.push({ type: 'Galaxie', name: galaxy.name, elementId: galaxy.id, data: context });
            }
            galaxy.solarSystems.forEach(system => {
                context.system = system;
                if (system.name.toLowerCase().includes(query)) {
                    results.push({ type: 'Système Solaire', name: system.name, context: galaxy.name, elementId: galaxy.id, data: context });
                }
                system.planets.forEach(planet => {
                    context.planet = planet;
                    if (planet.name.toLowerCase().includes(query)) {
                        results.push({ type: 'Planète', name: planet.name, context: `${galaxy.name} > ${system.name}`, elementId: galaxy.id, data: context });
                    }
                    planet.satellites.forEach(satellite => {
                        if (satellite.name.toLowerCase().includes(query)) {
                             results.push({ type: 'Satellite', name: satellite.name, context: `${system.name} > ${planet.name}`, elementId: galaxy.id, data: context });
                        }
                    });
                });
            });
        });
        displaySearchResults(results);
    });

    function displaySearchResults(results) {
        if (results.length === 0) {
            searchResults.innerHTML = '<div class="p-3 text-gray-400">Aucun résultat</div>';
            searchResults.classList.remove('hidden');
            return;
        }
        searchResults.innerHTML = results
            .map((r, i) => `
                <div class="p-3 hover:bg-gray-800 cursor-pointer border-b border-gray-700 search-result-item" data-result-index="${i}">
                    <p class="font-semibold text-white">${r.name}</p>
                    <p class="text-xs text-gray-400">${r.type} ${r.context ? `(${r.context})` : ''}</p>
                </div>
            `)
            .join('');

        document.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const result = results[e.currentTarget.dataset.resultIndex];
                const galaxyEl = document.getElementById(result.elementId);

                if (galaxyEl) {
                    document.querySelectorAll('.galaxy.highlight').forEach(el => el.classList.remove('highlight'));
                    galaxyEl.classList.add('highlight');
                    // Pour l'instant, on affiche toujours l'info de la galaxie parente.
                    // La logique de drill-down affinera cela.
                    updateInfoPanel(result.data.galaxy);
                }

                searchResults.classList.add('hidden');
                searchBar.value = result.name;
            });
        });

        searchResults.classList.remove('hidden');
    }
});
