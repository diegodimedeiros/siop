(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const feedback = root.feedback = root.feedback || {};
  const STYLE_ID = 'siop-feedback-styles';
  const CONTAINER_ID = 'siop-feedback-container';
  const DEFAULT_DURATION = 4200;

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      #${CONTAINER_ID} {
        position: fixed;
        top: 24px;
        right: 24px;
        z-index: 1200;
        display: flex;
        flex-direction: column;
        gap: 12px;
        width: min(360px, calc(100vw - 32px));
      }
      .feedback-toast {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.14);
        background: rgba(16, 24, 20, 0.88);
        color: #f5f7f6;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
        backdrop-filter: blur(18px);
      }
      .feedback-toast[data-type="success"] {
        border-color: rgba(16, 185, 129, 0.45);
      }
      .feedback-toast[data-type="error"] {
        border-color: rgba(239, 68, 68, 0.45);
      }
      .feedback-toast[data-type="warning"] {
        border-color: rgba(245, 158, 11, 0.45);
      }
      .feedback-toast-icon {
        width: 10px;
        height: 10px;
        margin-top: 5px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.35);
        flex-shrink: 0;
      }
      .feedback-toast[data-type="success"] .feedback-toast-icon {
        background: #10b981;
      }
      .feedback-toast[data-type="error"] .feedback-toast-icon {
        background: #ef4444;
      }
      .feedback-toast[data-type="warning"] .feedback-toast-icon {
        background: #f59e0b;
      }
      .feedback-toast-body {
        flex: 1;
        min-width: 0;
        line-height: 1.45;
        font-size: 0.95rem;
      }
      .feedback-toast-close {
        appearance: none;
        border: 0;
        background: transparent;
        color: inherit;
        cursor: pointer;
        font-size: 1rem;
        line-height: 1;
        padding: 2px;
        opacity: 0.7;
      }
      .feedback-toast-close:hover {
        opacity: 1;
      }
      .feedback-inline-spinner {
        display: inline-block;
        width: 14px;
        height: 14px;
        border: 2px solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: feedback-spin 0.8s linear infinite;
        flex-shrink: 0;
      }
      .feedback-inline-loading {
        display: inline-flex;
        align-items: center;
        gap: 8px;
      }
      @keyframes feedback-spin {
        to {
          transform: rotate(360deg);
        }
      }
    `;
    document.head.appendChild(style);
  }

  function ensureContainer() {
    ensureStyles();

    let container = document.getElementById(CONTAINER_ID);
    if (!container) {
      container = document.createElement('div');
      container.id = CONTAINER_ID;
      document.body.appendChild(container);
    }
    return container;
  }

  function createToast(message, type) {
    const toast = document.createElement('div');
    toast.className = 'feedback-toast';
    toast.dataset.type = type;

    const icon = document.createElement('span');
    icon.className = 'feedback-toast-icon';
    icon.setAttribute('aria-hidden', 'true');

    const body = document.createElement('div');
    body.className = 'feedback-toast-body';
    body.textContent = message;

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'feedback-toast-close';
    close.setAttribute('aria-label', 'Fechar');
    close.textContent = 'x';
    close.addEventListener('click', () => toast.remove());

    toast.appendChild(icon);
    toast.appendChild(body);
    toast.appendChild(close);
    return toast;
  }

  function show(message, options) {
    if (!message) return null;

    const config = options || {};
    const type = config.type || 'info';
    const duration = config.duration === 0 ? 0 : (config.duration || DEFAULT_DURATION);
    const container = ensureContainer();
    const toast = createToast(message, type);
    container.appendChild(toast);

    if (duration > 0) {
      window.setTimeout(() => {
        toast.remove();
      }, duration);
    }

    return toast;
  }

  function showSuccess(message, options) {
    return show(message, { ...options, type: 'success' });
  }

  function showError(message, options) {
    return show(message, { ...options, type: 'error', duration: options?.duration || 5200 });
  }

  function showWarning(message, options) {
    return show(message, { ...options, type: 'warning' });
  }

  function setLoading(target, loading, options) {
    if (!target) return;

    const config = options || {};
    if (loading) {
      if (target.dataset.feedbackLoading === '1') return;

      target.dataset.feedbackLoading = '1';
      target.dataset.feedbackOriginalHtml = target.innerHTML;
      target.dataset.feedbackOriginalDisabled = target.disabled ? '1' : '0';

      const width = Math.ceil(target.getBoundingClientRect().width);
      if (width > 0) {
        target.dataset.feedbackOriginalWidth = target.style.width || '';
        target.style.width = `${width}px`;
      }

      target.disabled = true;
      target.setAttribute('aria-busy', 'true');
      target.classList.add('is-loading');

      const wrapper = document.createElement('span');
      wrapper.className = 'feedback-inline-loading';

      const spinner = document.createElement('span');
      spinner.className = 'feedback-inline-spinner';
      spinner.setAttribute('aria-hidden', 'true');

      const label = document.createElement('span');
      label.textContent = config.label || target.dataset.loadingLabel || 'Processando...';

      wrapper.appendChild(spinner);
      wrapper.appendChild(label);
      target.innerHTML = '';
      target.appendChild(wrapper);
      return;
    }

    if (target.dataset.feedbackLoading !== '1') return;

    target.innerHTML = target.dataset.feedbackOriginalHtml || '';
    target.disabled = target.dataset.feedbackOriginalDisabled === '1';
    target.removeAttribute('aria-busy');
    target.classList.remove('is-loading');

    if (Object.prototype.hasOwnProperty.call(target.dataset, 'feedbackOriginalWidth')) {
      target.style.width = target.dataset.feedbackOriginalWidth || '';
    }

    delete target.dataset.feedbackLoading;
    delete target.dataset.feedbackOriginalHtml;
    delete target.dataset.feedbackOriginalDisabled;
    delete target.dataset.feedbackOriginalWidth;
  }

  async function runWithLoading(target, task, options) {
    setLoading(target, true, options);
    try {
      return await task();
    } finally {
      setLoading(target, false);
    }
  }

  function getErrorMessage(error, fallback) {
    if (error && typeof error === 'object') {
      if (typeof error.userMessage === 'string' && error.userMessage.trim()) {
        return error.userMessage;
      }
      if (error instanceof Error && error.message) {
        return error.message;
      }
    }

    if (typeof error === 'string' && error.trim()) {
      return error;
    }

    return fallback || 'Nao foi possivel concluir a operacao.';
  }

  function showRequestError(error, fallback, options) {
    console.error('[feedback] request error', error);
    return showError(getErrorMessage(error, fallback), options);
  }

  function withLoadingFallback(target, timeoutMs) {
    if (!target) return function noop() {};

    const timeout = timeoutMs || 6000;
    let finished = false;

    const finish = function finish() {
      if (finished) return;
      finished = true;
      clearTimeout(timerId);
      window.removeEventListener('pagehide', markFinished);
      setLoading(target, false);
    };

    const markFinished = function markFinished() {
      finished = true;
      clearTimeout(timerId);
    };

    const timerId = window.setTimeout(finish, timeout);
    window.addEventListener('pagehide', markFinished, { once: true });
    return finish;
  }

  feedback.show = show;
  feedback.showSuccess = showSuccess;
  feedback.showError = showError;
  feedback.showWarning = showWarning;
  feedback.setLoading = setLoading;
  feedback.runWithLoading = runWithLoading;
  feedback.getErrorMessage = getErrorMessage;
  feedback.showRequestError = showRequestError;
  feedback.withLoadingFallback = withLoadingFallback;
})();
