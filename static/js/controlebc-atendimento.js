(() => {
  'use strict';

  if (!window.SIOPShared) {
    throw new Error('Shared nao carregado');
  }

  function getShared(name, value) {
    if (!value) {
      console.error(`${name} nao carregado`);
    }
    return value;
  }

  const shared = window.SIOPShared;
  const isTrue = getShared('forms.isTrue', shared.forms?.isTrue);
  const toggleGroup = getShared('forms.toggleGroup', shared.forms?.toggleGroup);
  const updateFileStatus = getShared('files.updateFileStatus', shared.files?.updateFileStatus);
  const rebuildInputFiles = getShared('files.rebuildInputFiles', shared.files?.rebuildInputFiles);
  const renderFileList = getShared('files.renderFileList', shared.files?.renderFileList);
  const getCurrentPosition = getShared('geolocation.getCurrentPosition', shared.geolocation?.getCurrentPosition);
  const fillCoordinateFields = getShared('geolocation.fillCoordinateFields', shared.geolocation?.fillCoordinateFields);
  const renderGeolocation = getShared('geolocation.renderGeolocation', shared.geolocation?.renderGeolocation);
  const renderGeolocationError = getShared('geolocation.renderGeolocationError', shared.geolocation?.renderGeolocationError);
  const createSignaturePad = getShared('signaturePad.createSignaturePad', shared.signaturePad?.createSignaturePad);
  const openModal = getShared('modal.openModal', shared.modal?.openModal);
  const closeModal = getShared('modal.closeModal', shared.modal?.closeModal);
  const setLoading = getShared('feedback.setLoading', shared.feedback?.setLoading);
  const GEO_SUBMIT_TIMEOUT_MS = 2500;

  function wait(ms) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms);
    });
  }

  function initControleBCAtendimentoForm() {
    const form = document.getElementById('atendimento-form');
    if (!form) return;

    let fotosCameraSelecionadas = [];
    let fotosDispositivoSelecionadas = [];

    const locaisPorAreaNode = document.getElementById('locais-por-area');
    const locaisPorArea = locaisPorAreaNode ? JSON.parse(locaisPorAreaNode.textContent) : {};

    const tipoPessoa = document.getElementById('tipo_pessoa');
    const pessoaNacionalidade = document.getElementById('pessoa_nacionalidade');
    const contatoEstado = document.getElementById('contato_estado');
    const contatoPais = document.getElementById('contato_pais');
    const area = document.getElementById('area_atendimento');
    const local = document.getElementById('local');
    const possuiAcompanhante = document.getElementById('possui_acompanhante');
    const acompanhanteNomeGroup = document.getElementById('acompanhante_nome_group');
    const acompanhanteDocumentoGroup = document.getElementById('acompanhante_documento_group');
    const acompanhanteOrgaoGroup = document.getElementById('acompanhante_orgao_group');
    const acompanhanteSexoGroup = document.getElementById('acompanhante_sexo_group');
    const acompanhanteDataGroup = document.getElementById('acompanhante_data_group');
    const acompanhanteNacionalidadeGroup = document.getElementById('acompanhante_nacionalidade_group');
    const grauParentescoGroup = document.getElementById('grau_parentesco_group');
    const doencaPreexistente = document.getElementById('doenca_preexistente');
    const descricaoDoencaGroup = document.getElementById('descricao_doenca_group');
    const alergia = document.getElementById('alergia');
    const descricaoAlergiaGroup = document.getElementById('descricao_alergia_group');
    const planoSaude = document.getElementById('plano_saude');
    const nomePlanoGroup = document.getElementById('nome_plano_group');
    const numeroCarteirinhaGroup = document.getElementById('numero_carteirinha_group');
    const atendimentos = document.getElementById('atendimentos');
    const primeirosSocorros = document.getElementById('primeiros_socorros');
    const seguiuPasseio = document.getElementById('seguiu_passeio');
    const houveRemocao = document.getElementById('houve_remocao');
    const transporteGroup = document.getElementById('transporte_group');
    const transporte = document.getElementById('transporte');
    const encaminhamento = document.getElementById('encaminhamento');
    const hospital = document.getElementById('hospital');
    const medicoResponsavel = document.getElementById('medico_responsavel');
    const crm = document.getElementById('crm');
    const assinaturaInput = document.getElementById('assinatura_atendido');
    const assinaturaStatus = document.getElementById('assinatura-status');
    const assinaturaModal = document.getElementById('signature-modal');
    const btnAssinaturaModal = document.getElementById('btn-assinatura-modal');
    const btnAssinaturaLimpar = document.getElementById('btn-assinatura-limpar');
    const btnAssinaturaCancelar = document.getElementById('btn-assinatura-cancelar');
    const btnAssinaturaConfirmar = document.getElementById('btn-assinatura-confirmar');
    const assinaturaModalCanvas = document.getElementById('assinatura_modal_canvas');
    const geoLatitudeInput = document.getElementById('geo_latitude');
    const geoLongitudeInput = document.getElementById('geo_longitude');
    const geolocalizacaoAtendimento = document.getElementById('geolocalizacao_atendimento');
    const geolocalizacaoAtendimentoVazia = document.getElementById('geolocalizacao_atendimento_vazia');
    const fotosCameraInput = document.getElementById('fotos_camera');
    const fotosDispositivoInput = document.getElementById('fotos_dispositivo');
    const listaFotosAtendimento = document.getElementById('lista_fotos_atendimento');
    const listaFotosAtendimentoVazia = document.getElementById('lista_fotos_atendimento_vazia');
    const fotosStatus = document.getElementById('quantidade_fotos_atendimento');
    const submitButton = document.querySelector('button[type="submit"][form="atendimento-form"]');
    const nativeSubmit = HTMLFormElement.prototype.submit;

    function updateLocais() {
      if (!area || !local) return;

      const areaAtual = area.value || '';
      const locais = locaisPorArea[areaAtual] || [];
      const localAtual = local.dataset.selectedValue || local.value;

      local.innerHTML = '';

      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = locais.length ? 'Selecione...' : 'Selecione a área primeiro...';
      local.appendChild(defaultOption);

      locais.forEach((item) => {
        const option = document.createElement('option');
        option.value = item;
        option.textContent = item;
        if (item === localAtual) {
          option.selected = true;
        }
        local.appendChild(option);
      });
    }

    function applyTipoPessoa() {
      const tipoPessoaValue = (tipoPessoa?.value || '').trim().toLowerCase();
      const estrangeiro = tipoPessoaValue.includes('estrangeiro');

      if (contatoEstado) {
        contatoEstado.disabled = estrangeiro;
        if (estrangeiro) contatoEstado.selectedIndex = 0;
      }

      if (contatoPais) {
        contatoPais.readOnly = !estrangeiro;
        if (estrangeiro) {
          if ((contatoPais.value || '').trim().toLowerCase() === 'brasil') {
            contatoPais.value = '';
          }
        } else if (!(contatoPais.value || '').trim()) {
          contatoPais.value = 'Brasil';
        }
      }

      if (pessoaNacionalidade && !estrangeiro && !(pessoaNacionalidade.value || '').trim()) {
        pessoaNacionalidade.value = 'Brasileira';
      }
    }

    function applyAcompanhante() {
      const show = isTrue(possuiAcompanhante?.value);
      toggleGroup(acompanhanteNomeGroup, show);
      toggleGroup(acompanhanteDocumentoGroup, show);
      toggleGroup(acompanhanteOrgaoGroup, show);
      toggleGroup(acompanhanteSexoGroup, show);
      toggleGroup(acompanhanteDataGroup, show);
      toggleGroup(acompanhanteNacionalidadeGroup, show);
      toggleGroup(grauParentescoGroup, show);
    }

    function applySaude() {
      toggleGroup(descricaoDoencaGroup, isTrue(doencaPreexistente?.value));
      toggleGroup(descricaoAlergiaGroup, isTrue(alergia?.value));
      toggleGroup(nomePlanoGroup, isTrue(planoSaude?.value));
      toggleGroup(numeroCarteirinhaGroup, isTrue(planoSaude?.value));
    }

    function syncPrimeirosSocorrosAvailability() {
      if (!atendimentos || !primeirosSocorros) return;

      const canUse = isTrue(atendimentos.value);
      primeirosSocorros.disabled = !canUse;
      if (!canUse) primeirosSocorros.value = '';
    }

    function syncRemocaoAvailability() {
      if (!seguiuPasseio || !houveRemocao) return;

      const canRemove = !isTrue(seguiuPasseio.value);
      houveRemocao.disabled = !canRemove;

      if (!canRemove) {
        houveRemocao.value = 'false';
      }
    }

    function syncEncaminhamentoAvailability() {
      if (!houveRemocao || !encaminhamento) return;

      const canUse = isTrue(houveRemocao.value);
      toggleGroup(transporteGroup, canUse);

      if (transporte) transporte.required = canUse;
      encaminhamento.disabled = !canUse;
      encaminhamento.required = canUse;
      if (hospital) {
        hospital.disabled = !canUse;
        hospital.required = canUse;
        if (!canUse) hospital.value = '';
      }
      if (medicoResponsavel) {
        medicoResponsavel.disabled = !canUse;
        if (!canUse) medicoResponsavel.value = '';
      }
      if (crm) {
        crm.disabled = !canUse;
        if (!canUse) crm.value = '';
      }

      if (!canUse) {
        if (transporte) transporte.value = '';
        encaminhamento.value = '';
      }
    }

    function updateAssinaturaStatus() {
      if (!assinaturaStatus || !assinaturaInput) return;
      assinaturaStatus.textContent = (assinaturaInput.value || '').trim()
        ? 'Assinatura capturada'
        : 'Sem assinatura';
    }

    const assinaturaPad = createSignaturePad(assinaturaModalCanvas);

    function openAssinaturaModal() {
      if (!assinaturaModal || !assinaturaPad) return;
      assinaturaPad.loadFromDataURL(assinaturaInput ? assinaturaInput.value : '');
      openModal(assinaturaModal);
    }

    function closeAssinaturaModal() {
      if (!assinaturaModal) return;
      closeModal(assinaturaModal);
    }

    function getFotosSelecionadas() {
      return fotosCameraSelecionadas.concat(fotosDispositivoSelecionadas);
    }

    function syncPhotoList() {
      const fotos = getFotosSelecionadas();
      renderFileList({
        files: fotos,
        listNode: listaFotosAtendimento,
        emptyNode: listaFotosAtendimentoVazia,
        onRemove: (index) => {
          if (index < fotosCameraSelecionadas.length) {
            fotosCameraSelecionadas = fotosCameraSelecionadas.filter((_, currentIndex) => currentIndex !== index);
            rebuildInputFiles(fotosCameraInput, fotosCameraSelecionadas);
          } else {
            const dispositivoIndex = index - fotosCameraSelecionadas.length;
            fotosDispositivoSelecionadas = fotosDispositivoSelecionadas.filter((_, currentIndex) => currentIndex !== dispositivoIndex);
            rebuildInputFiles(fotosDispositivoInput, fotosDispositivoSelecionadas);
          }

          updateFileStatus(fotoInputs, fotosStatus, 'foto', 'fotos');
          syncPhotoList();
        }
      });
    }

    function resetGeolocation() {
      if (geoLatitudeInput) geoLatitudeInput.value = '';
      if (geoLongitudeInput) geoLongitudeInput.value = '';
      if (geolocalizacaoAtendimento) geolocalizacaoAtendimento.innerHTML = '';
      if (geolocalizacaoAtendimentoVazia) {
        geolocalizacaoAtendimentoVazia.textContent = 'Nenhuma geolocalização registrada ainda.';
        geolocalizacaoAtendimentoVazia.style.display = '';
      }
    }

    function fillGeolocationFields(position) {
      if (!geoLatitudeInput || !geoLongitudeInput || !position?.coords) return;

      const coordinates = fillCoordinateFields(position, geoLatitudeInput, geoLongitudeInput, 7);
      if (!coordinates) return;
      renderGeolocation(geolocalizacaoAtendimento, geolocalizacaoAtendimentoVazia, coordinates.latitude, coordinates.longitude, {
        itemClass: 'geolocation-item-row',
        labelClass: '',
        valueClass: '',
      });
    }

    async function captureGeolocationBeforeSubmit() {
      if (!geoLatitudeInput || !geoLongitudeInput) return;

      if ((geoLatitudeInput.value || '').trim() && (geoLongitudeInput.value || '').trim()) {
        renderGeolocation(geolocalizacaoAtendimento, geolocalizacaoAtendimentoVazia, geoLatitudeInput.value.trim(), geoLongitudeInput.value.trim(), {
          itemClass: 'geolocation-item-row',
          labelClass: '',
          valueClass: '',
        });
        return;
      }

      if (!getCurrentPosition) {
        renderGeolocationError(geolocalizacaoAtendimento, geolocalizacaoAtendimentoVazia, 'Geolocalização indisponível neste dispositivo.');
        return;
      }

      renderGeolocationError(geolocalizacaoAtendimento, geolocalizacaoAtendimentoVazia, 'Obtendo geolocalização...');
      try {
        const position = await getCurrentPosition({
          enableHighAccuracy: true,
          timeout: 8000,
          maximumAge: 15000,
        });
        fillGeolocationFields(position);
      } catch {
        renderGeolocationError(geolocalizacaoAtendimento, geolocalizacaoAtendimentoVazia, 'Não foi possível obter a localização.');
      }
    }

    const fotoInputs = [fotosCameraInput, fotosDispositivoInput].filter(Boolean);
    if (fotoInputs.length) {
      const syncFotos = (changedInput) => {
        if (changedInput === fotosCameraInput) {
          const novosArquivos = Array.from(fotosCameraInput.files || []);
          if (novosArquivos.length) {
            fotosCameraSelecionadas = fotosCameraSelecionadas.concat(novosArquivos);
          }
          rebuildInputFiles(fotosCameraInput, fotosCameraSelecionadas);
        }

        if (changedInput === fotosDispositivoInput) {
          const novosArquivos = Array.from(fotosDispositivoInput.files || []);
          if (novosArquivos.length) {
            fotosDispositivoSelecionadas = fotosDispositivoSelecionadas.concat(novosArquivos);
          }
          rebuildInputFiles(fotosDispositivoInput, fotosDispositivoSelecionadas);
        }

        updateFileStatus(fotoInputs, fotosStatus, 'foto', 'fotos');
        syncPhotoList();
        if ((changedInput?.files?.length || 0) > 0) {
          captureGeolocationBeforeSubmit();
        }
      };

      fotoInputs.forEach((input) => {
        input.addEventListener('change', () => syncFotos(input));
      });

      updateFileStatus(fotoInputs, fotosStatus, 'foto', 'fotos');
      syncPhotoList();
    }

    tipoPessoa?.addEventListener('change', applyTipoPessoa);
    possuiAcompanhante?.addEventListener('change', applyAcompanhante);
    doencaPreexistente?.addEventListener('change', applySaude);
    alergia?.addEventListener('change', applySaude);
    planoSaude?.addEventListener('change', applySaude);
    atendimentos?.addEventListener('change', syncPrimeirosSocorrosAvailability);
    seguiuPasseio?.addEventListener('change', () => {
      syncRemocaoAvailability();
      syncEncaminhamentoAvailability();
    });
    houveRemocao?.addEventListener('change', syncEncaminhamentoAvailability);
    area?.addEventListener('change', updateLocais);

    if (btnAssinaturaModal) btnAssinaturaModal.addEventListener('click', openAssinaturaModal);
    if (btnAssinaturaLimpar && assinaturaPad) {
      btnAssinaturaLimpar.addEventListener('click', () => assinaturaPad.clear());
    }
    if (btnAssinaturaCancelar) btnAssinaturaCancelar.addEventListener('click', closeAssinaturaModal);
    if (btnAssinaturaConfirmar && assinaturaPad && assinaturaInput) {
      btnAssinaturaConfirmar.addEventListener('click', () => {
        assinaturaInput.value = assinaturaPad.getDataURL();
        updateAssinaturaStatus();
        closeAssinaturaModal();
      });
    }
    if (assinaturaModal) {
      assinaturaModal.addEventListener('click', (event) => {
        if (event.target === assinaturaModal) closeAssinaturaModal();
      });
    }

    form.addEventListener('reset', () => {
      window.setTimeout(() => {
        setLoading?.(submitButton, false);
        updateLocais();
        applyTipoPessoa();
        applyAcompanhante();
        applySaude();
        syncPrimeirosSocorrosAvailability();
        syncRemocaoAvailability();
        syncEncaminhamentoAvailability();
        if (assinaturaInput) assinaturaInput.value = '';
        fotosCameraSelecionadas = [];
        fotosDispositivoSelecionadas = [];
        resetGeolocation();
        if (assinaturaPad) assinaturaPad.clear();
        fotoInputs.forEach((input) => {
          input.value = '';
        });
        updateFileStatus(fotoInputs, fotosStatus, 'foto', 'fotos');
        syncPhotoList();
        updateAssinaturaStatus();
      }, 0);
    });

    let isPreparingSubmitWithGeo = false;
    form.addEventListener('submit', async (event) => {
      if (isPreparingSubmitWithGeo) return;
      if (!form.reportValidity()) return;

      event.preventDefault();
      isPreparingSubmitWithGeo = true;
      setLoading?.(submitButton, true, { label: 'Salvando...' });

      try {
        await Promise.race([
          captureGeolocationBeforeSubmit(),
          wait(GEO_SUBMIT_TIMEOUT_MS),
        ]);
        nativeSubmit.call(form);
      } catch (error) {
        console.error('Erro ao preparar envio do atendimento.', error);
      } finally {
        isPreparingSubmitWithGeo = false;
      }
    });

    updateLocais();
    applyTipoPessoa();
    applyAcompanhante();
    applySaude();
    syncPrimeirosSocorrosAvailability();
    syncRemocaoAvailability();
    syncEncaminhamentoAvailability();
    updateAssinaturaStatus();
    resetGeolocation();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initControleBCAtendimentoForm);
  } else {
    initControleBCAtendimentoForm();
  }
})();
