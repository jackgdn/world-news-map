const openfreemap = new ol.layer.Group();

const vectorSource = new ol.source.Vector();
const markersLayer = new ol.layer.Vector({
    source: vectorSource,
    style: new ol.style.Style({
        image: new ol.style.Circle({
            radius: 7,
            fill: new ol.style.Fill({ color: '#2a70d6' }),
            stroke: new ol.style.Stroke({ color: '#ffffff', width: 1.5 }),
        }),
    }),
});

const map = new ol.Map({
    target: 'map',
    layers: [
        openfreemap,
        markersLayer,
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([0, 0]),
        zoom: 2,
    }),
    controls: ol.control.defaults.defaults({
        zoom: false,
        rotate: false,
        attribution: true,
    }),
});

olms.apply(openfreemap, 'https://tiles.openfreemap.org/styles/liberty');

const popupElement = document.getElementById('marker-popup');
const POPUP_ANIMATION_MS = 220;
let popupHideTimer = null;
const popupOverlay = new ol.Overlay({
    element: popupElement,
    positioning: 'bottom-center',
    offset: [0, -12],
    stopEvent: true,
});
map.addOverlay(popupOverlay);

function closePopup() {
    if (popupHideTimer) {
        clearTimeout(popupHideTimer);
        popupHideTimer = null;
    }

    popupElement.classList.remove('is-visible');
    popupElement.setAttribute('aria-hidden', 'true');

    popupHideTimer = setTimeout(() => {
        popupOverlay.setPosition(undefined);
        popupElement.style.display = 'none';
        popupHideTimer = null;
    }, POPUP_ANIMATION_MS);
}

function openPopup(html, lon, lat) {
    if (popupHideTimer) {
        clearTimeout(popupHideTimer);
        popupHideTimer = null;
    }

    popupElement.innerHTML = html;
    popupOverlay.setPosition(ol.proj.fromLonLat([lon, lat]));
    popupElement.style.display = 'block';
    popupElement.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => {
        popupElement.classList.add('is-visible');
    });
}

map.on('singleclick', (event) => {
    const feature = map.forEachFeatureAtPixel(event.pixel, (foundFeature) => foundFeature);
    if (!feature) {
        closePopup();
        return;
    }

    const popupHtml = feature.get('popupHtml') || '';
    const lon = Number(feature.get('longitude'));
    const lat = Number(feature.get('latitude'));
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
        closePopup();
        return;
    }

    openPopup(popupHtml, lon, lat);
});

map.on('pointermove', (event) => {
    if (event.dragging) return;
    const hasFeature = map.hasFeatureAtPixel(event.pixel);
    map.getTargetElement().style.cursor = hasFeature ? 'pointer' : '';
});

const markerMap = new Map();

const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('toggle-btn');
const tabButtons = Array.from(document.querySelectorAll('.tab-btn'));
const tabPanels = {
    other: document.getElementById('tab-other'),
    all: document.getElementById('tab-all'),
};
let lastUpdateValue = '--';
let lastUpdateParsedDate = null;
let sidebarCollapsed = false;

function updateToggleButtonVisual() {
    const isMobile = window.matchMedia('(max-width: 768px)').matches;
    if (isMobile) {
        toggleBtn.textContent = sidebarCollapsed ? '▲' : '▼';
        toggleBtn.setAttribute('aria-label', sidebarCollapsed ? '展开底部栏' : '收起底部栏');
        return;
    }

    toggleBtn.textContent = sidebarCollapsed ? '»' : '«';
    toggleBtn.setAttribute('aria-label', sidebarCollapsed ? '展开侧边栏' : '收起侧边栏');
}

updateToggleButtonVisual();
window.addEventListener('resize', updateToggleButtonVisual);

toggleBtn.addEventListener('click', () => {
    sidebarCollapsed = !sidebarCollapsed;
    sidebar.classList.toggle('collapsed');
    toggleBtn.classList.toggle('is-collapsed', sidebarCollapsed);
    updateToggleButtonVisual();
    map.updateSize();
});

tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
        const tab = btn.getAttribute('data-tab');
        tabButtons.forEach((b) => b.classList.toggle('active', b === btn));
        Object.entries(tabPanels).forEach(([key, panel]) => {
            panel.classList.toggle('active', key === tab);
        });
    });
});

function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatLocalDateTime(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    const second = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

function formatTimezoneLabel(date) {
    const offsetMinutes = -date.getTimezoneOffset();
    const sign = offsetMinutes >= 0 ? '+' : '-';
    const absoluteMinutes = Math.abs(offsetMinutes);
    const hours = String(Math.floor(absoluteMinutes / 60)).padStart(2, '0');
    const minutes = String(absoluteMinutes % 60).padStart(2, '0');
    return `UTC${sign}${hours}:${minutes}`;
}

function formatRelativeTime(date) {
    const diffMs = Date.now() - date.getTime();
    if (!Number.isFinite(diffMs)) return '';

    if (diffMs < 60 * 1000) {
        return 'just updated';
    }

    const minutes = Math.floor(diffMs / (60 * 1000));
    if (minutes < 60) {
        return `${minutes} minutes ago`;
    }

    const hours = Math.floor(diffMs / (60 * 60 * 1000));
    if (hours < 24) {
        return `${hours} hours ago`;
    }

    const days = Math.floor(diffMs / (24 * 60 * 60 * 1000));
    return `${days} days ago`;
}

function getLastSevenDates() {
    const dates = [];
    const now = new Date();
    for (let i = 0; i < 7; i += 1) {
        const d = new Date(now);
        d.setDate(now.getDate() - i);
        dates.push(formatDate(d));
    }
    return dates;
}

function isValidCoordinate(coord) {
    if (!coord) return false;
    const lat = Number(coord.latitude);
    const lon = Number(coord.longitude);
    if (lat === null || lon === null || lat === undefined || lon === undefined) {
        return false;
    }
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
    if (lat === -1 && lon === -1) return false;
    return true;
}

function buildLinksHtml(links) {
    if (!Array.isArray(links) || links.length === 0) return '';
    return links.map((item) => {
        const label = item.source;
        return `<a href="${item.url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
    }).join('');
}

function createNewsCard(item, onClickCallback) {
    const card = document.createElement('div');
    card.className = 'news-item';
    const title = item.description;
    const time = item.date || '';
    const linksHtml = buildLinksHtml(item.links);

    card.innerHTML = `
        <div class="news-title">${title}</div>
        <div class="news-time">${time}</div>
        <div class="news-links">${linksHtml}</div>
    `;

    if (onClickCallback) {
        card.addEventListener('click', () => onClickCallback(item));
    }

    return card;
}

function buildPopupHtml(itemsAtPoint) {
    const sorted = [...itemsAtPoint].sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));
    const lines = sorted.map((it) => {
        const linksHtml = buildLinksHtml(it.links);
        const time = it.date || '';
        return `<div class="news-item">
            <div class="news-title">${it.description}</div>
            <div class="news-time">${time}</div>
            <div class="news-links">${linksHtml}</div>
        </div>`;
    }).join('');
    return `<div>${lines}</div>`;
}

function focusOnMarker(item) {
    if (!isValidCoordinate(item.coordinate)) return;
    const lat = Number(item.coordinate.latitude);
    const lon = Number(item.coordinate.longitude);
    map.getView().animate({
        center: ol.proj.fromLonLat([lon, lat]),
        zoom: 10,
        duration: 250,
    });

    const key = `${lat},${lon}`;
    if (markerMap.has(key)) {
        const markerInfo = markerMap.get(key);
        openPopup(markerInfo.popupHtml, markerInfo.longitude, markerInfo.latitude);
    }
}

function renderTabHeaders() {
    tabPanels.other.innerHTML = `<div class="sidebar-header">Other News <span class="header-update">Last Update: ${lastUpdateValue}</span></div>`;
    tabPanels.all.innerHTML = `<div class="sidebar-header">News List <span class="header-update">Last Update: ${lastUpdateValue}</span></div>`;
}

function refreshLastUpdateDisplay() {
    if (!lastUpdateParsedDate) {
        return;
    }

    const timezoneLabel = formatTimezoneLabel(lastUpdateParsedDate);
    const localText = formatLocalDateTime(lastUpdateParsedDate);
    const relativeText = formatRelativeTime(lastUpdateParsedDate);
    lastUpdateValue = `${timezoneLabel} ${localText} (${relativeText})`;
    renderTabHeaders();
}

function setLastUpdateText(value) {
    const raw = (value || '').trim();
    if (!raw) {
        lastUpdateValue = '--';
        lastUpdateParsedDate = null;
        renderTabHeaders();
        return;
    }

    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) {
        lastUpdateValue = raw;
        lastUpdateParsedDate = null;
        renderTabHeaders();
        return;
    }

    lastUpdateParsedDate = parsed;
    refreshLastUpdateDisplay();
}

async function fetchLastUpdateFromSecurityTxt() {
    try {
        const response = await fetch(`./.well-known/security.txt`);
        if (!response.ok) {
            setLastUpdateText('');
            return;
        }

        const text = await response.text();
        const lines = text.split(/\r?\n/);
        const secondLine = (lines[1] || '').trim();
        const matched = secondLine.match(/^#\s*Generated on\s+(.+)$/i);

        if (matched && matched[1]) {
            setLastUpdateText(matched[1].trim());
            return;
        }

        setLastUpdateText('');
    } catch (error) {
        console.error('Failed to fetch last update from security.txt:', error);
        setLastUpdateText('');
    }
}

async function fetchNews() {
    renderTabHeaders();
    vectorSource.clear();
    markerMap.clear();
    closePopup();

    const dates = getLastSevenDates();
    const allItems = [];

    await Promise.all(dates.map(async (date) => {
        const url = `./news/${date}.json`;
        try {
            const response = await fetch(url);
            if (!response.ok) return;
            const dayItems = await response.json();
            if (Array.isArray(dayItems)) {
                allItems.push(...dayItems);
            }
        } catch (error) {
            console.error(`Failed to fetch news for ${date}:`, error);
        }
    }));

    const noCoordinateItems = [];
    const groupedByCoordinate = new Map();

    allItems.forEach((item) => {
        const status = item.status || 'unknown';

        if (status === 'no_valid_coordinate') {
            noCoordinateItems.push(item);
        } else if (status === 'coordinate_fetched') {
            if (isValidCoordinate(item.coordinate)) {
                const lat = Number(item.coordinate.latitude);
                const lon = Number(item.coordinate.longitude);
                const key = `${lat},${lon}`;
                if (!groupedByCoordinate.has(key)) {
                    groupedByCoordinate.set(key, []);
                }
                groupedByCoordinate.get(key).push(item);
            } else {
                noCoordinateItems.push(item);
            }
        }
    });

    groupedByCoordinate.forEach((itemsAtPoint, key) => {
        const [lat, lon] = key.split(',').map(Number);
        const popupHtml = buildPopupHtml(itemsAtPoint);
        const markerFeature = new ol.Feature({
            geometry: new ol.geom.Point(ol.proj.fromLonLat([lon, lat])),
        });
        markerFeature.set('popupHtml', popupHtml);
        markerFeature.set('latitude', lat);
        markerFeature.set('longitude', lon);
        vectorSource.addFeature(markerFeature);

        markerMap.set(key, {
            popupHtml,
            latitude: lat,
            longitude: lon,
        });
    });

    noCoordinateItems.forEach((item) => {
        tabPanels.other.appendChild(createNewsCard(item, focusOnMarker));
    });

    if (noCoordinateItems.length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'empty-msg';
        emptyMsg.style.cssText = 'color: #999; font-size: 12px; padding: 20px 0;';
        emptyMsg.textContent = 'No News Here';
        tabPanels.other.appendChild(emptyMsg);
    }

    const validCoordinateItems = Array.from(groupedByCoordinate.values()).flat();
    const allFilteredItems = [...noCoordinateItems, ...validCoordinateItems];
    allFilteredItems.sort((a, b) => new Date(b.date) - new Date(a.date));

    allFilteredItems.forEach((item) => {
        tabPanels.all.appendChild(createNewsCard(item, focusOnMarker));
    });

    if (allFilteredItems.length === 0) {
        const emptyMsg = document.createElement('div');
        emptyMsg.className = 'empty-msg';
        emptyMsg.style.cssText = 'color: #999; font-size: 12px; padding: 20px 0;';
        emptyMsg.textContent = 'No News Here';
        tabPanels.all.appendChild(emptyMsg);
    }
}

(async () => {
    await fetchLastUpdateFromSecurityTxt();
    await fetchNews();
})();
