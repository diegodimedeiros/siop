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
  const syncFileCounter = getShared('files.syncFileCounter', shared.files?.syncFileCounter);
  const rebuildInputFiles = getShared('files.rebuildInputFiles', shared.files?.rebuildInputFiles);
  const renderFileList = getShared('files.renderFileList', shared.files?.renderFileList);
  const renderGeolocation = getShared('geolocation.renderGeolocation', shared.geolocation?.renderGeolocation);
  const renderGeolocationError = getShared('geolocation.renderGeolocationError', shared.geolocation?.renderGeolocationError);
  const getCurrentPosition = getShared('geolocation.getCurrentPosition', shared.geolocation?.getCurrentPosition);
  const fillCoordinateFields = getShared('geolocation.fillCoordinateFields', shared.geolocation?.fillCoordinateFields);
  const openModal = getShared('modal.openModal', shared.modal?.openModal);
  const setModalMessage = getShared('modal.setModalMessage', shared.modal?.setModalMessage);
  const requestJSON = getShared('http.requestJSON', shared.http?.requestJSON);
  const setLoading = getShared('feedback.setLoading', shared.feedback?.setLoading);
  const runWithLoading = getShared('feedback.runWithLoading', shared.feedback?.runWithLoading);
  const showSuccess = getShared('feedback.showSuccess', shared.feedback?.showSuccess);
  const showRequestError = getShared('feedback.showRequestError', shared.feedback?.showRequestError);

  const $ = (sel, root = document) => root.querySelector(sel);

  function pad2(n) {
    return String(n).padStart(2, '0');
  }

  function toLocalISODateTime(now = new Date()) {
    return (
      now.getFullYear() +
      '-' + pad2(now.getMonth() + 1) +
      '-' + pad2(now.getDate()) +
      'T' + pad2(now.getHours()) +
      ':' + pad2(now.getMinutes())
    );
  }

  function initControleBCManejoForm() {
    const form = $('#manejo-form');
    if (!form) return;

    let fotosCapturaSelecionadas = [];
    let fotosSolturaSelecionadas = [];

    const fotoCapturaInput = $('#foto_captura');
    const quantidadeFotos = $('#quantidade_fotos');
    const listaFotosCaptura = $('#lista_fotos_captura');
    const listaFotosCapturaVazia = $('#lista_fotos_captura_vazia');
    const geolocalizacaoCaptura = $('#geolocalizacao_captura');
    const geolocalizacaoCapturaVazia = $('#geolocalizacao_captura_vazia');
    const latitudeCapturaInput = $('#latitude_captura');
    const longitudeCapturaInput = $('#longitude_captura');

    const fotoSolturaInput = $('#foto_soltura');
    const quantidadeFotosSoltura = $('#quantidade_fotos_soltura');
    const listaFotosSoltura = $('#lista_fotos_soltura');
    const listaFotosSolturaVazia = $('#lista_fotos_soltura_vazia');

    const realizadoManejo = $('#realizado_manejo');
    const areaSolturaGroup = $('#area_soltura_group');
    const localSolturaGroup = $('#local_soltura_group');
    const fotosSolturaGroup = $('#fotos_soltura_group');
    const listaFotosSolturaGroup = $('#lista_fotos_soltura_group');
    const geolocalizacaoSolturaGroup = $('#geolocalizacao_soltura_group');
    const geolocalizacaoSoltura = $('#geolocalizacao_soltura');
    const geolocalizacaoSolturaVazia = $('#geolocalizacao_soltura_vazia');
    const areaSolturaInput = $('#area_soltura');
    const localSolturaInput = $('#local_soltura');
    const latitudeSolturaInput = $('#latitude_soltura');
    const longitudeSolturaInput = $('#longitude_soltura');
    const responsavelManejoInput = $('#responsavel_manejo');

    const acionadoOrgaoPublico = $('#acionado_orgao_publico');
    const orgaoPublicoGroup = $('#orgao_publico_group');
    const numeroBoletimGroup = $('#numero_boletim_ocorrencia_group');
    const orgaoPublicoInput = $('#orgao_publico');
    const numeroBoletimInput = $('#numero_boletim_ocorrencia');

    const dataHoraInput = $('#data_hora');
    const modalSucesso = $('#modal-sucesso');
    const modalId = $('#modal-id');
    const submitButton = document.querySelector('button[type="submit"][form="manejo-form"]');

    function setCurrentDateTime() {
      if (dataHoraInput && !dataHoraInput.value) {
        dataHoraInput.value = toLocalISODateTime();
      }
    }

    function syncSolturaFields() {
      if (!realizadoManejo || !areaSolturaGroup || !localSolturaGroup) return;

      const enabled = realizadoManejo.checked;
      areaSolturaGroup.classList.toggle('is-hidden', !enabled);
      localSolturaGroup.classList.toggle('is-hidden', !enabled);
      if (fotosSolturaGroup) fotosSolturaGroup.classList.toggle('is-hidden', !enabled);
      if (listaFotosSolturaGroup) listaFotosSolturaGroup.classList.toggle('is-hidden', !enabled);
      if (geolocalizacaoSolturaGroup) geolocalizacaoSolturaGroup.classList.toggle('is-hidden', !enabled);

      if (areaSolturaInput) areaSolturaInput.disabled = !enabled;
      if (localSolturaInput) localSolturaInput.disabled = !enabled;
      if (latitudeSolturaInput) latitudeSolturaInput.disabled = !enabled;
      if (longitudeSolturaInput) longitudeSolturaInput.disabled = !enabled;
      if (responsavelManejoInput) responsavelManejoInput.required = enabled;
    }

    function syncOrgaoPublicoFields() {
      if (!acionadoOrgaoPublico || !orgaoPublicoGroup || !numeroBoletimGroup) return;

      const enabled = acionadoOrgaoPublico.checked;
      orgaoPublicoGroup.classList.toggle('is-hidden', !enabled);
      numeroBoletimGroup.classList.toggle('is-hidden', !enabled);

      if (orgaoPublicoInput) {
        orgaoPublicoInput.disabled = !enabled;
        orgaoPublicoInput.required = enabled;
      }
      if (numeroBoletimInput) numeroBoletimInput.disabled = !enabled;
    }

    function syncPhotoList({ input, files, listNode, emptyNode, onRemove }) {
      if (!input || !listNode || !emptyNode) return;
      renderFileList({ files, listNode, emptyNode, onRemove });
    }

    function resetGeolocation() {
      if (latitudeCapturaInput) latitudeCapturaInput.value = '';
      if (longitudeCapturaInput) longitudeCapturaInput.value = '';
      if (latitudeSolturaInput) latitudeSolturaInput.value = '';
      if (longitudeSolturaInput) longitudeSolturaInput.value = '';

      if (geolocalizacaoCaptura) geolocalizacaoCaptura.innerHTML = '';
      if (geolocalizacaoSoltura) geolocalizacaoSoltura.innerHTML = '';

      if (geolocalizacaoCapturaVazia) {
        geolocalizacaoCapturaVazia.textContent = 'Nenhuma geolocalizacao registrada ainda.';
        geolocalizacaoCapturaVazia.style.display = '';
      }
      if (geolocalizacaoSolturaVazia) {
        geolocalizacaoSolturaVazia.textContent = 'Nenhuma geolocalizacao registrada ainda.';
        geolocalizacaoSolturaVazia.style.display = '';
      }
    }

    function resetManejoFormState() {
      fotosCapturaSelecionadas = [];
      fotosSolturaSelecionadas = [];

      rebuildInputFiles(fotoCapturaInput, fotosCapturaSelecionadas);
      rebuildInputFiles(fotoSolturaInput, fotosSolturaSelecionadas);

      syncFileCounter(quantidadeFotos, fotosCapturaSelecionadas, { singular: 'foto', plural: 'fotos' });
      syncFileCounter(quantidadeFotosSoltura, fotosSolturaSelecionadas, { singular: 'foto', plural: 'fotos' });

      syncPhotoList({
        input: fotoCapturaInput,
        files: fotosCapturaSelecionadas,
        listNode: listaFotosCaptura,
        emptyNode: listaFotosCapturaVazia,
        onRemove: () => {}
      });
      syncPhotoList({
        input: fotoSolturaInput,
        files: fotosSolturaSelecionadas,
        listNode: listaFotosSoltura,
        emptyNode: listaFotosSolturaVazia,
        onRemove: () => {}
      });

      resetGeolocation();
      syncSolturaFields();
      syncOrgaoPublicoFields();
      setCurrentDateTime();
    }

    function showSuccessModal(idValue) {
      if (!modalSucesso) {
        showSuccess?.(idValue ? `Manejo cadastrado com sucesso! ID: ${idValue}.` : 'Manejo cadastrado com sucesso!');
        return;
      }
      setModalMessage(modalSucesso, 'Manejo cadastrado com sucesso!');
      if (modalId) {
        modalId.textContent = idValue ? String(idValue) : '';
      }
      openModal(modalSucesso);
    }

    function fillCurrentGeolocation(kind) {
      const isCaptura = kind === 'captura';
      const container = isCaptura ? geolocalizacaoCaptura : geolocalizacaoSoltura;
      const emptyNode = isCaptura ? geolocalizacaoCapturaVazia : geolocalizacaoSolturaVazia;
      const latitudeInput = isCaptura ? latitudeCapturaInput : latitudeSolturaInput;
      const longitudeInput = isCaptura ? longitudeCapturaInput : longitudeSolturaInput;

      if (!('geolocation' in navigator)) {
        renderGeolocationError(container, emptyNode, 'Geolocalizacao indisponivel neste dispositivo.');
        return;
      }

      renderGeolocationError(container, emptyNode, 'Obtendo geolocalizacao...');

      getCurrentPosition({
        enableHighAccuracy: true,
        maximumAge: 10000,
        timeout: 15000,
      }).then((position) => {
        const coordinates = fillCoordinateFields(position, latitudeInput, longitudeInput, 7);
        if (coordinates) {
          renderGeolocation(container, emptyNode, coordinates.latitude, coordinates.longitude);
        }
      }).catch(() => {
        renderGeolocationError(container, emptyNode, 'Nao foi possivel obter a localizacao.');
      });
    }

    function syncCapturaList() {
      syncPhotoList({
        input: fotoCapturaInput,
        files: fotosCapturaSelecionadas,
        listNode: listaFotosCaptura,
        emptyNode: listaFotosCapturaVazia,
        onRemove: (index) => {
          fotosCapturaSelecionadas = fotosCapturaSelecionadas.filter((_, currentIndex) => currentIndex !== index);
          rebuildInputFiles(fotoCapturaInput, fotosCapturaSelecionadas);
          syncFileCounter(quantidadeFotos, fotosCapturaSelecionadas, { singular: 'foto', plural: 'fotos' });
          syncCapturaList();
        }
      });
    }

    function syncSolturaList() {
      syncPhotoList({
        input: fotoSolturaInput,
        files: fotosSolturaSelecionadas,
        listNode: listaFotosSoltura,
        emptyNode: listaFotosSolturaVazia,
        onRemove: (index) => {
          fotosSolturaSelecionadas = fotosSolturaSelecionadas.filter((_, currentIndex) => currentIndex !== index);
          rebuildInputFiles(fotoSolturaInput, fotosSolturaSelecionadas);
          syncFileCounter(quantidadeFotosSoltura, fotosSolturaSelecionadas, { singular: 'foto', plural: 'fotos' });
          syncSolturaList();
        }
      });
    }

    if (realizadoManejo) {
      realizadoManejo.addEventListener('change', syncSolturaFields);
      syncSolturaFields();
    }

    if (acionadoOrgaoPublico) {
      acionadoOrgaoPublico.addEventListener('change', syncOrgaoPublicoFields);
    }

    if (fotoCapturaInput) {
      fotoCapturaInput.addEventListener('change', () => {
        const novosArquivos = Array.from(fotoCapturaInput.files || []);
        if (novosArquivos.length) {
          fotosCapturaSelecionadas = fotosCapturaSelecionadas.concat(novosArquivos);
          rebuildInputFiles(fotoCapturaInput, fotosCapturaSelecionadas);
          fillCurrentGeolocation('captura');
        }
        syncFileCounter(quantidadeFotos, fotosCapturaSelecionadas, { singular: 'foto', plural: 'fotos' });
        syncCapturaList();
      });
      rebuildInputFiles(fotoCapturaInput, fotosCapturaSelecionadas);
      syncFileCounter(quantidadeFotos, fotosCapturaSelecionadas, { singular: 'foto', plural: 'fotos' });
      syncCapturaList();
    }

    if (fotoSolturaInput) {
      fotoSolturaInput.addEventListener('change', () => {
        const novosArquivos = Array.from(fotoSolturaInput.files || []);
        if (novosArquivos.length) {
          fotosSolturaSelecionadas = fotosSolturaSelecionadas.concat(novosArquivos);
          rebuildInputFiles(fotoSolturaInput, fotosSolturaSelecionadas);
          fillCurrentGeolocation('soltura');
        }
        syncFileCounter(quantidadeFotosSoltura, fotosSolturaSelecionadas, { singular: 'foto', plural: 'fotos' });
        syncSolturaList();
      });
      rebuildInputFiles(fotoSolturaInput, fotosSolturaSelecionadas);
      syncFileCounter(quantidadeFotosSoltura, fotosSolturaSelecionadas, { singular: 'foto', plural: 'fotos' });
      syncSolturaList();
    }

    form.addEventListener('reset', () => {
      window.setTimeout(() => {
        setLoading?.(submitButton, false);
        resetManejoFormState();
      }, 0);
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      await runWithLoading?.(submitButton, async () => {
        try {
          const payload = await requestJSON(form.action || window.location.pathname, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          });

          if (!payload?.ok) {
            throw new Error('Erro ao cadastrar manejo.');
          }

          const data = payload.data || {};
          showSuccessModal(data.id || null);
          form.reset();
          resetManejoFormState();
        } catch (error) {
          showRequestError?.(error, 'Erro ao cadastrar manejo.');
        }
      }, { label: 'Salvando...' });
    });

    setCurrentDateTime();
    syncOrgaoPublicoFields();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initControleBCManejoForm, { once: true });
  } else {
    initControleBCManejoForm();
  }
})();
