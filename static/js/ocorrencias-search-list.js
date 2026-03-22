(function () {
  'use strict';

  const root = window.SIOPOcorrencias = window.SIOPOcorrencias || {};
  const searchList = root.searchList = root.searchList || {};

  async function handleRowClick(context, row) {
    const id = row?.dataset?.id;
    if (!id) return;

    const data = await root.core.fetchEntityData(context, id, `Erro ao carregar ${context.entityLabel}.`);
    if (!data) return;

    root.viewEdit?.fillView?.(context, data);
    root.core.goToTab(context, 'tab-view');
  }

  function bindTabListClick(context) {
    if (!context.tabList || context.tabList.dataset.bound === '1') return;

    context.tabList.dataset.bound = '1';
    context.tabList.addEventListener('click', async (event) => {
      const paginationLink = event.target.closest('.pagination a, .pagination-btn[href]');
      if (paginationLink) {
        event.preventDefault();
        const href = paginationLink.getAttribute('href');
        if (!href) return;

        const pageUrl = new URL(href, window.location.origin);
        const page = pageUrl.searchParams.get('page') || '1';
        const query = pageUrl.searchParams.get('q') || (context.searchInput?.value || '');
        const scope = pageUrl.searchParams.get('scope') || root.core.getSearchScope(context);
        const sort = pageUrl.searchParams.get('sort') || (context.tabList.dataset.currentSort || '');
        const dir = pageUrl.searchParams.get('dir') || (context.tabList.dataset.currentDir || 'desc');

        if (context.searchInput) context.searchInput.value = query;
        root.core.syncSearchClearButton(context);
        if (context.searchDescricaoCheckbox) {
          context.searchDescricaoCheckbox.checked = scope === 'descricao';
        }
        await root.core.refreshTabList(context, page, query, scope, sort, dir);
        return;
      }

      const sortLink = event.target.closest('.sort-link');
      if (sortLink) {
        event.preventDefault();
        const href = sortLink.getAttribute('href');
        if (!href) return;

        const sortUrl = new URL(href, window.location.origin);
        const sort = sortUrl.searchParams.get('sort') || '';
        const dir = sortUrl.searchParams.get('dir') || 'desc';
        const query = sortUrl.searchParams.get('q') || (context.searchInput?.value || '');
        const scope = sortUrl.searchParams.get('scope') || root.core.getSearchScope(context);

        if (context.searchInput) context.searchInput.value = query;
        root.core.syncSearchClearButton(context);
        if (context.searchDescricaoCheckbox) {
          context.searchDescricaoCheckbox.checked = scope === 'descricao';
        }
        await root.core.refreshTabList(context, 1, query, scope, sort, dir);
        return;
      }

      const row = event.target.closest(context.rowSelector);
      if (!row) return;
      await handleRowClick(context, row);
    });
  }

  function bindExportListClick(context) {
    if (!context.tabExportList || context.tabExportList.dataset.bound === '1') return;

    context.tabExportList.dataset.bound = '1';
    context.tabExportList.addEventListener('click', async (event) => {
      const paginationLink = event.target.closest('.pagination a, .pagination-btn[href]');
      if (paginationLink) {
        event.preventDefault();
        const href = paginationLink.getAttribute('href');
        if (!href) return;

        const pageUrl = new URL(href, window.location.origin);
        const page = pageUrl.searchParams.get('page') || '1';
        const sort = pageUrl.searchParams.get('sort') || (context.tabExportList.dataset.currentSort || '');
        const dir = pageUrl.searchParams.get('dir') || (context.tabExportList.dataset.currentDir || 'desc');
        await root.core.refreshExportList(context, page, sort, dir);
        return;
      }

      const sortLink = event.target.closest('.sort-link');
      if (sortLink) {
        event.preventDefault();
        const href = sortLink.getAttribute('href');
        if (!href) return;

        const sortUrl = new URL(href, window.location.origin);
        const sort = sortUrl.searchParams.get('sort') || '';
        const dir = sortUrl.searchParams.get('dir') || 'desc';
        await root.core.refreshExportList(context, 1, sort, dir);
        return;
      }

      const row = event.target.closest(context.rowSelector);
      if (!row) return;
      await handleRowClick(context, row);
    });
  }

  function init(context) {
    if (context.searchInput) {
      context.searchInput.addEventListener('input', () => {
        root.core.syncSearchClearButton(context);
        if (context.searchDebounceTimer) clearTimeout(context.searchDebounceTimer);
        context.searchDebounceTimer = setTimeout(async () => {
          await root.core.refreshTabList(context, 1, context.searchInput.value || '', root.core.getSearchScope(context));
        }, 250);
      });
    }

    if (context.searchClearBtn && context.searchInput) {
      context.searchClearBtn.addEventListener('click', async () => {
        context.searchInput.value = '';
        root.core.syncSearchClearButton(context);
        context.searchInput.focus();
        await root.core.refreshTabList(context, 1, '', root.core.getSearchScope(context));
      });
    }

    if (context.searchDescricaoCheckbox) {
      context.searchDescricaoCheckbox.addEventListener('change', async () => {
        await root.core.refreshTabList(context, 1, context.searchInput?.value || '', root.core.getSearchScope(context));
      });
    }

    if (context.searchInput && context.tabList) {
      context.searchInput.value = context.tabList.dataset.currentQuery || '';
      root.core.syncSearchClearButton(context);
    }

    if (context.searchDescricaoCheckbox && context.tabList) {
      context.searchDescricaoCheckbox.checked = (context.tabList.dataset.currentScope || 'default') === 'descricao';
    }

    root.core.syncSearchForTab(context, 'tab-list');

    if (context.tabsContainer) {
      context.tabsContainer.addEventListener('click', (event) => {
        const button = event.target.closest('.tab-btn[data-tab]');
        if (!button || button.dataset.locked === 'true') return;
        root.core.syncSearchForTab(context, button.dataset.tab);
      });
    }

    bindTabListClick(context);
    bindExportListClick(context);
  }

  searchList.handleRowClick = handleRowClick;
  searchList.bindTabListClick = bindTabListClick;
  searchList.bindExportListClick = bindExportListClick;
  searchList.init = init;
})();
