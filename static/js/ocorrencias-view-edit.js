(function () {
  'use strict';

  const root = window.SIOPOcorrencias = window.SIOPOcorrencias || {};
  const viewEdit = root.viewEdit = root.viewEdit || {};
  const shared = window.SIOPShared || {};
  const requestJSON = shared.http?.requestJSON;
  const runWithLoading = shared.feedback?.runWithLoading;
  const showError = shared.feedback?.showError;
  const showRequestError = shared.feedback?.showRequestError;

  function fillView(context, data) {
    const setVal = (sel, value) => {
      const element = root.core.$(sel);
      if (element) element.value = value ?? '';
    };
    const setText = (sel, value) => {
      const element = root.core.$(sel);
      if (element) element.textContent = value || '—';
    };

    setVal('#view-id', data.id);
    const viewTitleId = root.core.$('#view-title-id');
    if (viewTitleId) viewTitleId.textContent = data.id ? `#${data.id}` : '';

    if (context.isAcessoTerceirosPage) {
      setVal('#view-data', data.entrada);
      setVal('#view-natureza', data.saida);
      setVal('#view-tipo', data.nome);
      setVal('#view-area', data.documento);
      setVal('#view-local', data.empresa);
      setVal('#view-pessoa', data.p1);
      setVal('#view-cftv', data.placa_veiculo);
      setVal('#view-descricao', data.descricao);
    } else {
      setVal('#view-data', data.data);
      setVal('#view-natureza', data.natureza);
      setVal('#view-tipo', data.tipo);
      setVal('#view-area', data.area);
      setVal('#view-local', data.local);
      setVal('#view-pessoa', data.pessoa);
      setVal('#view-cftv', data.cftv ? 'Sim' : 'Não');
      setVal('#view-bombeiro-civil', data.bombeiro_civil ? 'Sim' : 'Não');
      setVal('#view-descricao', data.descricao);
    }

    setText('#view-criado-em', data.criado_em);
    setText('#view-criado-por', data.criado_por);
    setText('#view-modificado-em', data.modificado_em);
    setText('#view-modificado-por', data.modificado_por);

    if (context.btnViewEdit) {
      if (context.isAcessoTerceirosPage) {
        const hasSaida = !!(data.saida || '').trim();
        context.btnViewEdit.disabled = hasSaida;
        context.btnViewEdit.title = hasSaida ? 'Registro com saída preenchida não pode ser editado.' : '';
      } else {
        const hasStatus = Object.prototype.hasOwnProperty.call(data, 'status');
        const isFinalizada = !!data.status;
        context.btnViewEdit.disabled = hasStatus ? isFinalizada : false;
        context.btnViewEdit.title = hasStatus && isFinalizada ? 'Registro finalizado não pode ser editado.' : '';
      }
    }

    const statusBadge = root.core.$('#view-status-badge');
    if (statusBadge) {
      if (context.isAcessoTerceirosPage) {
        const hasSaida = !!(data.saida || '').trim();
        statusBadge.textContent = hasSaida ? 'Finalizada' : 'Visualização';
        statusBadge.classList.toggle('completed', hasSaida);
        statusBadge.classList.toggle('pending', !hasSaida);
      } else if (Object.prototype.hasOwnProperty.call(data, 'status')) {
        const isFinalizada = !!data.status;
        statusBadge.textContent = isFinalizada ? 'Finalizada' : 'Em aberto';
        statusBadge.classList.toggle('completed', isFinalizada);
        statusBadge.classList.toggle('pending', !isFinalizada);
      } else {
        statusBadge.textContent = 'Visualização';
        statusBadge.classList.remove('completed');
        statusBadge.classList.add('pending');
      }
    }

    const anexosTbody = root.core.$('#view-anexos');
    if (!anexosTbody) return;

    if (data.anexos && data.anexos.length > 0) {
      anexosTbody.innerHTML = data.anexos.map((anexo) => `
        <tr>
          <td>${anexo.nome_arquivo || '-'}</td>
          <td>${anexo.mime_type || '-'}</td>
          <td>${anexo.criado_em || '-'}</td>
          <td>
            <a class="nav-link" style="display:inline-flex; padding:10px 14px;"
               href="${anexo.download_url}" target="_blank" rel="noopener">
              Baixar/Abrir
            </a>
          </td>
        </tr>
      `).join('');
    } else {
      anexosTbody.innerHTML = '<tr><td colspan="4">Nenhum anexo encontrado.</td></tr>';
    }
  }

  function init(context) {
    if (context.editForm && context.btnSalvarEdit) {
      context.btnSalvarEdit.addEventListener('click', () => context.editForm.requestSubmit());

      context.editForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        await runWithLoading?.(context.btnSalvarEdit, async () => {
          try {
            const recordId = context.editForm.dataset.recordId || context.editForm.dataset.ocorrenciaId;
            if (recordId && !context.editForm.action) {
              context.editForm.action = `${context.entityBasePath}/${recordId}/edit/`;
            }

            const payload = await requestJSON(context.editForm.action, {
              method: 'POST',
              body: new FormData(context.editForm),
              credentials: 'same-origin',
              headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (!payload?.ok || !payload?.data?.id) {
              console.error('JSON inesperado:', payload);
              throw new Error(`Erro ao editar ${context.entityLabel}.`);
            }

            root.feedback.showModal(
              context,
              `${context.entityLabel.charAt(0).toUpperCase() + context.entityLabel.slice(1)} alterado com sucesso!`,
              payload.data.id
            );

            context.editForm.reset();
            await root.core.refreshTabList(context);
            root.core.goToTab(context, 'tab-list');
          } catch (error) {
            showRequestError?.(error, `Erro ao editar ${context.entityLabel}.`);
          }
        }, { label: 'Salvando...' });
      });
    }

    document.addEventListener('click', (event) => {
      const button = event.target.closest('#btn-cancelar, #btn-cancelar-edit');
      if (!button) return;

      let form = null;
      if (button.id === 'btn-cancelar') {
        form = context.createForm;
      } else if (button.id === 'btn-cancelar-edit') {
        form = context.editForm;
      }

      if (!form) form = button.closest('form');
      if (form) form.reset();
      if (button.id === 'btn-cancelar') {
        root.core.setNewOcorrenciaDate(true);
      }

      root.core.goToTab(context, 'tab-list');
    });

    if (context.btnViewEdit) {
      context.btnViewEdit.addEventListener('click', async () => {
        if (context.btnViewEdit.disabled) return;

        const viewIdEl = root.core.$('#view-id');
        const id = viewIdEl?.value?.trim();
        if (!id) {
          showError?.(`Não foi possível identificar o(a) ${context.entityLabel} para editar.`);
          return;
        }

        const data = await root.core.fetchEntityData(context, id, `Erro ao carregar ${context.entityLabel} para editar.`);
        if (!data) return;
        if (!context.editForm) {
          console.warn(`Form ${context.editFormSelector} não encontrado para editar.`);
          return;
        }

        context.editForm.dataset.recordId = String(data.id ?? '');
        context.editForm.dataset.ocorrenciaId = String(data.id ?? '');

        const titleId = root.core.$('#edit-id');
        if (titleId) titleId.textContent = `#${data.id}`;
        context.editForm.action = `${context.entityBasePath}/${data.id}/edit/`;

        const setField = (selector, value) => {
          const element = root.core.$(selector, context.editForm);
          if (element) element.value = value ?? '';
        };

        setField('#natureza-edit', data.natureza);
        setField('#tipo-edit', data.tipo);
        setField('#area-edit', data.area);
        setField('#local-edit', data.local);
        setField('#nome-edit', data.nome);
        setField('#documento-edit', data.documento);
        setField('#empresa-edit', data.empresa);
        setField('#placa-veiculo-edit', data.placa_veiculo);
        const p1EditField = root.core.$('#p1-edit', context.editForm) || root.core.$('#pessoa-edit', context.editForm);
        if (p1EditField) p1EditField.value = data.p1 ?? data.pessoa ?? '';

        const entradaValue = data.entrada || data.data;
        if (entradaValue) {
          const dt = entradaValue.split(' ');
          if (dt.length === 2) {
            const [date, time] = dt;
            const [d, m, y] = date.split('/');
            setField('#data-edit', `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}T${time}`);
          }
        }

        if (data.saida) {
          const dt = data.saida.split(' ');
          if (dt.length === 2) {
            const [date, time] = dt;
            const [d, m, y] = date.split('/');
            setField('#saida-edit', `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}T${time}`);
          }
        }

        setField('#descricao-edit', data.descricao);
        const cftvEdit = root.core.$('#cftv-edit', context.editForm);
        if (cftvEdit) cftvEdit.checked = !!data.cftv;
        const bombeiroEdit = root.core.$('#bombeiro_civil-edit', context.editForm);
        if (bombeiroEdit) bombeiroEdit.checked = !!data.bombeiro_civil;
        const statusEdit = root.core.$('#status-edit', context.editForm);
        if (statusEdit) statusEdit.checked = !!data.status;

        root.core.$('#edit-criado-em').textContent = data.criado_em || '—';
        root.core.$('#edit-criado-por').textContent = data.criado_por || '—';
        root.core.$('#edit-modificado-em').textContent = data.modificado_em || '—';
        root.core.$('#edit-modificado-por').textContent = data.modificado_por || '—';

        root.core.goToTab(context, 'tab-edit');
      });
    }
  }

  viewEdit.fillView = fillView;
  viewEdit.init = init;
})();
