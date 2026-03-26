(function () {
  'use strict';

  const root = window.SIOPControleBCChamados = window.SIOPControleBCChamados || {};

  function bindControleBCChamadosRows() {
    document.addEventListener('click', (event) => {
      const row = event.target.closest('.controlebc-record-row[data-view-url]');
      if (!row) return;

      const ignoreClick = event.target.closest('a, button, input, select, textarea, label');
      if (ignoreClick) return;

      const url = row.dataset.viewUrl;
      if (!url) return;
      window.location.href = url;
    });

    document.addEventListener('keydown', (event) => {
      const row = event.target.closest('.controlebc-record-row[data-view-url]');
      if (!row) return;
      if (event.key !== 'Enter' && event.key !== ' ') return;

      event.preventDefault();
      const url = row.dataset.viewUrl;
      if (!url) return;
      window.location.href = url;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      bindControleBCChamadosRows();
      const context = root.core?.buildContext?.();
      root.export?.init?.(context);
    }, { once: true });
  } else {
    bindControleBCChamadosRows();
    const context = root.core?.buildContext?.();
    root.export?.init?.(context);
  }
})();
