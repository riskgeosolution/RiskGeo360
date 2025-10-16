// Constantes e Variáveis Globais
const INITIAL_LATITUDE = -15.78;
const INITIAL_LONGITUDE = -47.92;
const ZOOM_LEVEL = 4;
let updateIntervalId = null;
let currentCoords = { lat: INITIAL_LATITUDE, lon: INITIAL_LONGITUDE };
let currentCityName = "Brasília";
let currentCharts = {};
let pluvioChartInstance = null;
let lastMapView = null; // Variável para guardar o estado do mapa

// Mapeamento de níveis de risco para texto
const riskTextMap = {
    VERDE: "Observação",
    AMARELO: "Atenção",
    LARANJA: "Alto Risco",
    VERMELHO: "Risco Extremo",
    ERRO: "Erro"
};

// Mapeamento de cor para Nível (para o painel lateral)
const colorToRiskMap = {
    "#008000": "Observação",
    "#FFFF00": "Atenção",
    "#FFA500": "Alto Risco",
    "#FF0000": "Risco Extremo",
    "#999": "Carregando"
};


// ==========================================================
// Mapeamento de Elementos e Navegação
// ==========================================================
const tempElement = document.getElementById('temperatura');
const chuvaHistElement = document.getElementById('chuva-agora');
const chuvaFutElement = document.getElementById('chuva-futura');
const nomeCidadeElement = document.getElementById('nome-cidade');
const alertaPanel = document.getElementById('alerta-panel');
const mapContainer = document.getElementById('map-container');
const dashboardContainer = document.getElementById('dashboard-container');
const dashboardTitle = document.getElementById('dashboard-title');
const openDashboardBtn = document.getElementById('open-dashboard-btn');
const backToMapBtn = document.getElementById('back-to-map-btn');
const periodoSelector = document.getElementById('periodo-selector');
const municipioDisplay = document.getElementById('municipio-display');
const toggleDetalhesBtn = document.getElementById('toggle-detalhes-btn');
const detalhesContainer = document.getElementById('detalhes-adicionais-container');
const monitorRoomBtn = document.getElementById('monitor-room-btn');
const monitorRoomContainer = document.getElementById('monitor-room-container');
const backToMapFromMonitorBtn = document.getElementById('back-to-map-from-monitor-btn');
const capitaisGridContainer = document.getElementById('capitais-grid-container');
const alertaTituloElement = document.getElementById('alerta-titulo');

// ==========================================================
// FUNÇÕES AUXILIARES
// ==========================================================
function converterCodigoTempo(code) {
    const codes = {
        0: "Céu Limpo", 1: "Céu Parcialmente Nublado", 2: "Céu Nublado", 3: "Céu Encoberto",
        45: "Neblina", 48: "Névoa", 51: "Chuvisco Leve", 53: "Chuvisco Moderado", 55: "Chuvisco Intenso",
        61: "Chuva Leve", 63: "Chuva Moderada", 65: "Chuva Forte", 80: "Pancadas de Chuva Leve",
        81: "Pancadas de Chuva Moderada", 82: "Pancadas de Chuva Forte", 95: "Tempestade",
        96: "Tempestade com Granizo Leve", 99: "Tempestade com Granizo Forte"
    };
    return codes[code] || `Cód. ${code}`;
}


// ==========================================================
// FUNÇÕES DE NAVEGAÇÃO E SALA DE MONITORAMENTO
// ==========================================================
function showDashboard() {
    mapContainer.style.display = 'none';
    monitorRoomContainer.style.display = 'none';
    dashboardContainer.style.display = 'block';
    dashboardTitle.textContent = `Pluviometria Histórica para ${currentCityName}`;
    municipioDisplay.textContent = `Município: ${currentCityName} - Estação: Modelo ERA5`;
    periodoSelector.value = '72';
    fetchAndRenderPluvioChart(currentCoords.lat, currentCoords.lon, currentCityName, periodoSelector.value);
    fetchAndRenderForecastChart(currentCoords.lat, currentCoords.lon, currentCityName);
    fetchAndRenderDetailCards(currentCoords.lat, currentCoords.lon, currentCityName); // Busca os dados para os cards
    map.invalidateSize();
}

function showMap() {
    dashboardContainer.style.display = 'none';
    monitorRoomContainer.style.display = 'none';
    mapContainer.style.display = 'block';
    if(detalhesContainer) detalhesContainer.style.display = 'none';
    if(toggleDetalhesBtn) toggleDetalhesBtn.textContent = 'Ver Detalhes Adicionais';

    // Se um estado anterior do mapa foi salvo, restaura-o
    if (lastMapView) {
        map.setView(lastMapView.center, lastMapView.zoom);
    }

    // Garante que o mapa seja renderizado corretamente após a transição
    setTimeout(() => {
        map.invalidateSize();
    }, 10);
}

function showMonitorRoom() {
    mapContainer.style.display = 'none';
    dashboardContainer.style.display = 'none';
    monitorRoomContainer.style.display = 'block';
    fetchCapitaisRisco();
}

async function fetchCapitaisRisco() {
    capitaisGridContainer.innerHTML = '<div>Aguardando dados das cidades...</div>';
    try {
        const response = await fetch(`/api/capitais_risco`);
        const dados = await response.json();
        if (!response.ok || dados.error) throw new Error(dados.error || 'Falha na comunicação com o servidor.');
        renderCapitaisCards(dados);
    } catch (error) {
        console.error("Falha na rede ao buscar Sala de Monitoramento:", error);
        capitaisGridContainer.innerHTML = `<div>ERRO DE CONEXÃO: Verifique o console do navegador e o terminal do servidor Flask.</div>`;
    }
}

function renderCapitaisCards(capitais) {
    capitaisGridContainer.innerHTML = '';
    let htmlContent = '';
    capitais.forEach(cidade => {
        const riscoNivel = cidade.risco_nivel.nivel;
        const riscoTexto = riskTextMap[riscoNivel] || 'Indefinido';
        const cameraButton = cidade.camera_url ? `<a href="${cidade.camera_url}" target="_blank" class="camera-btn" style="background-color: #3f51b5; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 0.9em; margin-top: 10px; display: inline-block;">Ver Câmera</a>` : '';
        htmlContent += `
            <div class="capital-card">
                <span class="card-city-name">${cidade.capital} (${cidade.estado})</span>
                <span class="card-risk-level nivel-${riscoNivel}" title="Maior Risco (Hist. ou Futuro): ${cidade.maior_risco_valor.toFixed(1)} mm">${riscoTexto}</span>
                <div class="card-details" style="font-size: 0.9em; color: #333; margin-top: 10px;">
                    <span>Acum. 24h: <strong>${cidade.chuva_24h.toFixed(1)} mm</strong></span><br>
                    <span>Acum. 72h: <strong>${cidade.chuva_72h.toFixed(1)} mm</strong></span>
                </div>
                ${cameraButton}
            </div>`;
    });
    capitaisGridContainer.innerHTML = htmlContent;
}

if(toggleDetalhesBtn) {
    toggleDetalhesBtn.onclick = () => {
        const isHidden = detalhesContainer.style.display === 'none';
        detalhesContainer.style.display = isHidden ? 'block' : 'none';
        toggleDetalhesBtn.textContent = isHidden ? 'Ocultar Detalhes Adicionais' : 'Ver Detalhes Adicionais';
    };
}

if(periodoSelector) {
    periodoSelector.onchange = function() {
        fetchAndRenderPluvioChart(currentCoords.lat, currentCoords.lon, currentCityName, this.value);
    };
}

openDashboardBtn.onclick = showDashboard;
backToMapBtn.onclick = showMap;
monitorRoomBtn.onclick = showMonitorRoom;
backToMapFromMonitorBtn.onclick = showMap;

// ==========================================================
// FUNÇÕES DE BUSCA DE DADOS E RENDERIZAÇÃO
// ==========================================================
async function determinarNivelAlerta(historico, futura) {
    const maiorRisco = Math.max(historico, futura);
    if (maiorRisco >= 30) return "#FF0000";
    if (maiorRisco >= 20) return "#FFA500";
    if (maiorRisco >= 10) return "#FFFF00";
    return "#008000";
}

async function fetchAndRenderDetailCards(latitude, longitude, nomeLocal) {
    try {
        const response = await fetch(`/api/weather?lat=${latitude}&lon=${longitude}&nome_cidade=${encodeURIComponent(nomeLocal)}`);
        if (!response.ok) throw new Error('Falha na resposta da API');
        const dados = await response.json();

        const detailsHtml = `
            <h2 style="text-align: left; margin-bottom: 15px; color: #003296;">Informações Detalhadas (Atual)</h2>
            <div class="details-grid">
                <div class="detail-card">
                    <span class="detail-label">Condição Atual</span>
                    <span class="detail-value">${dados.descricao_tempo || '--'}</span>
                </div>
                <div class="detail-card">
                    <span class="detail-label">Sensação Térmica</span>
                    <span class="detail-value">${dados.sensacao_termica?.toFixed(1) || '--'} °C</span>
                </div>
                <div class="detail-card">
                    <span class="detail-label">Umidade Relativa</span>
                    <span class="detail-value">${dados.umidade_relativa?.toFixed(0) || '--'} %</span>
                </div>
                <div class="detail-card">
                    <span class="detail-label">Ponto de Orvalho</span>
                    <span class="detail-value">${dados.ponto_orvalho?.toFixed(1) || '--'} °C</span>
                </div>
                <div class="detail-card">
                    <span class="detail-label">Pressão Atmosférica</span>
                    <span class="detail-value">${dados.pressao?.toFixed(0) || '--'} hPa</span>
                </div>
                <div class="detail-card">
                    <span class="detail-label">Vento Atual (10m)</span>
                    <span class="detail-value">${dados.velocidade_vento?.toFixed(1) || '--'} km/h</span>
                </div>
                 <div class="detail-card">
                    <span class="detail-label">Rajada de Vento (Máx)</span>
                    <span class="detail-value">${dados.rajada_vento?.toFixed(1) || '--'} km/h</span>
                </div>
            </div>
        `;
        detalhesContainer.innerHTML = detailsHtml;

    } catch (error) {
        console.error("Falha ao carregar detalhes atuais:", error);
        detalhesContainer.innerHTML = '<p>Erro ao carregar detalhes atuais.</p>';
    }
}

async function fetchAndRenderPluvioChart(latitude, longitude, nomeLocal, periodoHoras) {
    dashboardTitle.textContent = `Carregando dados de ${periodoHoras}h para ${nomeLocal}...`;
    try {
        const response = await fetch(`/api/historical_pluvio?lat=${latitude}&lon=${longitude}&periodo=${periodoHoras}&nome_cidade=${encodeURIComponent(nomeLocal)}`);
        const data = await response.json();
        if (!response.ok || data.error || data.volume_pluviometria === undefined) throw new Error(data.error || 'Dados incompletos da API.');
        const hourlyData = data.volume_pluviometria || [];
        const labels = data.data_pluviometria.map(t => new Date(t).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(',', ''));
        let acumulado = 0;
        const acumuladoArray = hourlyData.map(val => (acumulado += (val || 0)));
        const pluvioCtx = document.getElementById('pluvioChart').getContext('2d');
        if (currentCharts.pluvio) currentCharts.pluvio.destroy();
        currentCharts.pluvio = new Chart(pluvioCtx, {
            type: 'bar',
            data: { labels, datasets: [ { label: 'Pluviometria (mm)', data: hourlyData, backgroundColor: 'rgba(54, 162, 235, 0.7)', yAxisID: 'y-pluv', order: 2 }, { label: `Acumulado ${periodoHoras}h: ${data.acumulado_total.toFixed(1)} mm`, data: acumuladoArray, type: 'line', borderColor: 'black', borderWidth: 2, pointRadius: 0, fill: false, yAxisID: 'y-pluv', order: 1 } ] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { id: 'y-pluv', position: 'left', beginAtZero: true, title: { display: true, text: 'Pluviometria (mm)' } }, x: { ticks: { autoSkip: true, maxRotation: 45, minRotation: 45, font: { size: 10 } } } } }
        });
        dashboardTitle.textContent = `Pluviometria Histórica para ${data.cidade}`;
        municipioDisplay.textContent = `Município: ${data.municipio} | Total Acumulado: ${data.acumulado_total.toFixed(1)} mm`;
    } catch (error) {
        dashboardTitle.textContent = `ERRO ao carregar Pluviometria: ${error.message}`;
    }
}

async function fetchAndRenderForecastChart(latitude, longitude, nomeLocal) {
    try {
        const response = await fetch(`/api/forecast_chart?lat=${latitude}&lon=${longitude}&nome_cidade=${encodeURIComponent(nomeLocal)}`);
        const forecastData = await response.json();
        if (!response.ok || forecastData.error || !forecastData.hourly) throw new Error(forecastData.error || 'Dados de previsão incompletos.');

        const hourlyData = forecastData.hourly.precipitation.slice(0, 72) || [];
        const timeLabels = forecastData.hourly.time.slice(0, 72) || [];
        let acumulado = 0;
        const acumuladoArray = hourlyData.map(val => (acumulado += (val || 0)));
        const labels = timeLabels.map(t => new Date(t).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).replace(',', ''));
        const previsaoCtx = document.getElementById('previsaoChart').getContext('2d');
        if (currentCharts.previsao) currentCharts.previsao.destroy();
        currentCharts.previsao = new Chart(previsaoCtx, {
            type: 'bar',
            data: { labels, datasets: [ { label: 'Pluviometria Prevista (mm)', data: hourlyData, backgroundColor: 'rgba(255, 159, 64, 0.7)', yAxisID: 'y-pluv', order: 2 }, { label: `Acumulado Futuro: ${acumulado.toFixed(1)} mm`, data: acumuladoArray, type: 'line', borderColor: '#FF4500', borderWidth: 2, pointRadius: 0, fill: false, yAxisID: 'y-pluv', order: 1 } ] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { id: 'y-pluv', position: 'left', beginAtZero: true, title: { display: true, text: 'Pluviometria (mm)' } }, x: { ticks: { autoSkip: true, maxRotation: 45, minRotation: 45, font: { size: 10 } } } } }
        });
    } catch (error) {
        console.error("Falha ao carregar Gráfico de Previsão:", error);
    }
}

// ==========================================================
// INICIALIZAÇÃO E MANIPULAÇÃO DO MAPA
// ==========================================================
const map = L.map('map').setView([INITIAL_LATITUDE, INITIAL_LONGITUDE], ZOOM_LEVEL);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);

const geocoder = L.Control.geocoder({ position: 'topleft', collapsed: false, placeholder: 'Pesquisar cidade aqui...', defaultMarkGeocode: false }).addTo(map);
geocoder.on('markgeocode', e => {
    const { center, name } = e.geocode;
    // Salva a visualização do mapa ANTES de aplicar o zoom da busca
    lastMapView = { center: map.getCenter(), zoom: map.getZoom() };
    map.setView(center, 13);
    processarNovoLocal(center.lat, center.lng, name.split(',')[0].trim());
});

function processarNovoLocal(latitude, longitude, nomeLocal) {
    if (updateIntervalId) clearInterval(updateIntervalId);
    currentCoords = { lat: latitude, lon: longitude };
    currentCityName = nomeLocal;
    nomeCidadeElement.textContent = nomeLocal;
    carregarDadosClimaticos(latitude, longitude, nomeLocal);
    updateIntervalId = setInterval(() => carregarDadosClimaticos(currentCoords.lat, currentCoords.lon, currentCityName), 600000); // 10 min
}

async function carregarDadosClimaticos(latitude, longitude, nomeLocal) {
    tempElement.textContent = "Carregando...";
    chuvaHistElement.textContent = "Carregando...";
    chuvaFutElement.textContent = "Carregando...";
    nomeCidadeElement.textContent = nomeLocal;
    alertaPanel.style.backgroundColor = 'white';
    try {
        const response = await fetch(`/api/weather?lat=${latitude}&lon=${longitude}&nome_cidade=${encodeURIComponent(nomeLocal)}`);
        if (!response.ok) throw new Error('Falha na resposta da API');
        const dados = await response.json();
        const corAlerta = await determinarNivelAlerta(dados.chuva_72h_hist || 0, dados.chuva_72h_fut || 0);
        alertaTituloElement.textContent = `Nível: ${colorToRiskMap[corAlerta] || 'Indefinido'}`;
        alertaPanel.style.backgroundColor = corAlerta;
        alertaPanel.classList.toggle('color-dark', corAlerta === "#FFFF00" || corAlerta === "#FFFFFF");
        alertaPanel.classList.toggle('color-light', corAlerta !== "#FFFF00" && corAlerta !== "#FFFFFF");
        nomeCidadeElement.textContent = dados.cidade_nome || nomeLocal;
        tempElement.textContent = (dados.temperatura != null ? dados.temperatura.toFixed(1) : '--') + "°C";
        chuvaHistElement.textContent = (dados.chuva_72h_hist != null ? dados.chuva_72h_hist.toFixed(1) : '--') + " mm";
        chuvaFutElement.textContent = (dados.chuva_72h_fut != null ? dados.chuva_72h_fut.toFixed(1) : '--') + " mm";
    } catch (error) {
        alertaTituloElement.textContent = `ERRO DE DADOS`;
        alertaPanel.style.backgroundColor = 'white';
        alertaPanel.classList.add('color-dark');
        alertaPanel.classList.remove('color-light');
        nomeCidadeElement.textContent = "ERRO NA BUSCA";
        tempElement.textContent = "ERRO";
        chuvaHistElement.textContent = "ERRO";
        chuvaFutElement.textContent = "ERRO";
    }
}

async function fetchAndPlaceAllMarkers() {
    try {
        const response = await fetch('/api/todos_os_pontos');
        if (!response.ok) throw new Error('Falha ao buscar todos os pontos do mapa.');
        const todosOsPontos = await response.json();
        todosOsPontos.forEach(ponto => {
            if (ponto.lat === undefined || ponto.lon === undefined) return;
            L.marker([ponto.lat, ponto.lon]).addTo(map)
                .bindTooltip(`${ponto.nome} (${ponto.estado || ''})`.replace(' ()', ''))
                .on('click', () => {
                    // Salva a visualização do mapa ANTES de aplicar o zoom do clique
                    lastMapView = { center: map.getCenter(), zoom: map.getZoom() };
                    map.setView([ponto.lat, ponto.lon], 11);
                    processarNovoLocal(ponto.lat, ponto.lon, ponto.nome);
                });
        });
    } catch (error) {
        console.error("Erro ao carregar os marcadores no mapa:", error);
    }
}

function ajustarLayoutMobile() {
    const header = document.querySelector('.app-header');
    if (!header) return;
    const headerHeight = header.offsetHeight;
    const containers = document.querySelectorAll('#map-container, #dashboard-container, #monitor-room-container');
    containers.forEach(container => { container.style.top = `${headerHeight}px`; });
    if (map) { setTimeout(() => map.invalidateSize(), 100); }
}

window.addEventListener('DOMContentLoaded', ajustarLayoutMobile);
window.addEventListener('resize', ajustarLayoutMobile);

// INICIALIZAÇÃO
processarNovoLocal(INITIAL_LATITUDE, INITIAL_LONGITUDE, "Brasília");
fetchAndPlaceAllMarkers();

