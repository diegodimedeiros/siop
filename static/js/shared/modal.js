(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const modal = root.modal = root.modal || {};

  function toggleBodyScroll(locked) {
    document.body.style.overflow = locked ? 'hidden' : '';
  }

  function openModal(modalNode, options) {
    if (!modalNode) return;

    const config = options || {};
    modalNode.hidden = false;
    modalNode.classList.add('active');
    modalNode.style.display = config.display || 'flex';
    toggleBodyScroll(config.lockScroll !== false);
  }

  function closeModal(modalNode, options) {
    if (!modalNode) return;

    const config = options || {};
    modalNode.classList.remove('active');
    modalNode.style.display = 'none';
    modalNode.hidden = true;
    if (config.unlockScroll !== false) {
      toggleBodyScroll(false);
    }
  }

  function setModalMessage(modalNode, message, selector) {
    if (!modalNode) return;

    const messageNode = selector
      ? modalNode.querySelector(selector)
      : (modalNode.querySelector('.modal-message') || modalNode.querySelector('h2'));

    if (messageNode) {
      messageNode.textContent = message;
    }
  }

  document.addEventListener('click', function (event) {
    const closeButton = event.target.closest('[data-modal-close]');
    if (!closeButton) return;

    const targetSelector = closeButton.getAttribute('data-modal-close');
    const modalNode = targetSelector
      ? document.querySelector(targetSelector)
      : closeButton.closest('.modal-overlay');

    closeModal(modalNode);
  });

  modal.toggleBodyScroll = toggleBodyScroll;
  modal.openModal = openModal;
  modal.closeModal = closeModal;
  modal.setModalMessage = setModalMessage;
})();
