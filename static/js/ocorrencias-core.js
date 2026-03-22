(function () {
  'use strict';

  if (!window.SIOPShared) {
    throw new Error('Shared nao carregado');
  }

  const root = window.SIOPOcorrencias = window.SIOPOcorrencias || {};
  const core = root.core = root.core || {};
  const shared = window.SIOPShared;
  const fetchJSON = shared.http?.fetchJSON;
  const showError = shared.feedback?.showError;

  const $ = (sel, rootNode = document) => rootNode.querySelector(sel);

  function pad2(n) {
    return String(n).padStart(2, '0');
  }

  function toLocalISODateTime(now = new Date()) {
    return (
      now.getFullYear() +
      '-' + pad2(now.getMonth() + 1) +
      '-' + pad2(now.getDate()) +
      'T' + pad2(now.getHours()) +
      ':' + pad2(now.getMinutes())
    );
  }

  function setNewOcorrenciaDate(force) {
    ['#data', '#data_hora', '#data_atendimento'].forEach((selector) => {
      const input = $(selector);
      if (input && (force || !input.value)) {
        input.value = toLocalISODateTime();
      }
    });
  }

  function buildContext() {
    const realPath = document.body?.dataset?.realPath || window.location.pathname || '';
    const isControleBCPage = realPath.startsWith('/controlebc/');
    const isAcessoTerceirosPage = !!(
      $('#acesso-terceiros-form') ||
      $('#edit-acesso-terceiros-form') ||
      $('.acesso_terceiro-row')
    );
    const pageConfig = isAcessoTerceirosPage
      ? {
          entityBasePath: '/acesso-terceiros',
          rowSelector: '.acesso_terceiro-row',
          createFormSelector: '#acesso-terceiros-form',
          editFormSelector: '#edit-acesso-terceiros-form',
          entityLabel: 'acesso de terceiros',
        }
      : {
          entityBasePath: '/ocorrencias',
          rowSelector: '.ocorrencia-row',
          createFormSelector: '#ocorrencia-form',
          editFormSelector: '#edit-ocorrencia-form',
          entityLabel: 'ocorrência',
        };

    const createForm = $(pageConfig.createFormSelector);
    const editForm = $(pageConfig.editFormSelector);
    const tabList = $('#tab-list');
    const tabExportList = $('#tab-export-list');

    return {
      isControleBCPage,
      isAcessoTerceirosPage,
      entityBasePath: pageConfig.entityBasePath,
      rowSelector: pageConfig.rowSelector,
      createFormSelector: pageConfig.createFormSelector,
      editFormSelector: pageConfig.editFormSelector,
      entityLabel: pageConfig.entityLabel,
      searchBox: $('.records-search-box') || $('#ocorrencias-search-box') || $('#acessos-terceiros-search-box'),
      searchInput: $('.records-search-input') || $('#ocorrencias-search-input') || $('#acessos-terceiros-search-input'),
      searchDescricaoCheckbox: $('.records-search-descricao') || $('#ocorrencias-search-descricao') || $('#acessos-terceiros-search-descricao'),
      searchClearBtn: $('.records-search-clear') || $('#ocorrencias-search-clear') || $('#acessos-terceiros-search-clear'),
      exportNaturezaSelect: $('#export-natureza'),
      exportTipoSelect: $('#export-tipo'),
      exportAreaSelect: $('#export-area'),
      exportLocalSelect: $('#export-local'),
      exportP1Select: $('#export-p1'),
      exportPessoaSelect: $('#export-pessoa'),
      exportNomeInput: $('#export-nome'),
      exportDocumentoInput: $('#export-documento'),
      exportEmpresaInput: $('#export-empresa'),
      exportPlacaVeiculoInput: $('#export-placa-veiculo'),
      exportStatusSelect: $('#export-status'),
      exportBombeiroCivilSelect: $('#export-bombeiro-civil'),
      exportCftvSelect: $('#export-cftv'),
      exportDataInicioInput: $('#export-data-inicio') || $('#export-entrada-inicio'),
      exportDataFimInput: $('#export-data-fim') || $('#export-entrada-fim'),
      exportSaidaInicioInput: $('#export-saida-inicio'),
      exportSaidaFimInput: $('#export-saida-fim'),
      btnExportFiltrar: $('#btn-export-filtrar'),
      btnExportLimpar: $('#btn-export-limpar'),
      btnExportCsv: $('#btn-export-csv'),
      btnExportXlsx: $('#btn-export-xlsx'),
      btnExportPdf: $('#btn-export-pdf'),
      btnViewExportPdf: $('#btn-view-export-pdf'),
      btnViewEdit: $('#btn-view-edit'),
      btnSalvar: $('#btn-salvar'),
      btnSalvarEdit: $('#btn-salvar-edit'),
      createForm,
      editForm,
      tabList,
      tabExportList,
      tabsContainer: document.querySelector('.tabs-container'),
      modalSucesso: $('#modal-sucesso'),
      searchDebounceTimer: null,
      hasOcorrenciasDomain: !!(
        createForm ||
        editForm ||
        tabList ||
        tabExportList ||
        $('.ocorrencia-row') ||
        $('.acesso_terceiro-row')
      ),
    };
  }

  function getSearchScope(context) {
    return context.searchDescricaoCheckbox?.checked ? 'descricao' : 'default';
  }

  function syncSearchClearButton(context) {
    if (!context.searchClearBtn || !context.searchInput) return;
    const hasValue = !!(context.searchInput.value || '').trim();
    context.searchClearBtn.style.display = hasValue ? 'inline-flex' : 'none';
  }

  function syncSearchForTab(context, tabId) {
    if (!context.searchBox || !context.searchInput) return;

    const isListTab = tabId === 'tab-list';
    context.searchBox.style.display = isListTab ? '' : 'none';
    context.searchInput.disabled = !isListTab;
    if (context.searchDescricaoCheckbox) {
      context.searchDescricaoCheckbox.disabled = !isListTab;
    }
    if (!isListTab && context.searchDebounceTimer) {
      clearTimeout(context.searchDebounceTimer);
    }
  }

  function goToTab(context, tabId) {
    if (!context.tabsContainer) return;

    const tabButtons = context.tabsContainer.querySelectorAll('.tab-btn');
    const tabContents = context.tabsContainer.querySelectorAll('.tab-content');
    tabButtons.forEach((button) => button.classList.remove('active'));
    tabContents.forEach((content) => content.classList.remove('active'));

    const targetButton = context.tabsContainer.querySelector(`[data-tab="${tabId}"]`);
    const targetContent = context.tabsContainer.querySelector(`#${tabId}`);
    if (targetButton) targetButton.classList.add('active');
    if (targetContent) targetContent.classList.add('active');

    if (tabId === 'tab-new') {
      setNewOcorrenciaDate();
    }
    syncSearchForTab(context, tabId);
  }

  async function fetchEntityData(context, id, errorMessage) {
    try {
      return await fetchJSON(`${context.entityBasePath}/${id}/json/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      });
    } catch (err) {
      showError?.(err?.message || errorMessage || `Erro ao carregar ${context.entityLabel}.`);
      return null;
    }
  }

  async function refreshTabList(context, pageNumber = null, searchQuery = null, scopeValue = null, sortValue = null, dirValue = null) {
    if (!context.tabList) return;

    const url = new URL(`${context.entityBasePath}/list/partial/`, window.location.origin);
    const page = pageNumber || context.tabList.dataset.currentPage || '1';
    const query = (searchQuery !== null ? searchQuery : (context.tabList.dataset.currentQuery || '')).trim();
    const scope = scopeValue || context.tabList.dataset.currentScope || getSearchScope(context);
    const sort = sortValue !== null ? sortValue : (context.tabList.dataset.currentSort || '');
    const dir = dirValue !== null ? dirValue : (context.tabList.dataset.currentDir || 'desc');

    context.tabList.dataset.currentPage = page;
    context.tabList.dataset.currentQuery = query;
    context.tabList.dataset.currentScope = scope;
    context.tabList.dataset.currentSort = sort;
    context.tabList.dataset.currentDir = dir;

    url.searchParams.set('page', page);
    if (query) url.searchParams.set('q', query);
    if (scope) url.searchParams.set('scope', scope);
    if (sort) {
      url.searchParams.set('sort', sort);
      url.searchParams.set('dir', dir);
    }

    const response = await fetch(url.toString(), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (!response.ok) {
      console.error('Falha ao atualizar lista:', response.status);
      return;
    }

    context.tabList.innerHTML = await response.text();
    delete context.tabList.dataset.bound;
    root.searchList?.bindTabListClick?.(context);
  }

  async function refreshExportList(context, pageNumber = null, sortValue = null, dirValue = null) {
    if (!context.tabExportList) return;

    const url = new URL(`${context.entityBasePath}/list/partial/`, window.location.origin);
    const page = pageNumber || context.tabExportList.dataset.currentPage || '1';
    const sort = sortValue !== null ? sortValue : (context.tabExportList.dataset.currentSort || '');
    const dir = dirValue !== null ? dirValue : (context.tabExportList.dataset.currentDir || 'desc');

    context.tabExportList.dataset.currentPage = page;
    context.tabExportList.dataset.currentSort = sort;
    context.tabExportList.dataset.currentDir = dir;

    url.searchParams.set('page', page);
    if (sort) {
      url.searchParams.set('sort', sort);
      url.searchParams.set('dir', dir);
    }

    const filters = root.export?.getFilters?.(context) || {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
    });

    const response = await fetch(url.toString(), {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (!response.ok) {
      console.error('Falha ao atualizar lista de exportação:', response.status);
      return;
    }

    context.tabExportList.innerHTML = await response.text();
    delete context.tabExportList.dataset.bound;
    root.searchList?.bindExportListClick?.(context);
  }

  function init() {
    const context = buildContext();
    if (context.isControleBCPage || !context.hasOcorrenciasDomain) return;

    root.feedback?.init?.(context);
    root.searchList?.init?.(context);
    root.create?.init?.(context);
    root.viewEdit?.init?.(context);
    root.export?.init?.(context);
  }

  core.$ = $;
  core.setNewOcorrenciaDate = setNewOcorrenciaDate;
  core.buildContext = buildContext;
  core.getSearchScope = getSearchScope;
  core.syncSearchClearButton = syncSearchClearButton;
  core.syncSearchForTab = syncSearchForTab;
  core.goToTab = goToTab;
  core.fetchEntityData = fetchEntityData;
  core.refreshTabList = refreshTabList;
  core.refreshExportList = refreshExportList;
  core.init = init;
})();
