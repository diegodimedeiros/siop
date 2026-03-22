(() => {
  "use strict";

  if (!window.SIOPShared) {
    throw new Error("Shared nao carregado");
  }

  function getShared(name, value) {
    if (!value) {
      console.error(`${name} nao carregado`);
    }
    return value;
  }

  const shared = window.SIOPShared;
  const BrowserGeolocationCollector = getShared("geolocation.BrowserGeolocationCollector", shared.geolocation?.BrowserGeolocationCollector);
  const postJSON = getShared("http.postJSON", shared.http?.postJSON);

  async function postGeolocation(payload) {
    const response = await postJSON("/controlebc/api/geolocalizacao/browser/", payload);
    if (response.ok === false) {
      throw new Error(response.error || "Falha ao salvar geolocalização.");
    }
    return response.data;
  }

  async function init() {
    const btnCapture = document.getElementById("btn-capture-geolocation");
    const btnSave = document.getElementById("btn-save-geolocation");
    const status = document.getElementById("geo-status");
    const preview = document.getElementById("geo-preview");
    const inputObjetoTipo = document.getElementById("geo-objeto-tipo");
    const inputObjetoId = document.getElementById("geo-objeto-id");

    if (!btnCapture || !btnSave || !status || !preview || !inputObjetoTipo || !inputObjetoId) return;

    const collector = new BrowserGeolocationCollector();
    let latestPayload = null;

    btnCapture.addEventListener("click", async () => {
      status.textContent = "Coletando geolocalização...";
      btnCapture.disabled = true;
      try {
        const payload = await collector.collect();
        latestPayload = payload;
        preview.textContent = JSON.stringify(payload.position, null, 2);
        status.textContent = "Geolocalização coletada com sucesso.";
      } catch (err) {
        latestPayload = null;
        preview.textContent = "";
        status.textContent = err.message || "Falha ao coletar geolocalização.";
      } finally {
        btnCapture.disabled = false;
      }
    });

    btnSave.addEventListener("click", async () => {
      if (!latestPayload) {
        status.textContent = "Colete a geolocalização antes de salvar.";
        return;
      }

      const objetoId = (inputObjetoId.value || "").trim();
      if (!objetoId) {
        status.textContent = "Informe o ID do registro para salvar.";
        return;
      }

      btnSave.disabled = true;
      status.textContent = "Salvando geolocalização...";
      try {
        const persisted = await postGeolocation({
          ...latestPayload,
          objeto_tipo: inputObjetoTipo.value || "resgate",
          objeto_id: Number(objetoId),
        });
        status.textContent = `Geolocalização salva (ID ${persisted.id}).`;
      } catch (err) {
        status.textContent = err.message || "Falha ao salvar geolocalização.";
      } finally {
        btnSave.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", init, { once: true });
})();
