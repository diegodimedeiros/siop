(function () {
  'use strict';

  const root = window.SIOPControleBCChamados = window.SIOPControleBCChamados || {};
  const core = root.core = root.core || {};

  const $ = (selector, rootNode = document) => rootNode.querySelector(selector);

  function getRealPath() {
    const realPath = document.body?.dataset?.realPath || window.location.pathname || '';
    return (realPath.split('?')[0] || '').trim() || window.location.pathname || '/';
  }

  function buildContext() {
    const exportForm = $('#controlebc-export-form');
    const exportPage = exportForm?.dataset?.exportPage || '';

    return {
      realPath: getRealPath(),
      exportForm,
      exportPage,
      btnExportFiltrar: $('#btn-export-filtrar'),
      btnExportLimpar: $('#btn-export-limpar'),
      btnExportCsv: $('#btn-export-csv'),
      btnExportXlsx: $('#btn-export-xlsx'),
      btnExportPdf: $('#btn-export-pdf'),
    };
  }

  function buildExportQuery(form, format) {
    const params = new URLSearchParams();
    const formData = new FormData(form);

    formData.forEach((value, key) => {
      const normalized = String(value || '').trim();
      if (!normalized) return;
      params.set(key, normalized);
    });

    params.set('tab', 'export');
    if (format) {
      params.set('export', format);
    } else {
      params.delete('export');
    }

    return params;
  }

  function navigateWithExportParams(form, format) {
    const action = form.getAttribute('action') || getRealPath();
    const params = buildExportQuery(form, format);
    window.location.assign(`${action}?${params.toString()}`);
  }

  core.$ = $;
  core.getRealPath = getRealPath;
  core.buildContext = buildContext;
  core.buildExportQuery = buildExportQuery;
  core.navigateWithExportParams = navigateWithExportParams;
})();
