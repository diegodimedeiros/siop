(function () {
  'use strict';

  if (!window.SIOPShared) {
    throw new Error('Shared nao carregado');
  }

  const root = window.SIOPOcorrencias = window.SIOPOcorrencias || {};
  const feedback = root.feedback = root.feedback || {};
  const shared = window.SIOPShared;
  const openModal = shared.modal?.openModal;
  const setModalMessage = shared.modal?.setModalMessage;
  const showSuccess = shared.feedback?.showSuccess;
  const showWarning = shared.feedback?.showWarning;
  const showError = shared.feedback?.showError;
  const showRequestError = shared.feedback?.showRequestError;

  function showModal(context, message, idValue = null) {
    const modal = context.modalSucesso;
    if (!modal) {
      if (idValue) {
        showSuccess?.(`${message} ID: ${idValue}.`);
      } else {
        showSuccess?.(message);
      }
      return;
    }

    setModalMessage(modal, message);

    const modalId = root.core.$('#modal-id', modal);
    const modalIdRow = modalId?.closest('p');
    if (modalId) modalId.textContent = idValue ? String(idValue) : '';
    if (modalIdRow) modalIdRow.style.display = idValue ? '' : 'none';

    openModal(modal);
  }

  function consumeExportError() {
    const url = new URL(window.location.href);
    const message = (url.searchParams.get('export_error') || '').trim();
    if (!message) return;

    showErrorMessage(message);
    url.searchParams.delete('export_error');
    window.history.replaceState({}, document.title, url.toString());
  }

  function showWarningMessage(message, options) {
    return showWarning?.(message, options);
  }

  function showErrorMessage(message, options) {
    return showError?.(message, options);
  }

  function init(context) {
    consumeExportError();
  }

  feedback.showModal = showModal;
  feedback.showWarning = showWarningMessage;
  feedback.showError = showErrorMessage;
  feedback.showRequestError = showRequestError;
  feedback.consumeExportError = consumeExportError;
  feedback.init = init;
})();
