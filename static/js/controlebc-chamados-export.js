(function () {
  'use strict';

  const root = window.SIOPControleBCChamados = window.SIOPControleBCChamados || {};
  const exportModule = root.export = root.export || {};
  const shared = window.SIOPShared || {};
  const setLoading = shared.feedback?.setLoading;
  const withLoadingFallback = shared.feedback?.withLoadingFallback;
  const showRequestError = shared.feedback?.showRequestError;

  function clear(context) {
    const clearUrl = context.btnExportLimpar?.dataset?.clearUrl;
    window.location.assign(clearUrl || `${context.realPath || root.core.getRealPath()}?tab=export`);
  }

  function trigger(context, format, triggerButton) {
    if (!context.exportForm) return;

    const releaseLoading = withLoadingFallback?.(triggerButton, 5000);
    try {
      root.core.navigateWithExportParams(context.exportForm, format);
    } catch (error) {
      releaseLoading?.();
      showRequestError?.(error, 'Nao foi possivel iniciar a exportacao.');
    }
  }

  function init(context) {
    if (!context.exportForm) return;

    if (context.btnExportFiltrar) {
      context.btnExportFiltrar.addEventListener('click', (event) => {
        event.preventDefault();
        trigger(context, '', context.btnExportFiltrar);
      });
    }

    if (context.btnExportLimpar) {
      context.btnExportLimpar.addEventListener('click', () => {
        clear(context);
      });
    }

    if (context.btnExportCsv) {
      context.btnExportCsv.addEventListener('click', (event) => {
        event.preventDefault();
        setLoading?.(context.btnExportCsv, true, { label: 'Gerando CSV...' });
        trigger(context, 'csv', context.btnExportCsv);
      });
    }

    if (context.btnExportXlsx) {
      context.btnExportXlsx.addEventListener('click', (event) => {
        event.preventDefault();
        setLoading?.(context.btnExportXlsx, true, { label: 'Gerando XLSX...' });
        trigger(context, 'xlsx', context.btnExportXlsx);
      });
    }

    if (context.btnExportPdf) {
      context.btnExportPdf.addEventListener('click', (event) => {
        event.preventDefault();
        setLoading?.(context.btnExportPdf, true, { label: 'Gerando PDF...' });
        trigger(context, 'pdf', context.btnExportPdf);
      });
    }
  }

  exportModule.clear = clear;
  exportModule.trigger = trigger;
  exportModule.init = init;
})();
