(function () {
  'use strict';

  const root = window.SIOPOcorrencias = window.SIOPOcorrencias || {};
  const exportModule = root.export = root.export || {};
  const shared = window.SIOPShared || {};
  const setLoading = shared.feedback?.setLoading;
  const runWithLoading = shared.feedback?.runWithLoading;
  const withLoadingFallback = shared.feedback?.withLoadingFallback;

  function getFilters(context) {
    const pessoaFilter = context.isAcessoTerceirosPage
      ? { p1: context.exportP1Select?.value || '' }
      : { pessoa: context.exportPessoaSelect?.value || '' };

    return {
      nome: context.exportNomeInput?.value || '',
      documento: context.exportDocumentoInput?.value || '',
      empresa: context.exportEmpresaInput?.value || '',
      placa_veiculo: context.exportPlacaVeiculoInput?.value || '',
      natureza: context.exportNaturezaSelect?.value || '',
      tipo: context.exportTipoSelect?.value || '',
      area: context.exportAreaSelect?.value || '',
      local: context.exportLocalSelect?.value || '',
      ...pessoaFilter,
      status: context.exportStatusSelect?.value || '',
      bombeiro_civil: context.exportBombeiroCivilSelect?.value || '',
      cftv: context.exportCftvSelect?.value || '',
      data_inicio: context.exportDataInicioInput?.value || '',
      data_fim: context.exportDataFimInput?.value || '',
      entrada_inicio: context.exportDataInicioInput?.value || '',
      entrada_fim: context.exportDataFimInput?.value || '',
      saida_inicio: context.exportSaidaInicioInput?.value || '',
      saida_fim: context.exportSaidaFimInput?.value || '',
    };
  }

  function hasAnyActiveFilter(filters) {
    return Object.values(filters).some((value) => String(value || '').trim() !== '');
  }

  function clearList(context) {
    if (!context.tabExportList) return;

    context.tabExportList.dataset.currentPage = '1';
    context.tabExportList.dataset.currentSort = '';
    context.tabExportList.dataset.currentDir = 'desc';
    context.tabExportList.innerHTML = `
      <section class="glass-card">
        <div class="card-header">
          <div>
            <div class="card-title">Listagem para exportação</div>
            <div class="card-subtitle">Aplique os filtros acima e clique em Filtrar para exibir os resultados.</div>
          </div>
        </div>
      </section>
    `;
    delete context.tabExportList.dataset.bound;
    root.searchList.bindExportListClick(context);
  }

  function trigger(context, format, triggerButton) {
    const filters = getFilters(context);
    if (!hasAnyActiveFilter(filters)) {
      root.feedback.showWarning?.('Aplique ao menos um filtro para exportar os registros.');
      setLoading?.(triggerButton, false);
      return;
    }

    const url = new URL(`${context.entityBasePath}/export/${format}/`, window.location.origin);
    Object.entries(filters).forEach(([key, value]) => {
      if (value) url.searchParams.set(key, value);
    });
    const releaseLoading = withLoadingFallback?.(triggerButton, 5000);
    try {
      window.location.assign(url.toString());
    } catch (error) {
      releaseLoading?.();
      root.feedback.showRequestError?.(error, 'Nao foi possivel iniciar a exportacao.');
    }
  }

  function init(context) {
    if (context.btnExportFiltrar) {
      context.btnExportFiltrar.addEventListener('click', async () => {
        await runWithLoading?.(context.btnExportFiltrar, async () => {
          await root.core.refreshExportList(context, 1);
        }, { label: 'Filtrando...' });
      });
    }

    if (context.btnExportLimpar) {
      context.btnExportLimpar.addEventListener('click', () => {
        if (context.exportNaturezaSelect) context.exportNaturezaSelect.value = '';
        if (context.exportAreaSelect) context.exportAreaSelect.value = '';
        if (context.exportNaturezaSelect) context.exportNaturezaSelect.dispatchEvent(new Event('change'));
        if (context.exportAreaSelect) context.exportAreaSelect.dispatchEvent(new Event('change'));
        if (context.exportP1Select) context.exportP1Select.value = '';
        if (context.exportPessoaSelect) context.exportPessoaSelect.value = '';
        if (context.exportNomeInput) context.exportNomeInput.value = '';
        if (context.exportDocumentoInput) context.exportDocumentoInput.value = '';
        if (context.exportEmpresaInput) context.exportEmpresaInput.value = '';
        if (context.exportPlacaVeiculoInput) context.exportPlacaVeiculoInput.value = '';
        if (context.exportStatusSelect) context.exportStatusSelect.value = '';
        if (context.exportBombeiroCivilSelect) context.exportBombeiroCivilSelect.value = '';
        if (context.exportCftvSelect) context.exportCftvSelect.value = '';
        if (context.exportDataInicioInput) context.exportDataInicioInput.value = '';
        if (context.exportDataFimInput) context.exportDataFimInput.value = '';
        if (context.exportSaidaInicioInput) context.exportSaidaInicioInput.value = '';
        if (context.exportSaidaFimInput) context.exportSaidaFimInput.value = '';
        clearList(context);
      });
    }

    if (context.btnExportCsv) {
      context.btnExportCsv.addEventListener('click', () => {
        setLoading?.(context.btnExportCsv, true, { label: 'Gerando CSV...' });
        trigger(context, 'csv', context.btnExportCsv);
      });
    }
    if (context.btnExportXlsx) {
      context.btnExportXlsx.addEventListener('click', () => {
        setLoading?.(context.btnExportXlsx, true, { label: 'Gerando XLSX...' });
        trigger(context, 'xlsx', context.btnExportXlsx);
      });
    }
    if (context.btnExportPdf) {
      context.btnExportPdf.addEventListener('click', () => {
        setLoading?.(context.btnExportPdf, true, { label: 'Gerando PDF...' });
        trigger(context, 'pdf', context.btnExportPdf);
      });
    }
    if (context.btnViewExportPdf && !context.isControleBCPage) {
      context.btnViewExportPdf.addEventListener('click', () => {
        const viewIdEl = root.core.$('#view-id');
        const id = viewIdEl?.value?.trim();
        if (!id) return;

        const url = context.isAcessoTerceirosPage
          ? new URL(`/acesso-terceiros/${id}/export/pdf-view/`, window.location.origin)
          : new URL(`/ocorrencias/${id}/export/pdf-view/`, window.location.origin);
        window.location.href = url.toString();
      });
    }
  }

  exportModule.getFilters = getFilters;
  exportModule.clearList = clearList;
  exportModule.trigger = trigger;
  exportModule.init = init;
})();
