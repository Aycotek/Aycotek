const universeData = [
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
        id: 'ss1-veille', name: 'Processus de Veille', position: { x: '20%', y: '25%' }, connections: ['ss1-ideation'],
        planets: [
          { id: 'p1-veille-tech', name: 'Veille Technologique', position: { x: '30%', y: '40%' }, connections: ['p1-veille-marche'], documents: [
            { name: 'Rapport Tendance IA Q2', creator: 'A. Turing', approver: 'J. Von Neumann', lifespan: '2025-12-31', status: 'approved' },
            { name: 'Analyse concurrentielle Web3', creator: 'S. Nakamoto', approver: 'V. Buterin', lifespan: '2025-06-30', status: 'pending_approval' }
          ]},
          { id: 'p1-veille-marche', name: 'Veille Marché', position: { x: '70%', y: '60%' }, documents: [
            { name: 'Etude de marché - Secteur A', creator: 'P. Kotler', approver: 'D. Ogilvy', lifespan: '2026-01-01', status: 'approved' }
          ]},
        ]
      },
      {
        id: 'ss1-ideation', name: 'Processus d\'Idéation', position: { x: '40%', y: '75%' }, connections: ['ss1-poc'],
        kpis: [{ name: "Taux de conversion Idée->Proto", value: "25%" }],
        planets: [
          { id: 'p2-ateliers', name: 'Ateliers de créativité', position: { x: '25%', y: '60%' }, connections: ['p2-recueil'], documents: [
            { name: 'Compte-rendu Atelier "Blue Sky"', creator: 'L. Pauling', approver: 'M. Curie', lifespan: 'N/A', status: 'approved' }
          ]},
          { id: 'p2-recueil', name: 'Recueil des idées', position: { x: '65%', y: '30%' }, documents: [
            { name: 'Export plateforme à idées v3', creator: 'Admin', approver: 'Admin', lifespan: 'N/A', status: 'approved' }
          ]},
        ]
      },
      {
        id: 'ss1-poc', name: 'Processus de Prototypage', position: { x: '70%', y: '20%' }, connections: ['ss1-validation'],
        planets: [
          { id: 'p3-maquettage', name: 'Maquettage UX/UI', position: { x: '40%', y: '30%' }, connections: ['p3-dev-poc'], documents: [
            { name: 'Maquette Figma v4', creator: 'J. Ive', approver: 'S. Jobs', lifespan: '2025-02-01', status: 'pending_approval' }
          ]},
          { id: 'p3-dev-poc', name: 'Développement PoC', position: { x: '60%', y: '70%' }, documents: [
            { name: 'Lien vers repo Git du PoC', creator: 'L. Torvalds', approver: 'R. Stallman', lifespan: 'N/A', status: 'approved' }
          ]},
        ]
      },
       {
        id: 'ss1-validation', name: 'Processus de Validation', position: { x: '80%', y: '70%' },
        planets: [
          { id: 'p4-tests-utilisateurs', name: 'Tests Utilisateurs', position: { x: '35%', y: '65%' }, connections: ['p4-validation-metier'], documents: [
            { name: 'Retours verbatim utilisateurs', creator: 'U. Xperience', approver: 'C. Satisfaction', lifespan: '2025-04-15', status: 'approved' }
          ]},
          { id: 'p4-validation-metier', name: 'Validation Métier', position: { x: '75%', y: '35%' }, documents: [
            { name: 'PV de validation du COPIL', creator: 'C.E.O.', approver: 'C.O.O.', lifespan: '2025-05-01', status: 'approved' }
          ]},
        ]
      }
    ]
  },
  {
    id: 'g2-market', name: 'Galaxie de la Commercialisation', type: 'on-path', position: { x: '40%', y: '60%' }, theme: { primary: '#ff8c00', secondary: '#ffdd00' },
    description: 'Une galaxie spirale où les prototypes sont polis pour devenir des produits phares.', valueProposition: "Augmentation des parts de marché, croissance du chiffre d'affaires.",
    solarSystems: [
      { id: 'ss2-strategie', name: 'Stratégie Marketing', position: { x: '20%', y: '30%' }, connections: ['ss2-contenu'], planets: [{id: 'p5-branding', name: 'Branding', position: {x:'50%', y:'50%'}, documents:[{name: 'Charte Graphique v2', creator: 'P. Rand', approver: 'S. Bass', lifespan: '2028-01-01', status: 'approved' }]}] },
      { id: 'ss2-contenu', name: 'Création de Contenu', position: { x: '40%', y: '70%' }, connections: ['ss2-campagnes'], planets: [{id: 'p6-blog', name: 'Blog', position: {x:'50%', y:'50%'}, documents:[{name: 'Article "Top 10 Features"', creator: 'S. Godin', approver: 'J. Dujardin', lifespan: 'N/A', status: 'pending_approval' }]}] },
      { id: 'ss2-campagnes', name: 'Gestion des Campagnes', position: { x: '70%', y: '30%' }, connections: ['ss2-analyse'], planets: [{id: 'p7-ads', name: 'Publicités en ligne', position: {x:'50%', y:'50%'}, documents:[{name: 'Rapport Campagne T2', creator: 'D. Draper', approver: 'P. Olson', lifespan: '2025-07-15', status: 'approved' }]}] },
      { id: 'ss2-analyse', name: 'Analyse de la Performance', position: { x: '80%', y: '70%' }, planets: [{id: 'p8-reporting', name: 'Reporting', position: {x:'50%', y:'50%'}, documents:[{name: 'Dashboard Suivi Ventes', creator: 'Data Team', approver: 'C.F.O.', lifespan: 'N/A', status: 'approved' }]}] },
    ]
  },
  // ... (le reste des données reste identique)
];

// --- Application ---
document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('map-container');
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
        const svg = createAndAppend('svg', mapContainer, { id: 'path-container' });
        svg.style.zIndex = -1;
        const path = createAndAppend('path', svg, { id: 'travel-path' });
        if (points.length < 2) return;

        const rect = mapContainer.getBoundingClientRect();
        const pixelPoints = points.map(p => ({
            x: parseFloat(p.position.x) / 100 * rect.width,
            y: parseFloat(p.position.y) / 100 * rect.height,
        }));

        pixelPoints.sort((a, b) => a.x - b.x);
        let d = `M ${pixelPoints[0].x} ${pixelPoints[0].y}`;
        for (let i = 1; i < pixelPoints.length; i++) {
            const p1 = pixelPoints[i-1], p2 = pixelPoints[i];
            d += ` C ${p1.x + (p2.x - p1.x) / 2},${p1.y} ${p1.x + (p2.x - p1.x) / 2},${p2.y} ${p2.x},${p2.y}`;
        }
        path.setAttribute('d', d);
    }

    function render() {
        mapContainer.innerHTML = '';
        mapContainer.style.transform = 'translate(0,0) scale(1)';
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
            const el = createAndAppend('div', mapContainer, { id: item.id, className: `${itemClass} is-fading-in`});
            el.textContent = item.name;
            Object.assign(el.style, { left: item.position.x, top: item.position.y, transform: 'translate(-50%, -50%)' });

            el.addEventListener('click', (e) => {
                e.stopPropagation();
                clickHandler(item);
            });

            el.addEventListener('mouseover', () => handleMouseOver(item, itemsToRender));
            el.addEventListener('mouseout', handleMouseOut);
        });
        drawPath(itemsToRender);
        drawConnectionLines(itemsToRender);
    }

    function drawConnectionLines(items) {
        const svg = document.getElementById('path-container') || createAndAppend('svg', mapContainer, { id: 'path-container' });
        const rect = mapContainer.getBoundingClientRect();

        const positions = {};
        items.forEach(item => {
            positions[item.id] = {
                x: parseFloat(item.position.x) / 100 * rect.width,
                y: parseFloat(item.position.y) / 100 * rect.height,
            };
        });

        items.forEach(item => {
            if (item.connections) {
                item.connections.forEach(targetId => {
                    const startPos = positions[item.id];
                    const endPos = positions[targetId];
                    if (startPos && endPos) {
                        const line = createAndAppend('line', svg, {
                            className: 'connection-line',
                            'data-from': item.id,
                            'data-to': targetId
                        });
                        line.setAttribute('x1', startPos.x);
                        line.setAttribute('y1', startPos.y);
                        line.setAttribute('x2', endPos.x);
                        line.setAttribute('y2', endPos.y);
                    }
                });
            }
        });
    }

    function transitionTo(newState, clickedElement) {
        Array.from(mapContainer.children).forEach(child => child.classList.add('is-fading-out'));

        if (clickedElement) {
            const rect = clickedElement.getBoundingClientRect();
            const containerRect = mapContainer.getBoundingClientRect();
            const scale = 3;
            const translateX = (containerRect.width / 2) - rect.left - (rect.width / 2);
            const translateY = (containerRect.height / 2) - rect.top - (rect.height / 2);
            mapContainer.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        }

        setTimeout(() => {
            Object.assign(viewState, newState);
            render();
        }, 500);
    }

    function handleGalaxyClick(galaxy) {
        root.style.setProperty('--theme-primary', galaxy.theme.primary);
        root.style.setProperty('--theme-secondary', galaxy.theme.secondary);
        updateInfoPanel(galaxy);
        transitionTo({ level: 'galaxy', activeGalaxyId: galaxy.id }, document.getElementById(galaxy.id));
    }

    function handleSystemClick(system) {
        updateInfoPanel(system);
        transitionTo({ level: 'system', activeSystemId: system.id }, document.getElementById(system.id));
    }

    function handlePlanetClick(planet) {
        updateInfoPanel(planet);
    }

    function handleMouseOver(item, allItems) {
        if (!item.connections) return;

        // Highlight the item itself
        document.getElementById(item.id)?.classList.add('highlighted');

        // Highlight connections and connected items
        item.connections.forEach(targetId => {
            document.getElementById(targetId)?.classList.add('highlighted');
            // Highlight the line connecting them
            const line = document.querySelector(`.connection-line[data-from='${item.id}'][data-to='${targetId}']`);
            line?.classList.add('highlighted');
        });
    }

    function handleMouseOut() {
        document.querySelectorAll('.highlighted').forEach(el => el.classList.remove('highlighted'));
    }

    function navigateBack() {
        let targetLevel, stateUpdates;
        if (viewState.level === 'system') {
            targetLevel = 'galaxy';
            const galaxy = universeData.find(g => g.id === viewState.activeGalaxyId);
            updateInfoPanel(galaxy);
            stateUpdates = { activeSystemId: null };
        } else if (viewState.level === 'galaxy') {
            targetLevel = 'universe';
            root.style.removeProperty('--theme-primary');
            root.style.removeProperty('--theme-secondary');
            infoPanel.classList.remove('visible');
            stateUpdates = { activeGalaxyId: null, activeSystemId: null };
        }

        Array.from(mapContainer.children).forEach(child => child.classList.add('is-fading-out'));
        setTimeout(() => {
            Object.assign(viewState, { level: targetLevel, ...stateUpdates });
            render();
        }, 500);
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
            const docList = data.documents.map(doc => {
                const statusColor = doc.status === 'pending_approval' ? 'text-yellow-400' : 'text-gray-400';
                return `<li class="bg-gray-800 p-3 rounded-md">
                          <p class="text-gray-100">${doc.name}</p>
                          <div class="text-xs mt-2 space-y-1 ${statusColor}">
                            <p>Créateur: ${doc.creator} | Approbateur: ${doc.approver}</p>
                            <p>Fin de vie: ${doc.lifespan} | Statut: ${doc.status.replace('_', ' ')}</p>
                          </div>
                        </li>`;
            }).join('');
            content += `<div><h3 class="font-semibold mb-2 text-gray-200">Documents Clés</h3><ul class="space-y-2">${docList}</ul></div>`;
        }
        panelContent.innerHTML = content;
        infoPanel.classList.add('visible');
    }

    function startJourney() {
        if (viewState.level !== 'universe') return;
        const ship = createAndAppend('div', mapContainer, { id: 'wikicovage' });
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
