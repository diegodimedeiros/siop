(function () {
  'use strict';

  const root = window.SIOPOcorrencias = window.SIOPOcorrencias || {};
  const create = root.create = root.create || {};
  const shared = window.SIOPShared || {};
  const requestJSON = shared.http?.requestJSON;
  const runWithLoading = shared.feedback?.runWithLoading;
  const showRequestError = shared.feedback?.showRequestError;

  function init(context) {
    if (!context.createForm || !context.btnSalvar) return;

    context.btnSalvar.addEventListener('click', () => context.createForm.requestSubmit());
    context.createForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      await runWithLoading?.(context.btnSalvar, async () => {
        try {
          const payload = await requestJSON(context.createForm.action, {
            method: 'POST',
            body: new FormData(context.createForm),
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          });

          if (!payload?.ok || !payload?.data?.id) {
            console.error('JSON inesperado:', payload);
            throw new Error(`Erro ao cadastrar ${context.entityLabel}.`);
          }

          root.feedback.showModal(
            context,
            `${context.entityLabel.charAt(0).toUpperCase() + context.entityLabel.slice(1)} cadastrado com sucesso!`,
            payload.data.id
          );

          context.createForm.reset();
          root.core.setNewOcorrenciaDate(true);
          await root.core.refreshTabList(context);
          root.core.goToTab(context, 'tab-list');
        } catch (error) {
          showRequestError?.(error, `Erro ao cadastrar ${context.entityLabel}.`);
        }
      }, { label: 'Salvando...' });
    });
  }

  create.init = init;
})();
