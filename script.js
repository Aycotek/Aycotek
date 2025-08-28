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
    kpis: [{ name: "Taux de nouvelles idées", value: "12/mois" }, { name: "Budget R&D", value: "15% du CA" }],
    solarSystems: [
      {
        id: 'ss1-ideation',
        name: 'Système de l\'Idéation',
        description: 'Ici, les concepts sont des comètes filant dans tous les sens avant d\'être capturés par un puits gravitationnel.',
        kpis: [{ name: "Taux de conversion Idée->Proto", value: "25%" }],
        planets: [
          {
            id: 'p1-veille',
            name: 'Planète de la Veille',
            description: 'Une planète recouverte de capteurs qui analysent en permanence les signaux émis par les autres galaxies.',
            validationRules: "Le rapport de veille doit être validé par le 'Conseil des Stratèges' avant d'entrer en phase de prototypage.",
            lifecycle: 'Données valides pendant 1 cycle galactique (3 mois).',
            kpis: [{ name: 'Sources analysées', value: '1,337' }, { name: 'Pertinence des signaux', value: '89%' }],
            satellites: [
              { id: 's1-analyse-marche', name: 'Satellite d\'Analyse de Marché', description: 'Analyse les besoins non comblés des populations galactiques.' },
              { id: 's1-veille-techno', name: 'Satellite de Veille Technologique', description: 'Détecte les nouvelles technologies émergentes.' },
            ]
          },
          {
            id: 'p2-brainstorming',
            name: 'Planète du Brainstorming',
            description: 'Une géante gazeuse où les tempêtes d\'idées sont constantes et fertiles.',
            validationRules: "Toute idée doit récolter l'approbation d'au moins 3 clans d'ingénieurs différents pour être matérialisée.",
            lifecycle: 'Une idée non développée est réabsorbée par l\'atmosphère après 2 rotations.',
            kpis: [{ name: 'Idées générées/session', value: '54' }],
            satellites: [
              { id: 's2-atelier-creatif', name: 'Lune des Ateliers Créatifs', description: 'Organise des sessions de créativité structurées.' },
              { id: 's2-boite-idees', name: 'Astéroïde "Boîte à Idées"', description: 'Capture les idées spontanées de tout l\'équipage.' },
            ]
          }
        ]
      }
    ]
  },
  // ... (le reste des données reste identique mais pourrait aussi être enrichi de KPIs)
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
        kpis: [{ name: 'Portée des campagnes', value: '3M d\'unités' }, { name: 'Taux d\'engagement', value: '4.5%' }],
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
    // Le reste est déclaré dans les fonctions pour la portée

    let viewState = {
        level: 'universe', // 'universe', 'galaxy', 'system'
        activeGalaxyId: null,
        activeSystemId: null,
    };

    // --- Fonctions de Rendu Principales ---

    function render() {
        container.innerHTML = ''; // Nettoyer la vue à chaque rendu
        container.style.transform = ''; // Réinitialiser le zoom

        // Gérer la visibilité du bouton retour
        backButton.classList.toggle('hidden', viewState.level === 'universe');

        switch (viewState.level) {
            case 'system':
                renderSystemView(viewState.activeGalaxyId, viewState.activeSystemId);
                break;
            case 'galaxy':
                renderGalaxyView(viewState.activeGalaxyId);
                break;
            case 'universe':
            default:
                renderUniverseView();
                break;
        }
    }

    function renderUniverseView() {
        const svgNS = "http://www.w3.org/2000/svg";
        const svg = document.createElementNS(svgNS, 'svg');
        svg.id = 'path-container';
        Object.assign(svg.style, { position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: -1 });
        const path = document.createElementNS(svgNS, 'path');
        path.id = 'travel-path';
        svg.appendChild(path);
        container.appendChild(svg);

        const pathPoints = [];
        universeData.forEach(galaxy => {
            const galaxyEl = createAndAppend('div', container, { id: galaxy.id, className: 'galaxy' }, { left: galaxy.position.x, top: galaxy.position.y });
            createAndAppend('div', galaxyEl, { className: 'galaxy-label', textContent: galaxy.name });
            galaxyEl.addEventListener('click', () => handleGalaxyClick(galaxy));
            if (galaxy.type === 'on-path') {
                const rect = container.getBoundingClientRect();
                pathPoints.push({ x: parseFloat(galaxy.position.x) / 100 * rect.width, y: parseFloat(galaxy.position.y) / 100 * rect.height });
            }
        });
        drawPath(path, pathPoints);
        startJourney();
    }

    function renderGalaxyView(galaxyId) {
        const galaxy = universeData.find(g => g.id === galaxyId);
        if (!galaxy) return;

        const count = galaxy.solarSystems.length;
        galaxy.solarSystems.forEach((system, index) => {
            const angle = (index / count) * 2 * Math.PI;
            const radius = count > 1 ? 35 : 0; // Centre si un seul système
            const x = 50 + radius * Math.cos(angle);
            const y = 50 + radius * Math.sin(angle);

            const systemEl = createAndAppend('div', container, { id: system.id, className: 'solar-system', textContent: system.name });
            Object.assign(systemEl.style, { left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)' });
            systemEl.addEventListener('click', () => handleSystemClick(system));
        });
    }

    function renderSystemView(galaxyId, systemId) {
        const galaxy = universeData.find(g => g.id === galaxyId);
        const system = galaxy?.solarSystems.find(s => s.id === systemId);
        if (!system) return;

        const count = system.planets.length;
        system.planets.forEach((planet, index) => {
            const angle = (index / count) * 2 * Math.PI;
            const radius = 35;
            const x = 50 + radius * Math.cos(angle);
            const y = 50 + radius * Math.sin(angle);

            const planetEl = createAndAppend('div', container, { id: planet.id, className: 'planet', textContent: planet.name });
            Object.assign(planetEl.style, { left: `${x}%`, top: `${y}%`, transform: 'translate(-50%, -50%)', width: '80px', height: '80px' });
            // planetEl.addEventListener('click', () => handlePlanetClick(planet));
        });
    }

    // --- Gestionnaires de Clics et Transitions ---

    function zoomAndPan(element, scale, targetLevel, stateUpdates) {
        const rect = element.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const translateX = (containerRect.width / 2) - rect.left - (rect.width / 2);
        const translateY = (containerRect.height / 2) - rect.top - (rect.height / 2);
        container.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;

        setTimeout(() => {
            Object.assign(viewState, { level: targetLevel, ...stateUpdates });
            render();
        }, 1000);
    }

    function handleGalaxyClick(galaxy) {
        updateInfoPanel(galaxy);
        zoomAndPan(document.getElementById(galaxy.id), 4, 'galaxy', { activeGalaxyId: galaxy.id });
    }

    function handleSystemClick(system) {
        updateInfoPanel(system);
        zoomAndPan(document.getElementById(system.id), 5, 'system', { activeSystemId: system.id });
    }

    // --- Fonctions Utilitaires ---

    function createAndAppend(tag, parent, attributes = {}, styles = {}) {
        const el = document.createElement(tag);
        Object.assign(el, attributes);
        Object.assign(el.style, styles);
        parent.appendChild(el);
        return el;
    }

    function drawPath(path, pathPoints) {
        pathPoints.sort((a, b) => a.x - b.x);
        if (pathPoints.length === 0) return;
        let pathD = `M ${pathPoints[0].x} ${pathPoints[0].y}`;
        for (let i = 1; i < pathPoints.length; i++) {
            const p1 = pathPoints[i-1], p2 = pathPoints[i];
            const cp1x = p1.x + (p2.x - p1.x) / 2, cp1y = p1.y;
            const cp2x = p1.x + (p2.x - p1.x) / 2, cp2y = p2.y;
            pathD += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
        }
        path.setAttribute('d', pathD);
    }

    function startJourney() {
        if (viewState.level !== 'universe') return;
        const ship = createAndAppend('div', container, { id: 'wikicovage' });
        const path = document.getElementById('travel-path');
        if (!path || path.getTotalLength() === 0) return;

        const pathLength = path.getTotalLength();
        const startPoint = path.getPointAtLength(0);
        const nextAnglePoint = path.getPointAtLength(1);
        const startAngle = Math.atan2(nextAnglePoint.y - startPoint.y, nextAnglePoint.x - startPoint.x);
        ship.style.transform = `translate(${startPoint.x}px, ${startPoint.y}px) rotate(${startAngle}rad)`;

        let startTime = null;
        const duration = 15000;
        function animate(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const point = path.getPointAtLength(progress * pathLength);
            const nextPoint = path.getPointAtLength(progress * pathLength + 1);
            const angle = Math.atan2(nextPoint.y - point.y, nextPoint.x - point.x);
            ship.style.transform = `translate(${point.x}px, ${point.y}px) rotate(${angle}rad)`;
            if (progress < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
    }

    function updateInfoPanel(data) {
        let content = '', type = '';
        if (data.solarSystems) { type = 'Galaxie / Macro-Processus'; }
        else if (data.planets) { type = 'Système Solaire / Processus'; }
        else if (data.satellites) { type = 'Planète / Sous-Processus'; }
        else { type = 'Satellite'; }

        content = `
            <h2 class="text-2xl font-bold text-cyan-400 mb-2">${data.name}</h2>
            <p class="text-sm text-gray-400 mb-4">${type}</p>
            <div class="mb-6"><h3 class="font-semibold mb-2 text-gray-200">Description</h3><p class="text-gray-300">${data.description || 'Aucune description.'}</p></div>
        `;
        if (data.valueProposition) {
            content += `<div class="mb-6"><h3 class="font-semibold mb-2 text-gray-200">Valeur Apportée</h3><p class="text-yellow-300 italic">"${data.valueProposition}"</p></div>`;
        }
        // Ajout de la section KPI
        if (data.kpis && data.kpis.length > 0) {
            let kpiList = data.kpis.map(kpi => {
                const color = Math.random() < 0.6 ? 'bg-green-500' : 'bg-red-500'; // 60% chance d'être vert
                return `<li class="flex items-center justify-between bg-gray-800 p-2 rounded-md">
                          <span class="flex items-center">
                            <span class="kpi-indicator mr-3 ${color}"></span>
                            <span class="text-gray-300">${kpi.name}</span>
                          </span>
                          <span class="font-semibold text-white">${kpi.value}</span>
                        </li>`;
            }).join('');
            content += `<div class="mb-6">
                          <h3 class="font-semibold mb-2 text-gray-200">Indicateurs de Performance</h3>
                          <ul class="space-y-2">${kpiList}</ul>
                        </div>`;
        }

        panelContent.innerHTML = content;
        infoPanel.classList.add('visible');
    }

    closePanelBtn.addEventListener('click', () => infoPanel.classList.remove('visible'));

    // --- Lancement Initial & Gestionnaires d'événements globaux ---
    const backButton = document.getElementById('back-button');

    function navigateBack() {
        if (viewState.level === 'system') {
            viewState.level = 'galaxy';
            viewState.activeSystemId = null;
        } else if (viewState.level === 'galaxy') {
            viewState.level = 'universe';
            viewState.activeGalaxyId = null;
        }
        infoPanel.classList.remove('visible'); // Cacher le panneau en remontant
        render();
    }

    backButton.addEventListener('click', navigateBack);
    closePanelBtn.addEventListener('click', () => infoPanel.classList.remove('visible'));
    window.addEventListener('resize', render);

    render(); // Lancement initial
});
