// Estado Global da Aplicação
let selectedState = "SP";
let selectedYear = 2026;
let searchFilter = "";
let gestaoFilter = "todos";
let currentCompareMode = "oficial"; // "oficial", "ativos", "total", "equiparado"
let activeTab = "orcamento"; // "orcamento", "salarios"

// Variaveis de Controle da Aba de Salários
let selectedSalaryCargo = "pm_soldado";
let salarySearchFilter = "";

// Instâncias de Gráficos (Chart.js)
let chartTrend = null;
let chartBreakdown = null;
let chartCompare = null;
let chartSalaryTrend = null;
let chartSalaryCompare = null;

let currentTheme = "dark";

// Helper para calcular valores ajustados com base no modelo previdenciário e modo selecionado
function calculateRowValues(row, mode) {
    const ssp_raw = row["SSP (R$ Mi)"];
    const sap_raw = row["SAP (R$ Mi)"];
    const total_est = row["Orçamento Total Estado (R$ Mi)"];
    const inativos = row["Inativos_Militares (R$ Mi)"] || 0;
    const modelo_prev = row["Modelo_Previdenciario"];
    
    let ssp_val = ssp_raw;
    let sap_val = sap_raw;
    
    if (mode === "ativos") {
        if (modelo_prev === "Integrado") {
            ssp_val = Math.max(0, ssp_raw - inativos);
        }
    } else if (mode === "total") {
        if (modelo_prev === "Separado") {
            ssp_val = ssp_raw + inativos;
        }
    } else if (mode === "equiparado") {
        if (modelo_prev === "Separado") {
            ssp_val = ssp_raw + inativos;
        }
        const detran = row["DETRAN_Proxy (R$ Mi)"] || 0;
        const casa_mil = row["Casa_Militar_Ajuste (R$ Mi)"] || 0;
        ssp_val = ssp_val + detran + casa_mil;
    }
    
    const comb_val = ssp_val + sap_val;
    const ssp_pct = total_est > 0 ? (ssp_val / total_est) * 100 : 0;
    const sap_pct = total_est > 0 ? (sap_val / total_est) * 100 : 0;
    const comb_pct = total_est > 0 ? (comb_val / total_est) * 100 : 0;
    
    return {
        ssp_val,
        sap_val,
        comb_val,
        ssp_pct,
        sap_pct,
        comb_pct,
        total_est,
        inativos,
        modelo_prev
    };
}

// NOVO: Cálculo da distribuição por órgão policial (Proxy Metodológico)
function calculatePoliceBreakdown(row, mode) {
    const values = calculateRowValues(row, mode);
    const isSeparada = row["Modelo de Gestão"] === "SAP Separada";
    
    let pm = 0;
    let pc = 0;
    let cientifica = 0;
    let penal = 0;
    
    if (isSeparada) {
        // SAP separada: Polícia Penal é exatamente o gasto da SAP
        penal = values.sap_val;
        
        // Desdobramento dos outros órgãos com base nas subfunções da SSP
        const pol = row["Sub_Policiamento (R$ Mi)"] || 0;
        const def = row["Sub_Defesa_Civil (R$ Mi)"] || 0;
        const adm = row["Sub_Admin_Geral (R$ Mi)"] || 0;
        const intel = row["Sub_Inteligencia (R$ Mi)"] || 0;
        const dem = row["Sub_Demais (R$ Mi)"] || 0;
        
        pm = 0.65 * pol + 0.90 * def + 0.50 * adm + 0.50 * intel + 0.40 * dem;
        pc = 0.30 * pol + 0.05 * def + 0.40 * adm + 0.40 * intel + 0.40 * dem;
        cientifica = 0.05 * pol + 0.05 * def + 0.10 * adm + 0.10 * intel + 0.20 * dem;
        
        // Adicionar inativos militares à PM se o modo adicionar inativos
        const inativos = row["Inativos_Militares (R$ Mi)"] || 0;
        if (mode === "total" || mode === "equiparado") {
            if (row["Modelo_Previdenciario"] === "Separado") {
                pm += inativos;
            }
        }
        // Subtrair inativos se o modo subtrair ativos
        if (mode === "ativos" && row["Modelo_Previdenciario"] === "Integrado") {
            pm = Math.max(0, pm - inativos);
        }
        
        // Adicionar DETRAN à Polícia Civil se equiparado
        const detran = row["DETRAN_Proxy (R$ Mi)"] || 0;
        if (mode === "equiparado" && detran > 0) {
            pc += detran;
        }
        
        // Adicionar Casa Militar à PM se equiparado
        const casa_mil = row["Casa_Militar_Ajuste (R$ Mi)"] || 0;
        if (mode === "equiparado" && casa_mil > 0) {
            pm += casa_mil;
        }
    } else {
        // SSP Integrada: Custódia é parte da SSP. Estimativa proporcional clássica.
        // Distribui o SSP total (já com eventuais ajustes de inativos, etc.)
        const ssp_total = values.ssp_val;
        
        penal = ssp_total * 0.18;
        const rest = ssp_total * 0.82;
        
        pm = rest * 0.68;
        pc = rest * 0.27;
        cientifica = rest * 0.05;
    }
    
    return {
        pm,
        pc,
        cientifica,
        penal,
        total: pm + pc + cientifica + penal
    };
}

// Utilitários de Formatação
function formatBR(val, isPercent = false, noDecimals = false) {
    if (val === null || val === undefined || isNaN(val)) return "-";
    if (val === 0 && !isPercent) return "-";
    
    const dec = noDecimals ? 0 : 2;
    let formatted = val.toLocaleString("pt-BR", {
        minimumFractionDigits: dec,
        maximumFractionDigits: dec
    });
    
    return isPercent ? `${formatted}%` : formatted;
}

// Inicialização do App
document.addEventListener("DOMContentLoaded", () => {
    // 1. Configurar Tema Inicial
    initTheme();

    // 2. Popular seletores
    populateSelectors();

    // 3. Adicionar Listeners de Eventos
    setupEventListeners();

    // 4. Renderizar tudo pela primeira vez
    updateDashboard();
});

// Configurar o Tema Claro/Escuro
function initTheme() {
    const themeToggle = document.getElementById("theme-toggle");
    const savedTheme = localStorage.getItem("theme") || "dark";
    
    currentTheme = savedTheme;
    document.documentElement.setAttribute("data-theme", savedTheme);
    themeToggle.checked = (savedTheme === "light");
}

function toggleTheme() {
    const themeToggle = document.getElementById("theme-toggle");
    currentTheme = themeToggle.checked ? "light" : "dark";
    
    document.documentElement.setAttribute("data-theme", currentTheme);
    localStorage.setItem("theme", currentTheme);
    
    // Atualizar os gráficos ativos
    updateCharts();
}

// Preencher os filtros Select com dados reais
function populateSelectors() {
    const selectState = document.getElementById("select-state");
    const selectYear = document.getElementById("select-year");
    const selectSalState = document.getElementById("select-salary-state");
    const selectSalYear = document.getElementById("select-salary-year");
    
    // Extrair UFs e Anos únicos
    const ufs = [...new Set(ORCAMENTOS_DATA.map(d => d["UF"]))].sort();
    const anos = [...new Set(ORCAMENTOS_DATA.map(d => d["Ano"]))].sort((a, b) => b - a); // Decrescente
    
    const ufsOptions = ufs.map(uf => `<option value="${uf}" ${uf === selectedState ? "selected" : ""}>${uf}</option>`).join("");
    const anosOptions = anos.map(ano => `<option value="${ano}" ${ano === selectedYear ? "selected" : ""}>${ano}</option>`).join("");
    
    selectState.innerHTML = ufsOptions;
    selectYear.innerHTML = anosOptions;
    selectSalState.innerHTML = ufsOptions;
    selectSalYear.innerHTML = anosOptions;
}

// Listeners de Interação
function setupEventListeners() {
    // Configurar Alternador de Abas Principais
    const btnTabOrcamento = document.getElementById("btn-tab-orcamento");
    const btnTabSalarios = document.getElementById("btn-tab-salarios");
    const contentOrcamento = document.getElementById("content-orcamento");
    const contentSalarios = document.getElementById("content-salarios");
    
    btnTabOrcamento.addEventListener("click", () => {
        btnTabOrcamento.classList.add("active");
        btnTabSalarios.classList.remove("active");
        contentOrcamento.classList.add("active");
        contentSalarios.classList.remove("active");
        activeTab = "orcamento";
        updateDashboard();
    });
    
    btnTabSalarios.addEventListener("click", () => {
        btnTabSalarios.classList.add("active");
        btnTabOrcamento.classList.remove("active");
        contentSalarios.classList.add("active");
        contentOrcamento.classList.remove("active");
        activeTab = "salarios";
        updateSalaryDashboard();
    });

    // Filtros da Aba 1 (Orçamento)
    document.getElementById("select-state").addEventListener("change", (e) => {
        selectedState = e.target.value;
        document.getElementById("select-salary-state").value = selectedState; // Sincroniza com a outra aba
        updateDashboard();
    });
    
    document.getElementById("select-year").addEventListener("change", (e) => {
        selectedYear = parseInt(e.target.value);
        document.getElementById("select-salary-year").value = selectedYear; // Sincroniza com a outra aba
        updateDashboard();
    });
    
    document.getElementById("select-gestao").addEventListener("change", (e) => {
        gestaoFilter = e.target.value;
        renderTable();
    });
    
    document.getElementById("input-search").addEventListener("input", (e) => {
        searchFilter = e.target.value.toUpperCase();
        renderTable();
    });
    
    // Filtros da Aba 2 (Salários)
    document.getElementById("select-salary-state").addEventListener("change", (e) => {
        selectedState = e.target.value;
        document.getElementById("select-state").value = selectedState; // Sincroniza com a outra aba
        updateSalaryDashboard();
    });
    
    document.getElementById("select-salary-year").addEventListener("change", (e) => {
        selectedYear = parseInt(e.target.value);
        document.getElementById("select-year").value = selectedYear; // Sincroniza com a outra aba
        updateSalaryDashboard();
    });
    
    document.getElementById("select-salary-cargo").addEventListener("change", (e) => {
        selectedSalaryCargo = e.target.value;
        updateSalaryDashboard();
    });
    
    document.getElementById("input-salary-search").addEventListener("input", (e) => {
        salarySearchFilter = e.target.value.toUpperCase();
        renderSalaryNationalTable();
    });

    document.getElementById("theme-toggle").addEventListener("change", toggleTheme);
    
    // Listeners para os botões de ajuste previdenciário
    const modeTabs = document.getElementById("mode-tabs");
    if (modeTabs) {
        const buttons = modeTabs.querySelectorAll(".tab-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", () => {
                buttons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                currentCompareMode = btn.getAttribute("data-mode");
                updateDashboard();
            });
        });
    }
}

// ==========================================
// ABA 1: LOGICA DO PAINEL ORÇAMENTÁRIO
// ==========================================

// Atualização Geral do Painel Orçamentário
function updateDashboard() {
    renderMetrics();
    renderTable();
    updateCharts();
}

// Renderizar Painel de Métricas Rápidas
function renderMetrics() {
    const record = ORCAMENTOS_DATA.find(d => d["UF"] === selectedState && d["Ano"] === selectedYear);
    
    if (!record) {
        document.getElementById("metric-ssp-val").innerText = "-";
        document.getElementById("metric-sap-val").innerText = "-";
        document.getElementById("metric-comb-val").innerText = "-";
        document.getElementById("metric-desc").innerHTML = "Dados não localizados para esta seleção.";
        return;
    }
    
    const isSeparada = record["Modelo de Gestão"] === "SAP Separada";
    const values = calculateRowValues(record, currentCompareMode);
    
    document.getElementById("metric-ssp-val").innerText = formatBR(values.ssp_pct, true);
    document.getElementById("metric-sap-val").innerText = isSeparada ? formatBR(values.sap_pct, true) : "Integrado";
    document.getElementById("metric-comb-val").innerText = formatBR(values.comb_pct, true);
    
    let desc = "";
    
    // Texto descritivo do modo
    let modeText = "";
    if (currentCompareMode === "oficial") {
        modeText = " (Modo Oficial SICONFI)";
    } else if (currentCompareMode === "ativos") {
        modeText = " (Modo Apenas Ativos/Operacional)";
    } else if (currentCompareMode === "total") {
        modeText = " (Modo Total: Ativos + Inativos)";
    } else if (currentCompareMode === "equiparado") {
        modeText = " (Modo Equiparado: Denominador Comum)";
    }
    
    if (isSeparada) {
        desc = `Em <strong>${selectedYear}</strong>, o estado do <strong>${selectedState}</strong> teve gestão descentralizada. 
                Investiu <strong>R$ ${formatBR(values.ssp_val)} Mi</strong> na Segurança (SSP) e 
                <strong>R$ ${formatBR(values.sap_val)} Mi</strong> na Custódia (SAP), totalizando <strong>R$ ${formatBR(values.comb_val)} Mi</strong>${modeText}.`;
    } else {
        desc = `Em <strong>${selectedYear}</strong>, o estado do <strong>${selectedState}</strong> teve gestão unificada. 
                Os recursos penitenciários estão contidos na própria pasta de Segurança (SSP), totalizando 
                <strong>R$ ${formatBR(values.ssp_val)} Mi</strong>${modeText}.`;
    }
    
    // Detalhar impacto previdenciário e de equiparação
    if (currentCompareMode === "equiparado") {
        const detranVal = record["DETRAN_Proxy (R$ Mi)"] || 0;
        const casaMilitarVal = record["Casa_Militar_Ajuste (R$ Mi)"] || 0;
        let adjustments = [];
        
        if (values.modelo_prev === "Separado") {
            adjustments.push(`Inativos Militares (+R$ ${formatBR(values.inativos)} Mi)`);
        } else {
            adjustments.push(`Inativos Militares (já integrados no orçamento da SSP)`);
        }
        
        if (detranVal > 0) {
            adjustments.push(`DETRAN (+R$ ${formatBR(detranVal)} Mi)`);
        } else {
            adjustments.push(`DETRAN (já integrado na Polícia Civil/SSP)`);
        }
        
        if (casaMilitarVal > 0) {
            adjustments.push(`Casa Militar/Defesa Civil (+R$ ${formatBR(casaMilitarVal)} Mi)`);
        }
        
        desc += `<br><span style="font-size: 0.9rem; color: var(--text-muted); display: block; margin-top: 0.5rem;">
                 * <strong>Composição da Equiparação:</strong> ${adjustments.join(", ")}.
                 </span>`;
    } else if (values.inativos > 0) {
        if (values.modelo_prev === "Integrado") {
            desc += `<br><span style="font-size: 0.9rem; color: var(--text-muted); display: block; margin-top: 0.5rem;">
                     * Este estado possui contabilidade <strong>integrada</strong>. 
                     Gastos com inativos/pensionistas militares estimados em <strong>R$ ${formatBR(values.inativos)} Mi</strong>. 
                     ${currentCompareMode === "ativos" ? "<strong>Estes inativos foram deduzidos</strong> do valor de Segurança." : "Estes inativos <strong>estão incluídos</strong> no valor de Segurança."}
                     </span>`;
        } else {
            desc += `<br><span style="font-size: 0.9rem; color: var(--text-muted); display: block; margin-top: 0.5rem;">
                     * Este estado possui contabilidade <strong>separada</strong> (previdência sob a Função 09). 
                     Gastos com inativos/pensionistas militares extraídos do RREO Anexo 04 somam <strong>R$ ${formatBR(values.inativos)} Mi</strong>. 
                     ${currentCompareMode === "total" ? "<strong>Estes inativos foram adicionados</strong> ao valor de Segurança." : "Estes inativos <strong>não estão incluídos</strong> no valor de Segurança."}
                     </span>`;
        }
    }
    
    document.getElementById("metric-desc").innerHTML = desc;
}

// Renderizar Tabela Interativa
function renderTable() {
    const tableBody = document.getElementById("table-body");
    tableBody.innerHTML = "";
    
    // Filtrar dados para o ano selecionado
    let dataForYear = ORCAMENTOS_DATA.filter(d => d["Ano"] === selectedYear);
    
    // Filtro de Busca
    if (searchFilter) {
        dataForYear = dataForYear.filter(d => d["UF"].includes(searchFilter));
    }
    
    // Filtro de Gestão
    if (gestaoFilter !== "todos") {
        dataForYear = dataForYear.filter(d => {
            const isSeparada = d["Modelo de Gestão"] === "SAP Separada";
            return gestaoFilter === "separada" ? isSeparada : !isSeparada;
        });
    }
    
    // Ordenar por UF alfabeticamente
    dataForYear.sort((a, b) => a["UF"].localeCompare(b["UF"]));
    
    if (dataForYear.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="9" class="cell-center cell-muted">Nenhum estado corresponde aos filtros aplicados.</td></tr>`;
        return;
    }
    
    dataForYear.forEach(row => {
        const tr = document.createElement("tr");
        if (row["UF"] === selectedState) {
            tr.className = "highlighted";
        }
        
        const isSeparada = row["Modelo de Gestão"] === "SAP Separada";
        const badgeClass = isSeparada ? "sap-separada" : "ssp-integrada";
        const labelGestao = isSeparada ? "SAP Separada" : "SSP Integrada";
        
        // Calcular valores dinamicamente com base no modo selecionado
        const vals = calculateRowValues(row, currentCompareMode);
        
        tr.innerHTML = `
            <td class="cell-bold">${row["UF"]}</td>
            <td><span class="badge ${badgeClass}">${labelGestao}</span></td>
            <td class="cell-right">${formatBR(vals.ssp_val)}</td>
            <td class="cell-right ${!isSeparada ? 'cell-muted' : ''}">${isSeparada ? formatBR(vals.sap_val) : "-"}</td>
            <td class="cell-right cell-bold">${formatBR(vals.comb_val)}</td>
            <td class="cell-right cell-muted">${formatBR(vals.total_est)}</td>
            <td class="cell-right">${formatBR(vals.ssp_pct, true)}</td>
            <td class="cell-right ${!isSeparada ? 'cell-muted' : ''}">${isSeparada ? formatBR(vals.sap_pct, true) : "-"}</td>
            <td class="cell-right cell-bold">${formatBR(vals.comb_pct, true)}</td>
        `;
        
        // Clicar na linha muda o estado selecionado
        tr.addEventListener("click", () => {
            selectedState = row["UF"];
            document.getElementById("select-state").value = selectedState;
            document.getElementById("select-salary-state").value = selectedState;
            updateDashboard();
        });
        
        tableBody.appendChild(tr);
    });
}

// Configurações Globais de Tema dos Gráficos
function getChartColors() {
    const isLight = currentTheme === "light";
    return {
        text: isLight ? "#1e293b" : "#f8fafc",
        grid: isLight ? "#cbd5e1" : "rgba(255, 255, 255, 0.08)",
        cardBg: isLight ? "#ffffff" : "#1e293b",
        tooltipBg: isLight ? "rgba(15, 23, 42, 0.9)" : "rgba(255, 255, 255, 0.95)",
        tooltipText: isLight ? "#ffffff" : "#0f172a"
    };
}

// Atualizar Gráficos Chart.js
function updateCharts() {
    const colors = getChartColors();
    
    // Configurar fontes globais do Chart.js
    Chart.defaults.color = colors.text;
    Chart.defaults.font.family = "'Inter', sans-serif";
    
    if (activeTab === "orcamento") {
        renderTrendChart(colors);
        renderBreakdownChart(colors);
        renderCompareChart(colors);
    } else {
        updateSalaryCharts();
    }
}

// Gráfico 1: Linha de Tendência Histórica do Estado Selecionado
function renderTrendChart(colors) {
    const ctx = document.getElementById("chart-trend").getContext("2d");
    
    // Obter histórico do estado ordenado por ano
    const stateHistory = ORCAMENTOS_DATA.filter(d => d["UF"] === selectedState).sort((a, b) => a["Ano"] - b["Ano"]);
    const labels = stateHistory.map(d => d["Ano"]);
    
    // Calcular os valores ajustados historicamente
    const adjustedHistory = stateHistory.map(d => calculateRowValues(d, currentCompareMode));
    
    const sspData = adjustedHistory.map(d => d.ssp_pct);
    const sapData = adjustedHistory.map(d => d.sap_pct);
    const combData = adjustedHistory.map(d => d.comb_pct);
    
    if (chartTrend) {
        chartTrend.destroy();
    }
    
    document.getElementById("trend-chart-title").innerText = `Evolução do Orçamento (%) - ${selectedState}`;
    
    chartTrend = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "SSP (%)",
                    data: sspData,
                    borderColor: "#3b82f6",
                    backgroundColor: "rgba(59, 130, 246, 0.1)",
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: "#3b82f6",
                    tension: 0.15
                },
                {
                    label: "SAP (%)",
                    data: sapData,
                    borderColor: "#10b981",
                    backgroundColor: "rgba(16, 185, 129, 0.1)",
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: "#10b981",
                    tension: 0.15,
                    // Ocultar linha se for estado puramente integrado para não poluir
                    hidden: stateHistory.every(d => d["SAP (%)"] === 0)
                },
                {
                    label: "Total SSP+SAP (%)",
                    data: combData,
                    borderColor: "#8b5cf6",
                    backgroundColor: "rgba(139, 92, 246, 0.15)",
                    borderWidth: 4,
                    pointRadius: 5,
                    pointBackgroundColor: "#8b5cf6",
                    tension: 0.15,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        boxWidth: 20,
                        font: { size: 12, weight: 500 }
                    }
                },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: "rgba(0, 0, 0, 0.1)",
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.dataset.label}: ${formatBR(context.parsed.y, true)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: colors.grid },
                    ticks: {
                        callback: function(value) { return value + "%"; },
                        font: { size: 11 }
                    },
                    title: {
                        display: true,
                        text: "% do Orçamento Estadual",
                        font: { size: 12, weight: 600 }
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

// NOVO Gráfico 2: Distribuição por Órgão Policial (Doughnut Chart)
function renderBreakdownChart(colors) {
    const canvas = document.getElementById("chart-breakdown");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const record = ORCAMENTOS_DATA.find(d => d["UF"] === selectedState && d["Ano"] === selectedYear);
    
    if (chartBreakdown) {
        chartBreakdown.destroy();
    }
    
    if (!record) {
        return;
    }
    
    const breakdown = calculatePoliceBreakdown(record, currentCompareMode);
    const total = breakdown.total;
    
    const data = [breakdown.pm, breakdown.pc, breakdown.cientifica, breakdown.penal];
    const labels = ["Polícia Militar + BM", "Polícia Civil", "Polícia Científica", "Polícia Penal"];
    
    // Esquema de cores premium: PM (azul), PC (vermelho/rosa), Científica (amber), Penal (verde)
    const bgColors = ["#3b82f6", "#f43f5e", "#fbbf24", "#10b981"];
    const hoverBgColors = ["#2563eb", "#e11d48", "#d97706", "#059669"];
    
    document.getElementById("breakdown-chart-title").innerText = `Gastos por Corporação - ${selectedState} (${selectedYear})`;
    
    chartBreakdown = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [
                {
                    data: data,
                    backgroundColor: bgColors,
                    hoverBackgroundColor: hoverBgColors,
                    borderWidth: currentTheme === "light" ? 1.5 : 2,
                    borderColor: colors.cardBg
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        boxWidth: 10,
                        padding: 10,
                        font: { size: 10, weight: 600 }
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: "rgba(0, 0, 0, 0.1)",
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const val = context.parsed;
                            const pct = total > 0 ? (val / total) * 100 : 0;
                            return ` ${context.label}: R$ ${formatBR(val)} Mi (${formatBR(pct, true)})`;
                        }
                    }
                }
            },
            cutout: "60%"
        }
    });
}

// Gráfico 3: Comparação de Barras de Todos os Estados (Ano Selecionado)
function renderCompareChart(colors) {
    const ctx = document.getElementById("chart-compare").getContext("2d");
    
    // Obter dados de todos os estados no ano selecionado
    const yearData = ORCAMENTOS_DATA.filter(d => d["Ano"] === selectedYear);
    
    // Calcular os valores ajustados para cada estado
    const adjustedYearData = yearData.map(d => {
        const vals = calculateRowValues(d, currentCompareMode);
        return {
            UF: d["UF"],
            SSP_SAP_pct: vals.comb_pct,
            SSP_SAP_val: vals.comb_val
        };
    });
    
    // Ordenar de forma decrescente pela porcentagem de orçamento total
    adjustedYearData.sort((a, b) => b.SSP_SAP_pct - a.SSP_SAP_pct);
    
    const labels = adjustedYearData.map(d => d.UF);
    const values = adjustedYearData.map(d => d.SSP_SAP_pct);
    
    // Criar array de cores para as barras - Destacar o estado selecionado
    const borderColors = adjustedYearData.map(d => d.UF === selectedState ? "#ffffff" : "transparent");
    const backgroundColors = adjustedYearData.map(d => d.UF === selectedState ? "#8b5cf6" : "rgba(139, 92, 246, 0.5)");
    
    if (chartCompare) {
        chartCompare.destroy();
    }
    
    document.getElementById("compare-chart-title").innerText = `Comparação de Orçamento Combinado (%) - Todos os Estados (${selectedYear})`;
    
    chartCompare = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Investimento SSP + SAP (%)",
                    data: values,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: adjustedYearData.map(d => d.UF === selectedState ? 2 : 0),
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    callbacks: {
                        label: function(context) {
                            const row = adjustedYearData[context.dataIndex];
                            return ` Total: ${formatBR(context.parsed.y, true)} (R$ ${formatBR(row.SSP_SAP_val)} Mi)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: colors.grid },
                    ticks: {
                        callback: function(value) { return value + "%"; }
                    },
                    title: {
                        display: true,
                        text: "% do Orçamento Estadual",
                        font: { size: 12, weight: 600 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 10, weight: 600 }
                    }
                }
            }
        }
    });
}

// ==========================================
// ABA 2: LOGICA DOS SALÁRIOS HISTÓRICOS
// ==========================================

function updateSalaryDashboard() {
    renderSalaryMetrics();
    renderSalaryTable();
    renderSalaryNationalTable();
    updateSalaryCharts();
}

function renderSalaryMetrics() {
    const yearData = SALARIOS_DATA.filter(d => d["Ano"] === selectedYear);
    const activeRecord = yearData.find(d => d["UF"] === selectedState);
    
    if (!activeRecord) {
        document.getElementById("salary-metric-val").innerText = "-";
        document.getElementById("salary-metric-rank").innerText = "-";
        document.getElementById("salary-metric-avg").innerText = "-";
        document.getElementById("salary-desc").innerText = "Dados salariais não localizados para esta seleção.";
        return;
    }
    
    const salaryVal = activeRecord[selectedSalaryCargo];
    
    // Média Nacional
    const sum = yearData.reduce((acc, curr) => acc + (curr[selectedSalaryCargo] || 0), 0);
    const avg = sum / yearData.length;
    
    // Posição no Ranking Nacional (Decrescente)
    const sorted = [...yearData].sort((a, b) => b[selectedSalaryCargo] - a[selectedSalaryCargo]);
    const rankIndex = sorted.findIndex(d => d["UF"] === selectedState);
    const rank = rankIndex + 1;
    
    // Evolução 10 anos
    const stateHistory = SALARIOS_DATA.filter(d => d["UF"] === selectedState).sort((a, b) => a["Ano"] - b["Ano"]);
    let growthText = "";
    if (stateHistory.length >= 2) {
        const val2015 = stateHistory.find(d => d["Ano"] === 2015)?.[selectedSalaryCargo] || 0;
        const latestRecord = stateHistory[stateHistory.length - 1];
        const latestYear = latestRecord ? latestRecord["Ano"] : 2026;
        const valLatest = latestRecord ? (latestRecord[selectedSalaryCargo] || 0) : 0;
        if (val2015 > 0 && valLatest > 0) {
            const growth = ((valLatest - val2015) / val2015) * 100;
            const diffYears = latestYear - 2015;
            growthText = `Com um crescimento nominal acumulado de <strong>${formatBR(growth)}%</strong> nos últimos ${diffYears} anos (subindo de <strong>R$ ${formatBR(val2015, false, true)}</strong> em 2015 para <strong>R$ ${formatBR(valLatest, false, true)}</strong> em ${latestYear}).`;
        }
    }
    
    // Alimentar métricas rápidas
    document.getElementById("salary-metric-val").innerText = `R$ ${formatBR(salaryVal, false, true)}`;
    document.getElementById("salary-metric-rank").innerText = `${rank}º / 27`;
    document.getElementById("salary-metric-avg").innerText = `R$ ${formatBR(Math.round(avg), false, true)}`;
    
    const cargoNames = {
        pm_soldado: "Soldado PM",
        pm_sargento: "Sargento PM",
        pm_coronel: "Coronel PM",
        pc_agente: "Investigador / Agente PC",
        pc_escrivao: "Escrivão PC",
        pc_delegado: "Delegado PC",
        perito: "Perito Criminal",
        penal: "Policial Penal"
    };
    
    const diffPct = ((salaryVal - avg) / avg) * 100;
    const diffText = diffPct >= 0 
        ? `está <strong>${formatBR(diffPct)}% acima</strong> da média brasileira`
        : `está <strong>${formatBR(Math.abs(diffPct))}% abaixo</strong> da média brasileira`;
        
    let desc = `Em <strong>${selectedYear}</strong>, a remuneração bruta média mensal para o cargo de <strong>${cargoNames[selectedSalaryCargo]}</strong> no estado de <strong>${selectedState}</strong> foi de <strong>R$ ${formatBR(salaryVal, false, true)}</strong>. 
                Este montante ${diffText} (que é de R$ ${formatBR(Math.round(avg), false, true)}). 
                O estado está na <strong>${rank}ª posição</strong> do ranking da Federação para este cargo. ${growthText}`;
                
    document.getElementById("salary-desc").innerHTML = desc;
}

// Tabela 1: Histórico de Salários por Cargo no Estado
function renderSalaryTable() {
    const tableBody = document.getElementById("salary-table-body");
    tableBody.innerHTML = "";
    
    const stateData = SALARIOS_DATA.filter(d => d["UF"] === selectedState).sort((a, b) => b["Ano"] - a["Ano"]);
    
    if (stateData.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="9" class="cell-center cell-muted">Nenhum dado salarial localizado para esta seleção.</td></tr>`;
        return;
    }
    
    document.getElementById("salary-table-title").innerText = `Histórico Salarial do Estado - ${selectedState}`;
    
    stateData.forEach(row => {
        const tr = document.createElement("tr");
        if (row["Ano"] === selectedYear) {
            tr.className = "highlighted";
        }
        
        tr.innerHTML = `
            <td class="cell-bold">${row["Ano"]}</td>
            <td class="cell-right">R$ ${formatBR(row["pm_soldado"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["pm_sargento"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["pm_coronel"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["pc_agente"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["pc_escrivao"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["pc_delegado"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["perito"], false, true)}</td>
            <td class="cell-right">R$ ${formatBR(row["penal"], false, true)}</td>
        `;
        
        tr.addEventListener("click", () => {
            selectedYear = row["Ano"];
            document.getElementById("select-year").value = selectedYear;
            document.getElementById("select-salary-year").value = selectedYear;
            updateDashboard();
            updateSalaryDashboard();
        });
        
        tableBody.appendChild(tr);
    });
}

// Tabela 2: Ranking Nacional de Salários para o Cargo Selecionado
function renderSalaryNationalTable() {
    const tableBody = document.getElementById("salary-national-table-body");
    tableBody.innerHTML = "";
    
    let yearData = SALARIOS_DATA.filter(d => d["Ano"] === selectedYear);
    
    // Ordenar por salário decrescente
    yearData.sort((a, b) => b[selectedSalaryCargo] - a[selectedSalaryCargo]);
    
    const leaderSalary = yearData[0]?.[selectedSalaryCargo] || 1;
    const sum = yearData.reduce((acc, curr) => acc + (curr[selectedSalaryCargo] || 0), 0);
    const avg = sum / yearData.length;
    
    let displayData = yearData.map((d, index) => ({
        rank: index + 1,
        UF: d.UF,
        salary: d[selectedSalaryCargo]
    }));
    
    if (salarySearchFilter) {
        displayData = displayData.filter(d => d.UF.includes(salarySearchFilter));
    }
    
    const cargoNames = {
        pm_soldado: "Soldado da Polícia Militar",
        pm_sargento: "Sargento da Polícia Militar",
        pm_coronel: "Coronel da Polícia Militar",
        pc_agente: "Investigador / Agente da Polícia Civil",
        pc_escrivao: "Escrivão da Polícia Civil",
        pc_delegado: "Delegado da Polícia Civil",
        perito: "Perito Criminal da Polícia Científica",
        penal: "Policial Penal"
    };
    
    document.getElementById("salary-national-table-title").innerText = `Ranking Nacional de Salários - ${cargoNames[selectedSalaryCargo]} (${selectedYear})`;
    
    if (displayData.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="5" class="cell-center cell-muted">Nenhum estado corresponde aos filtros aplicados.</td></tr>`;
        return;
    }
    
    displayData.forEach(row => {
        const tr = document.createElement("tr");
        if (row.UF === selectedState) {
            tr.className = "highlighted";
        }
        
        const diffAvg = ((row.salary - avg) / avg) * 100;
        const diffLeader = ((row.salary - leaderSalary) / leaderSalary) * 100;
        
        const diffAvgText = diffAvg >= 0 
            ? `<span style="color: #10b981; font-weight: 600;">+${formatBR(diffAvg)}%</span>`
            : `<span style="color: #f43f5e; font-weight: 600;">${formatBR(diffAvg)}%</span>`;
            
        const diffLeaderText = row.rank === 1
            ? `<span style="color: #10b981; font-weight: 600;">Líder</span>`
            : `<span style="color: #f43f5e; font-weight: 500;">${formatBR(diffLeader)}%</span>`;
            
        tr.innerHTML = `
            <td class="cell-bold">${row.rank}º</td>
            <td class="cell-bold">${row.UF}</td>
            <td class="cell-right">R$ ${formatBR(row.salary, false, true)}</td>
            <td class="cell-right">${diffAvgText}</td>
            <td class="cell-right">${diffLeaderText}</td>
        `;
        
        tr.addEventListener("click", () => {
            selectedState = row.UF;
            document.getElementById("select-state").value = selectedState;
            document.getElementById("select-salary-state").value = selectedState;
            updateDashboard();
            updateSalaryDashboard();
        });
        
        tableBody.appendChild(tr);
    });
}

// Atualizar Gráficos da Aba 2 (Salários)
function updateSalaryCharts() {
    const colors = getChartColors();
    renderSalaryTrendChart(colors);
    renderSalaryCompareChart(colors);
}

// Gráfico de Tendência Temporal dos Salários (Estado em foco vs Média Nacional)
function renderSalaryTrendChart(colors) {
    const ctx = document.getElementById("chart-salary-trend").getContext("2d");
    
    // Histórico do estado selecionado
    const stateHistory = SALARIOS_DATA.filter(d => d["UF"] === selectedState).sort((a, b) => a["Ano"] - b["Ano"]);
    const labels = stateHistory.map(d => d["Ano"]);
    const stateSalaries = stateHistory.map(d => d[selectedSalaryCargo]);
    
    // Histórico da média nacional para o cargo correspondente
    const avgSalaries = [];
    for (let ano = 2015; ano <= 2024; ano++) {
        const yearData = SALARIOS_DATA.filter(d => d["Ano"] === ano);
        const sum = yearData.reduce((acc, curr) => acc + (curr[selectedSalaryCargo] || 0), 0);
        avgSalaries.push(Math.round(sum / yearData.length));
    }
    
    if (chartSalaryTrend) {
        chartSalaryTrend.destroy();
    }
    
    const cargoNames = {
        pm_soldado: "Soldado PM",
        pm_sargento: "Sargento PM",
        pm_coronel: "Coronel PM",
        pc_agente: "Investigador PC",
        pc_escrivao: "Escrivão PC",
        pc_delegado: "Delegado PC",
        perito: "Perito Criminal",
        penal: "Policial Penal"
    };
    
    document.getElementById("salary-trend-title").innerText = `Evolução Histórica do Salário - ${cargoNames[selectedSalaryCargo]} (${selectedState})`;
    
    chartSalaryTrend = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: `${selectedState} (R$)`,
                    data: stateSalaries,
                    borderColor: "#8b5cf6",
                    backgroundColor: "rgba(139, 92, 246, 0.1)",
                    borderWidth: 3.5,
                    pointRadius: 4,
                    pointBackgroundColor: "#8b5cf6",
                    tension: 0.1,
                    fill: true
                },
                {
                    label: "Média Nacional (R$)",
                    data: avgSalaries,
                    borderColor: colors.text === "#f8fafc" ? "rgba(255, 255, 255, 0.35)" : "rgba(15, 23, 42, 0.35)",
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: { font: { size: 11, weight: 500 } }
                },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    borderColor: "rgba(0, 0, 0, 0.1)",
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            return ` ${context.dataset.label.split(" (")[0]}: R$ ${formatBR(context.parsed.y, false, true)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: colors.grid },
                    ticks: {
                        callback: function(value) { return "R$ " + formatBR(value, false, true); },
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

// Gráfico de Barras de Salários por Estado (Highlight no selecionado)
function renderSalaryCompareChart(colors) {
    const ctx = document.getElementById("chart-salary-compare").getContext("2d");
    
    const yearData = SALARIOS_DATA.filter(d => d["Ano"] === selectedYear);
    
    // Ordenar de forma decrescente
    yearData.sort((a, b) => b[selectedSalaryCargo] - a[selectedSalaryCargo]);
    
    const labels = yearData.map(d => d.UF);
    const values = yearData.map(d => d[selectedSalaryCargo]);
    
    // Destacar o estado ativo
    const borderColors = yearData.map(d => d.UF === selectedState ? "#ffffff" : "transparent");
    const backgroundColors = yearData.map(d => d.UF === selectedState ? "#8b5cf6" : "rgba(139, 92, 246, 0.45)");
    
    if (chartSalaryCompare) {
        chartSalaryCompare.destroy();
    }
    
    const cargoNames = {
        pm_soldado: "Soldado PM",
        pm_sargento: "Sargento PM",
        pm_coronel: "Coronel PM",
        pc_agente: "Investigador PC",
        pc_escrivao: "Escrivão PC",
        pc_delegado: "Delegado PC",
        perito: "Perito Criminal",
        penal: "Policial Penal"
    };
    
    document.getElementById("salary-compare-title").innerText = `Comparativo Nacional de Salários - ${cargoNames[selectedSalaryCargo]} (${selectedYear})`;
    
    chartSalaryCompare = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: yearData.map(d => d.UF === selectedState ? 2 : 0),
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.tooltipText,
                    bodyColor: colors.tooltipText,
                    callbacks: {
                        label: function(context) {
                            return ` Salário: R$ ${formatBR(context.parsed.y, false, true)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: colors.grid },
                    ticks: {
                        callback: function(value) { return "R$ " + formatBR(value, false, true); },
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 9, weight: 600 } }
                }
            }
        }
    });
}
