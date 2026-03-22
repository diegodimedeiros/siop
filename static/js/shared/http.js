(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const http = root.http = root.http || {};

  class HttpRequestError extends Error {
    constructor(message, options) {
      super(message);
      this.name = 'HttpRequestError';
      this.status = options?.status || 0;
      this.code = options?.code || '';
      this.category = options?.category || 'unknown';
      this.details = options?.details || null;
      this.userMessage = options?.userMessage || message;
      this.payload = options?.payload || null;
      this.url = options?.url || '';
      this.cause = options?.cause;
    }
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function getErrorCategory(status, payload) {
    if (payload?.error?.code === 'invalid_json' || payload?.error?.code === 'invalid_payload') {
      return 'invalid_response';
    }
    if (status === 400 || status === 422) return 'validation';
    if (status === 401 || status === 403) return 'permission';
    if (status === 404) return 'not_found';
    if (status >= 500) return 'server';
    return 'request';
  }

  function getDefaultUserMessage(status, category) {
    if (category === 'network') {
      return 'Nao foi possivel conectar ao servidor.';
    }
    if (category === 'permission') {
      return 'Voce nao tem permissao para concluir esta acao.';
    }
    if (category === 'not_found') {
      return 'O recurso solicitado nao foi encontrado.';
    }
    if (category === 'validation') {
      return 'Existem dados invalidos no envio.';
    }
    if (category === 'invalid_response') {
      return 'O servidor retornou uma resposta invalida.';
    }
    if (status >= 500) {
      return 'Erro interno ao processar a solicitacao.';
    }
    return 'Nao foi possivel concluir a solicitacao.';
  }

  async function requestJSON(url, opts) {
    let response;
    try {
      response = await fetch(url, opts);
    } catch (error) {
      throw new HttpRequestError('Falha de rede.', {
        url,
        category: 'network',
        userMessage: getDefaultUserMessage(0, 'network'),
        cause: error,
      });
    }

    if (response.status === 204) {
      return { ok: true, data: {}, message: '' };
    }

    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      throw new HttpRequestError(`Resposta invalida ao buscar: ${url} (${response.status})`, {
        url,
        status: response.status,
        category: 'invalid_response',
        userMessage: getDefaultUserMessage(response.status, 'invalid_response'),
        cause: error,
      });
    }

    if (!response.ok || payload?.ok === false) {
      const category = getErrorCategory(response.status, payload);
      const message =
        payload?.error?.message ||
        payload?.error ||
        payload?.message ||
        `Erro ao buscar: ${url} (${response.status})`;

      throw new HttpRequestError(message, {
        url,
        status: response.status,
        code: payload?.error?.code || '',
        category,
        details: payload?.error?.details || null,
        payload,
        userMessage: message || getDefaultUserMessage(response.status, category),
      });
    }

    return payload;
  }

  async function fetchJSON(url, opts) {
    const payload = await requestJSON(url, opts);
    if (payload.ok === false) {
      const message = payload?.error?.message || payload?.error || `Erro ao buscar: ${url}`;
      throw new Error(message);
    }
    return payload.data || {};
  }

  async function postJSON(url, body, opts) {
    return await requestJSON(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
        ...(opts && opts.headers ? opts.headers : {}),
      },
      body: JSON.stringify(body),
      ...opts,
    });
  }

  http.getCookie = getCookie;
  http.HttpRequestError = HttpRequestError;
  http.requestJSON = requestJSON;
  http.fetchJSON = fetchJSON;
  http.postJSON = postJSON;
})();
