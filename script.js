// --- Nouvelle base de données de l'univers (données enrichies) ---
const universeData = [
  // 1. Galaxie de l'Innovation & Développement
  {
    id: 'g1-inno-dev',
    name: "Nébuleuse de l'Innovation",
    type: 'on-path',
    position: { x: '15%', y: '40%' },
    theme: { primary: 'cyan', secondary: 'white' },
    description: "Une nébuleuse bouillonnante où les idées naissent des gaz cosmiques et se transforment en prototypes stellaires.",
    valueProposition: "Réduction du temps de mise sur le marché, création de nouvelles sources de revenus.",
    kpis: [{ name: "Taux de nouvelles idées", value: "12/mois" }, { name: "Budget R&D", value: "15% du CA" }],
    solarSystems: [
      {
        id: 'ss1-veille', name: 'Processus de Veille', position: { x: '20%', y: '25%' },
        planets: [
          { id: 'p1-veille-tech', name: 'Veille Technologique', position: { x: '30%', y: '40%' }, documents: [{name: 'Rapport Tendance IA Q2'}, {name: 'Analyse concurrentielle Web3'}] },
          { id: 'p1-veille-marche', name: 'Veille Marché', position: { x: '70%', y: '60%' }, documents: [{name: 'Etude de marché - Secteur A'}, {name: 'Synthèse besoins clients'}] },
        ]
      },
      {
        id: 'ss1-ideation', name: 'Processus d\'Idéation', position: { x: '40%', y: '75%' },
        kpis: [{ name: "Taux de conversion Idée->Proto", value: "25%" }],
        planets: [
          { id: 'p2-ateliers', name: 'Ateliers de créativité', position: { x: '25%', y: '60%' }, documents: [{name: 'Compte-rendu Atelier "Blue Sky"'}] },
          { id: 'p2-recueil', name: 'Recueil des idées', position: { x: '65%', y: '30%' }, documents: [{name: 'Export plateforme à idées v3'}] },
        ]
      },
      {
        id: 'ss1-poc', name: 'Processus de Prototypage', position: { x: '70%', y: '20%' },
        planets: [
          { id: 'p3-maquettage', name: 'Maquettage UX/UI', position: { x: '40%', y: '30%' }, documents: [{name: 'Maquette Figma v4'}, {name: 'Parcours utilisateur validé'}] },
          { id: 'p3-dev-poc', name: 'Développement PoC', position: { x: '60%', y: '70%' }, documents: [{name: 'Lien vers repo Git du PoC'}, {name: 'Fiche de tests techniques'}] },
        ]
      },
       {
        id: 'ss1-validation', name: 'Processus de Validation', position: { x: '80%', y: '70%' },
        planets: [
          { id: 'p4-tests-utilisateurs', name: 'Tests Utilisateurs', position: { x: '35%', y: '65%' }, documents: [{name: 'Retours verbatim utilisateurs'}, {name: 'Rapport de tests v2'}] },
          { id: 'p4-validation-metier', name: 'Validation Métier', position: { x: '75%', y: '35%' }, documents: [{name: 'PV de validation du COPIL'}] },
        ]
      }
    ]
  },
  {
    id: 'g2-market', name: 'Galaxie de la Commercialisation', type: 'on-path', position: { x: '40%', y: '60%' }, theme: { primary: '#ff8c00', secondary: '#ffdd00' },
    description: 'Une galaxie spirale où les prototypes sont polis pour devenir des produits phares.', valueProposition: "Augmentation des parts de marché, croissance du chiffre d'affaires.",
    solarSystems: [
      { id: 'ss2-strategie', name: 'Stratégie Marketing', position: { x: '20%', y: '30%' }, planets: [{id: 'p5-branding', name: 'Branding', position: {x:'50%', y:'50%'}, documents:[]}] },
      { id: 'ss2-contenu', name: 'Création de Contenu', position: { x: '40%', y: '70%' }, planets: [{id: 'p6-blog', name: 'Blog', position: {x:'50%', y:'50%'}, documents:[]}] },
      { id: 'ss2-campagnes', name: 'Gestion des Campagnes', position: { x: '70%', y: '30%' }, planets: [{id: 'p7-ads', name: 'Publicités en ligne', position: {x:'50%', y:'50%'}, documents:[]}] },
      { id: 'ss2-analyse', name: 'Analyse de la Performance', position: { x: '80%', y: '70%' }, planets: [{id: 'p8-reporting', name: 'Reporting', position: {x:'50%', y:'50%'}, documents:[]}] },
    ]
  },
  {
    id: 'g3-prod', name: 'Amas de la Production', type: 'on-path', position: { x: '65%', y: '35%' }, theme: { primary: '#da70d6', secondary: '#ffc0cb' },
    description: "Un amas globulaire dense où les plans se transforment en matière.", valueProposition: "Optimisation des coûts, garantie de la qualité.",
    solarSystems: [
        { id: 'ss3-planning', name: 'Planification', position: { x: '15%', y: '50%' }, planets: [{id: 'p9-pdp', name: 'Plan de Production', position: {x:'50%', y:'50%'}, documents:[]}] },
        { id: 'ss3-appro', name: 'Approvisionnement', position: { x: '45%', y: '25%' }, planets: [{id: 'p10-sourcing', name: 'Sourcing Fournisseurs', position: {x:'50%', y:'50%'}, documents:[]}] },
        { id: 'ss3-fabrication', name: 'Fabrication', position: { x: '55%', y: '75%' }, planets: [{id: 'p11-assemblage', name: 'Chaîne d\'assemblage', position: {x:'50%', y:'50%'}, documents:[]}] },
        { id: 'ss3-logistique', name: 'Logistique', position: { x: '85%', y: '50%' }, planets: [{id: 'p12-expedition', name: 'Expédition', position: {x:'50%', y:'50%'}, documents:[]}] },
    ]
  },
  {
    id: 'g4-support', name: 'Galaxie du Support', type: 'on-path', position: { x: '85%', y: '55%' }, theme: { primary: '#32cd32', secondary: '#98fb98' },
    description: "Une galaxie accueillante où des flottes de vaisseaux sont prêtes à aider les utilisateurs.", valueProposition: "Fidélisation client, amélioration continue des produits.",
    solarSystems: [
        { id: 'ss4-onboarding', name: 'Onboarding Client', position: { x: '25%', y: '25%' }, planets: [{id: 'p13-tutoriels', name: 'Tutoriels', position: {x:'50%', y:'50%'}, documents:[]}] },
        { id: 'ss4-support-tech', name: 'Support Technique', position: { x: '35%', y: '75%' }, planets: [{id: 'p14-ticketing', name: 'Gestion des tickets', position: {x:'50%', y:'50%'}, documents:[]}] },
        { id: 'ss4-gestion-comptes', name: 'Gestion des comptes', position: { x: '65%', y: '75%' }, planets: [{id: 'p15-suivi', name: 'Suivi client', position: {x:'50%', y:'50%'}, documents:[]}] },
        { id: 'ss4-feedback', name: 'Collecte du Feedback', position: { x: '75%', y: '25%' }, planets: [{id: 'p16-enquetes', name: 'Enquêtes de satisfaction', position: {x:'50%', y:'50%'}, documents:[]}] },
    ]
  },
  {
    id: 'g5-strategie', name: 'Singularité Stratégique', type: 'off-path', position: { x: '50%', y: '10%' }, theme: { primary: '#f0e68c', secondary: 'white' },
    description: "Un point unique et massif qui influence la trajectoire de toutes les autres galaxies.", valueProposition: "Aligne l'ensemble des processus sur une vision commune.",
    solarSystems: [ {id: 'ss5-analyse', name: 'Analyse stratégique', position: {x: '50%', y: '50%'}, planets: []} ]
  },
  {
    id: 'g6-iso', name: 'Anomalie Réglementaire ISO', type: 'off-path', position: { x: '25%', y: '85%' }, theme: { primary: '#b0c4de', secondary: '#f0f8ff' },
    description: "Un champ de force complexe qui régit les lois de la sécurité de l'information.", valueProposition: "Garantit la confiance des clients et partenaires.",
    solarSystems: [ {id: 'ss6-audit', name: 'Processus d\'audit', position: {x: '50%', y: '50%'}, planets: []} ]
  }
];

// --- Application ---
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('universe-container');
    const infoPanel = document.getElementById('info-panel');
    const panelContent = document.getElementById('panel-content');
    const closePanelBtn = document.getElementById('close-panel');
    const backButton = document.getElementById('back-button');
    const root = document.documentElement;

    let viewState = {
        level: 'universe',
        activeGalaxyId: null,
        activeSystemId: null,
    };

    function createAndAppend(tag, parent, attributes = {}) {
        const el = document.createElement(tag);
        Object.assign(el, attributes);
        parent.appendChild(el);
        return el;
    }

    function drawPath(points) {
        const svg = createAndAppend('svg', container, { id: 'path-container' });
        svg.style.zIndex = -1;
        const path = createAndAppend('path', svg, { id: 'travel-path' });
        if (points.length < 2) return;
        points.sort((a, b) => a.x - b.x);
        let d = `M ${points[0].x} ${points[0].y}`;
        for (let i = 1; i < points.length; i++) {
            const p1 = points[i-1], p2 = points[i];
            d += ` C ${p1.x + (p2.x - p1.x) / 2},${p1.y} ${p1.x + (p2.x - p1.x) / 2},${p2.y} ${p2.x},${p2.y}`;
        }
        path.setAttribute('d', d);
    }

    function getPixelPositions(elements) {
        const rect = container.getBoundingClientRect();
        return elements.map(el => ({
            x: parseFloat(el.position.x) / 100 * rect.width,
            y: parseFloat(el.position.y) / 100 * rect.height,
        }));
    }

    function render() {
        container.innerHTML = '';
        container.style.transform = ''; // Reset zoom
        backButton.classList.toggle('hidden', viewState.level === 'universe');

        let itemsToRender = [];
        let itemClass = '';
        let clickHandler = () => {};

        if (viewState.level === 'universe') {
            itemsToRender = universeData;
            itemClass = 'galaxy';
            clickHandler = handleGalaxyClick;
            startJourney();
        } else {
            const galaxy = universeData.find(g => g.id === viewState.activeGalaxyId);
            if (!galaxy) return;

            if (viewState.level === 'galaxy') {
                itemsToRender = galaxy.solarSystems;
                itemClass = 'solar-system';
                clickHandler = handleSystemClick;
            } else if (viewState.level === 'system') {
                const system = galaxy.solarSystems.find(s => s.id === viewState.activeSystemId);
                itemsToRender = system?.planets || [];
                itemClass = 'planet';
                clickHandler = handlePlanetClick;
            }
        }

        itemsToRender.forEach(item => {
            const el = createAndAppend('div', container, { id: item.id, className: `${itemClass}` });
            el.textContent = item.name;
            Object.assign(el.style, { left: item.position.x, top: item.position.y, transform: 'translate(-50%, -50%)' });
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                clickHandler(item);
            });
        });

        drawPath(getPixelPositions(itemsToRender));
    }

    function handleGalaxyClick(galaxy) {
        root.style.setProperty('--theme-primary', galaxy.theme.primary);
        root.style.setProperty('--theme-secondary', galaxy.theme.secondary);
        updateInfoPanel(galaxy);
        viewState.level = 'galaxy';
        viewState.activeGalaxyId = galaxy.id;
        render();
    }

    function handleSystemClick(system) {
        updateInfoPanel(system);
        viewState.level = 'system';
        viewState.activeSystemId = system.id;
        render();
    }

    function handlePlanetClick(planet) {
        updateInfoPanel(planet);
    }

    function navigateBack() {
        if (viewState.level === 'system') {
            viewState.level = 'galaxy';
            const galaxy = universeData.find(g => g.id === viewState.activeGalaxyId);
            updateInfoPanel(galaxy);
            viewState.activeSystemId = null;
        } else if (viewState.level === 'galaxy') {
            viewState.level = 'universe';
            viewState.activeGalaxyId = null;
            root.style.removeProperty('--theme-primary');
            root.style.removeProperty('--theme-secondary');
            infoPanel.classList.remove('visible');
        }
        render();
    }

    function updateInfoPanel(data) {
        let content = '', type = '';
        if (data.solarSystems) { type = 'Galaxie / Macro-Processus'; }
        else if (data.planets) { type = 'Système Solaire / Processus'; }
        else { type = 'Planète / Sous-Processus'; }

        content = `<h2 class="text-2xl font-bold text-cyan-400 mb-2">${data.name}</h2><p class="text-sm text-gray-400 mb-4">${type}</p>`;
        if (data.description) {
            content += `<div class="mb-6"><h3 class="font-semibold mb-2 text-gray-200">Description</h3><p class="text-gray-300">${data.description}</p></div>`;
        }
        if (data.kpis && data.kpis.length > 0) {
            const kpiList = data.kpis.map(kpi => `<li class="flex items-center justify-between bg-gray-800 p-2 rounded-md"><span class="flex items-center"><span class="kpi-indicator mr-3 ${Math.random() < 0.6 ? 'bg-green-500' : 'bg-red-500'}"></span><span class="text-gray-300">${kpi.name}</span></span><span class="font-semibold text-white">${kpi.value}</span></li>`).join('');
            content += `<div class="mb-6"><h3 class="font-semibold mb-2 text-gray-200">Indicateurs</h3><ul class="space-y-2">${kpiList}</ul></div>`;
        }
        if (data.documents && data.documents.length > 0) {
            const docList = data.documents.map(doc => `<li class="bg-gray-800 p-2 rounded-md text-gray-300">${doc.name}</li>`).join('');
            content += `<div><h3 class="font-semibold mb-2 text-gray-200">Documents Clés</h3><ul class="space-y-2">${docList}</ul></div>`;
        }
        panelContent.innerHTML = content;
        infoPanel.classList.add('visible');
    }

    function startJourney() {
        if (viewState.level !== 'universe') return;
        const ship = createAndAppend('div', container, { id: 'wikicovage' });
        const path = document.getElementById('travel-path');
        if (!path || path.getTotalLength() === 0) return;
        const pathLength = path.getTotalLength();
        let startTime = null;
        const duration = 15000;
        function animate(timestamp) {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const point = path.getPointAtLength(progress * pathLength);
            const nextPoint = path.getPointAtLength(progress * pathLength + 1 > pathLength ? pathLength : progress * pathLength + 1);
            const angle = Math.atan2(nextPoint.y - point.y, nextPoint.x - point.x);
            ship.style.transform = `translate(${point.x}px, ${point.y}px) rotate(${angle}rad)`;
            if (progress < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
    }

    backButton.addEventListener('click', navigateBack);
    closePanelBtn.addEventListener('click', () => infoPanel.classList.remove('visible'));
    window.addEventListener('resize', render);
    render();
});
