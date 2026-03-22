(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const geolocation = root.geolocation = root.geolocation || {};

  class BrowserGeolocationCollector {
    constructor() {
      this.primaryOptions = {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 0,
      };
      this.fallbackOptions = {
        enableHighAccuracy: false,
        timeout: 8000,
        maximumAge: 15000,
      };
    }

    async getPermissionState() {
      if (!navigator.permissions || !navigator.permissions.query) return 'unknown';
      try {
        const result = await navigator.permissions.query({ name: 'geolocation' });
        return result.state || 'unknown';
      } catch {
        return 'unknown';
      }
    }

    getCurrentPosition(options) {
      return new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, options);
      });
    }

    normalizeError(err) {
      if (!err || typeof err.code !== 'number') {
        return { code: 0, message: 'Falha ao obter localizacao.' };
      }
      if (err.code === 1) return { code: 1, message: 'Permissao negada para geolocalizacao.' };
      if (err.code === 2) return { code: 2, message: 'Posicao indisponivel no momento.' };
      if (err.code === 3) return { code: 3, message: 'Tempo esgotado ao obter localizacao.' };
      return { code: err.code, message: err.message || 'Falha ao obter localizacao.' };
    }

    toPayload(position, permissionState) {
      const coords = position.coords;
      return {
        permission_state: permissionState,
        user_agent: navigator.userAgent || '',
        position: {
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy: coords.accuracy ?? null,
          altitude: coords.altitude ?? null,
          heading: coords.heading ?? null,
          speed: coords.speed ?? null,
          captured_at: new Date(position.timestamp).toISOString(),
        },
      };
    }

    async collect() {
      if (!('geolocation' in navigator)) {
        throw new Error('Este navegador nao suporta geolocalizacao.');
      }

      const permissionState = await this.getPermissionState();
      if (permissionState === 'denied') {
        throw new Error('Geolocalizacao bloqueada nas permissoes do navegador.');
      }

      try {
        const precise = await this.getCurrentPosition(this.primaryOptions);
        return this.toPayload(precise, permissionState);
      } catch (firstError) {
        const normalized = this.normalizeError(firstError);
        if (normalized.code === 1) throw new Error(normalized.message);

        try {
          const fallback = await this.getCurrentPosition(this.fallbackOptions);
          return this.toPayload(fallback, permissionState);
        } catch (secondError) {
          const finalError = this.normalizeError(secondError);
          throw new Error(finalError.message);
        }
      }
    }
  }

  function getCurrentPosition(options) {
    if (!('geolocation' in navigator)) {
      return Promise.reject(new Error('Geolocalizacao indisponivel neste dispositivo.'));
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, options);
    });
  }

  function fillCoordinateFields(position, latitudeInput, longitudeInput, decimals) {
    if (!position?.coords) return null;

    const digits = Number.isInteger(decimals) ? decimals : 7;
    const latitude = Number(position.coords.latitude);
    const longitude = Number(position.coords.longitude);

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

    const latitudeValue = latitude.toFixed(digits);
    const longitudeValue = longitude.toFixed(digits);

    if (latitudeInput) latitudeInput.value = latitudeValue;
    if (longitudeInput) longitudeInput.value = longitudeValue;

    return { latitude: latitudeValue, longitude: longitudeValue };
  }

  function renderGeolocation(container, emptyNode, latitude, longitude, options) {
    if (!container || !emptyNode) return;

    const config = options || {};
    container.innerHTML = '';

    const item = document.createElement('div');
    item.className = config.itemClass || 'manejo-geo-item';

    const label = document.createElement('strong');
    label.className = config.labelClass || 'manejo-geo-label';
    label.textContent = config.labelText || 'Lat/Lon:';

    const value = document.createElement('span');
    value.className = config.valueClass || 'manejo-geo-value';
    value.textContent = `${latitude}, ${longitude}`;

    item.appendChild(label);
    item.appendChild(value);
    container.appendChild(item);
    emptyNode.style.display = 'none';
  }

  function renderGeolocationError(container, emptyNode, message) {
    if (!container || !emptyNode) return;
    container.innerHTML = '';
    emptyNode.textContent = message;
    emptyNode.style.display = '';
  }

  geolocation.BrowserGeolocationCollector = BrowserGeolocationCollector;
  geolocation.getCurrentPosition = getCurrentPosition;
  geolocation.fillCoordinateFields = fillCoordinateFields;
  geolocation.renderGeolocation = renderGeolocation;
  geolocation.renderGeolocationError = renderGeolocationError;
})();
