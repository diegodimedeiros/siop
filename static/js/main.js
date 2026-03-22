/**
 * Script organizado: inicializações no DOMContentLoaded + módulos por responsabilidade
 * - Data/hora automática nos campos #data, #data_hora e #data_atendimento
 * - Selects dependentes: área/local e natureza/tipo
 * - UI: theme toggle, tilt 3D, counters, menu mobile, validação, senha, transições, tabs
 * - Registros:
 *    - Salvar via AJAX + modal + reset + refresh da lista (partial HTML) + ir pra tab list
 *    - Clique na linha da lista (delegação) para abrir tab view e preencher dados
 *    - (NOVO) Botão "Editar" na view: preenche tab-edit e muda para ela
 */

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

  // ============================================================
  // Utilidades
  // ============================================================
  const shared = window.SIOPShared;
  const populateSelect = getShared('forms.populateSelect', shared.forms?.populateSelect);
  const attachConstraintValidation = getShared('forms.attachConstraintValidation', shared.forms?.attachConstraintValidation);
  const fetchJSON = getShared('http.fetchJSON', shared.http?.fetchJSON);
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

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

  // ============================================================
  // 1) Campo data/hora automático
  // ============================================================
  function setNewOcorrenciaDate(force = false) {
    ['#data', '#data_hora', '#data_atendimento'].forEach(sel => {
      const dataInput = $(sel);
      if (dataInput && (force || !dataInput.value)) {
        dataInput.value = toLocalISODateTime();
      }
    });
  }

  function initAutoDate() {
    setNewOcorrenciaDate();
  }

  // ============================================================
  // 2) Selects dependentes (área/local e natureza/tipo)
  // ============================================================
  function initDependentSelects() {
    const areaSelect = $('#area');
    const localSelect = $('#local');
    const areaCapturaSelect = $('#area_captura');
    const localCapturaSelect = $('#local_captura');
    const classeFaunaSelect = $('#classe');
    const nomePopularSelect = $('#nome_popular');
    const naturezaSelect = $('#natureza');
    const tipoSelect = $('#tipo');
    const exportAreaSelect = $('#export-area');
    const exportLocalSelect = $('#export-local');
    const exportNaturezaSelect = $('#export-natureza');
    const exportTipoSelect = $('#export-tipo');
    const p1Select = $('#p1');
    const p1EditSelect = $('#p1-edit');
    const exportP1Select = $('#export-p1');
    const cache = new Map();

    async function getCached(key, loader) {
      if (cache.has(key)) return await cache.get(key);

      // Guarda a Promise imediatamente para evitar chamadas duplicadas concorrentes.
      const promise = (async () => await loader())();
      cache.set(key, promise);
      try {
        const data = await promise;
        cache.set(key, Promise.resolve(data));
        return data;
      } catch (err) {
        cache.delete(key);
        throw err;
      }
    }

    const getAreas = () => getCached('catalog:areas', async () => {
      const data = await fetchJSON('/api/catalogos/areas/');
      return data.areas || [];
    });

    const getNaturezas = () => getCached('catalog:naturezas', async () => {
      const data = await fetchJSON('/api/catalogos/naturezas/');
      return data.naturezas || [];
    });

    const getLocais = area => getCached(`catalog:locais:${area}`, async () => {
      const data = await fetchJSON('/api/catalogos/areas/locais/?area=' + encodeURIComponent(area));
      return data.locais || [];
    });

    const getEspeciesPorClasse = classe => getCached(`catalog:fauna:${classe}`, async () => {
      const data = await fetchJSON('/api/catalogos/fauna/especies/?classe=' + encodeURIComponent(classe));
      return data.especies || [];
    });

    const getTipos = natureza => getCached(`catalog:tipos:${natureza}`, async () => {
      const data = await fetchJSON('/api/catalogos/naturezas/tipos/?natureza=' + encodeURIComponent(natureza));
      return data.tipos || [];
    });

    const getP1 = () => getCached('catalog:p1', async () => {
      const data = await fetchJSON('/api/catalogos/p1/');
      return data.p1 || [];
    });

    // Área -> Local
    if (areaSelect && localSelect) {
      getAreas()
        .then(areas => populateSelect(areaSelect, areas, 'Selecione...'))
        .catch(() => populateSelect(areaSelect, [], 'Erro ao carregar áreas'));

      areaSelect.addEventListener('change', async () => {
        const area = areaSelect.value;

        if (!area) {
          populateSelect(localSelect, [], 'Selecione a área primeiro...');
          return;
        }

        try {
          const locais = await getLocais(area);
          populateSelect(localSelect, locais, 'Selecione...');
        } catch {
          populateSelect(localSelect, [], 'Erro ao carregar locais');
        }
      });
    }

    // Area de captura -> Local de captura
    if (areaCapturaSelect && localCapturaSelect) {
      getAreas()
        .then(areas => populateSelect(areaCapturaSelect, areas, 'Selecione...'))
        .catch(() => populateSelect(areaCapturaSelect, [], 'Erro ao carregar areas'));

      areaCapturaSelect.addEventListener('change', async () => {
        const area = areaCapturaSelect.value;

        if (!area) {
          populateSelect(localCapturaSelect, [], 'Selecione a area primeiro...');
          return;
        }

        try {
          const locais = await getLocais(area);
          populateSelect(localCapturaSelect, locais, 'Selecione...');
        } catch {
          populateSelect(localCapturaSelect, [], 'Erro ao carregar locais');
        }
      });
    }

    // Classe -> Nome Popular
    if (classeFaunaSelect && nomePopularSelect) {
      classeFaunaSelect.addEventListener('change', async () => {
        const classe = classeFaunaSelect.value;

        if (!classe) {
          populateSelect(nomePopularSelect, [], 'Selecione a Classe primeiro...');
          return;
        }

        try {
          const especies = await getEspeciesPorClasse(classe);
          populateSelect(nomePopularSelect, especies, 'Selecione...');
        } catch {
          populateSelect(nomePopularSelect, [], 'Erro ao carregar nomes populares');
        }
      });
    }

    // Natureza -> Tipo
    if (naturezaSelect && tipoSelect) {
      getNaturezas()
        .then(naturezas => populateSelect(naturezaSelect, naturezas, 'Selecione...'))
        .catch(() => populateSelect(naturezaSelect, [], 'Erro ao carregar naturezas'));

      naturezaSelect.addEventListener('change', async () => {
        const natureza = naturezaSelect.value;

        if (!natureza) {
          populateSelect(tipoSelect, [], 'Selecione a natureza primeiro...');
          return;
        }

        try {
          const tipos = await getTipos(natureza);
          populateSelect(tipoSelect, tipos, 'Selecione...');
        } catch {
          populateSelect(tipoSelect, [], 'Erro ao carregar tipos');
        }
      });
    }

    // Área -> Local (Exportar)
    if (exportAreaSelect && exportLocalSelect) {
      getAreas()
        .then(areas => populateSelect(exportAreaSelect, areas, 'Todos'))
        .catch(() => populateSelect(exportAreaSelect, [], 'Erro ao carregar áreas'));

      populateSelect(exportLocalSelect, [], 'Todos');

      exportAreaSelect.addEventListener('change', async () => {
        const area = exportAreaSelect.value;

        if (!area) {
          populateSelect(exportLocalSelect, [], 'Todos');
          return;
        }

        try {
          const locais = await getLocais(area);
          populateSelect(exportLocalSelect, locais, 'Todos');
        } catch {
          populateSelect(exportLocalSelect, [], 'Erro ao carregar locais');
        }
      });
    }

    // Natureza -> Tipo (Exportar)
    if (exportNaturezaSelect && exportTipoSelect) {
      getNaturezas()
        .then(naturezas => populateSelect(exportNaturezaSelect, naturezas, 'Todos'))
        .catch(() => populateSelect(exportNaturezaSelect, [], 'Erro ao carregar naturezas'));

      populateSelect(exportTipoSelect, [], 'Todos');

      exportNaturezaSelect.addEventListener('change', async () => {
        const natureza = exportNaturezaSelect.value;

        if (!natureza) {
          populateSelect(exportTipoSelect, [], 'Todos');
          return;
        }

        try {
          const tipos = await getTipos(natureza);
          populateSelect(exportTipoSelect, tipos, 'Todos');
        } catch {
          populateSelect(exportTipoSelect, [], 'Erro ao carregar tipos');
        }
      });
    }

    // P1
    if (p1Select || p1EditSelect || exportP1Select) {
      getP1()
        .then(options => {
          if (p1Select) populateSelect(p1Select, options, 'Selecione...');
          if (p1EditSelect) populateSelect(p1EditSelect, options, 'Selecione...');
          if (exportP1Select) populateSelect(exportP1Select, options, 'Todos');
        })
        .catch(() => {
          if (p1Select) populateSelect(p1Select, [], 'Erro ao carregar P1');
          if (p1EditSelect) populateSelect(p1EditSelect, [], 'Erro ao carregar P1');
          if (exportP1Select) populateSelect(exportP1Select, [], 'Erro ao carregar P1');
        });
    }
  }

  // ============================================================
  // 3) Theme Toggle
  // ============================================================
  function initThemeToggle() {
    const themeToggle = $('#theme-toggle');
    const iconSun = themeToggle ? $('.icon-sun', themeToggle) : null;
    const iconMoon = themeToggle ? $('.icon-moon', themeToggle) : null;

    function syncIcons(theme) {
      if (!iconSun || !iconMoon) return;
      const isLight = theme === 'light';
      iconSun.style.display = isLight ? 'none' : 'block';
      iconMoon.style.display = isLight ? 'block' : 'none';
    }

    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
      syncIcons(theme);
    }

    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);

    if (!themeToggle) return;

    themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      setTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  // ============================================================
  // 4) Efeito 3D Tilt
  // ============================================================
  function initTiltEffect() {
    $$('.glass-card-3d').forEach(card => {
      card.addEventListener('mousemove', e => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = (y - centerY) / 20;
        const rotateY = (centerX - x) / 20;

        card.style.transform =
          `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(10px)`;
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateZ(0)';
      });
    });
  }

  // ============================================================
  // 5) Counters animados
  // ============================================================
  function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const startTime = performance.now();

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(start + (target - start) * easeOut);

      const prefix = element.dataset.prefix || '';
      const suffix = element.dataset.suffix || '';
      element.textContent = prefix + current.toLocaleString() + suffix;

      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  function initCounters() {
    $$('.stat-value').forEach(counter => {
      const text = (counter.textContent || '').trim();
      const value = parseInt(text.replace(/[^0-9]/g, ''), 10);
      if (Number.isNaN(value)) return;

      if (text.includes('$')) counter.dataset.prefix = '$';
      if (text.includes('%')) counter.dataset.suffix = '%';

      animateCounter(counter, value);
    });
  }

  // ============================================================
  // 6) Menu Mobile
  // ============================================================
  function initMobileMenu() {
    const menuToggle = $('.mobile-menu-toggle');
    const sidebarHandle = $('#sidebar-handle');
    const sidebarBackdrop = $('#sidebar-backdrop');
    const sidebar = $('#sidebar');
    if (!sidebar) return;

    function syncSidebarControls() {
      const isOpen = sidebar.classList.contains('open');

      if (menuToggle) {
        menuToggle.setAttribute('aria-expanded', String(isOpen));
      }

      if (sidebarHandle) {
        sidebarHandle.setAttribute('aria-expanded', String(isOpen));
        sidebarHandle.setAttribute('aria-label', isOpen ? 'Fechar menu lateral' : 'Abrir menu lateral');
      }

      if (sidebarBackdrop) {
        sidebarBackdrop.hidden = !isOpen;
        sidebarBackdrop.classList.toggle('active', isOpen);
      }
    }

    function toggleSidebar() {
      sidebar.classList.toggle('open');
      syncSidebarControls();
    }

    if (menuToggle) {
      menuToggle.addEventListener('click', toggleSidebar);
    }

    if (sidebarHandle) {
      sidebarHandle.addEventListener('click', toggleSidebar);
    }

    if (sidebarBackdrop) {
      sidebarBackdrop.addEventListener('click', () => {
        sidebar.classList.remove('open');
        syncSidebarControls();
      });
    }

    syncSidebarControls();

    document.addEventListener('click', e => {
      const clickedOutside =
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        (!menuToggle || !menuToggle.contains(e.target)) &&
        (!sidebarHandle || !sidebarHandle.contains(e.target));

      if (clickedOutside) {
        sidebar.classList.remove('open');
        syncSidebarControls();
      }
    });
  }

  // ============================================================
  // 7) Validação de formulário (login/register)
  // ============================================================
  function initFormValidation() {
    $$('form[data-validate]').forEach(form => {
      form.addEventListener('submit', e => {
        e.preventDefault();

        let isValid = true;
        const inputs = $$('.form-input[required]', form);

        inputs.forEach(input => {
          if (!input.value.trim()) {
            isValid = false;
            input.style.borderColor = '#ff6b6b';
          } else {
            input.style.borderColor = '';
          }
        });

        const emailInput = $('input[type="email"]', form);
        if (emailInput && emailInput.value) {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!emailRegex.test(emailInput.value)) {
            isValid = false;
            emailInput.style.borderColor = '#ff6b6b';
          }
        }

        if (!isValid) return;

        if (form.dataset.redirect) {
          window.location.href = form.dataset.redirect;
        }
      });
    });

    $$([
      '#ocorrencia-form',
      '#edit-ocorrencia-form',
      '#acesso-terceiros-form',
      '#edit-acesso-terceiros-form',
      '#atendimento-form',
      '#manejo-form'
    ].join(',')).forEach((form) => {
      attachConstraintValidation?.(form);
    });
  }

  // ============================================================
  // 8) Mostrar/ocultar senha
  // ============================================================
  function initPasswordToggle() {
    $$('.password-toggle').forEach(button => {
      button.addEventListener('click', () => {
        const input = $('input', button.parentElement);
        const icon = $('svg', button);
        if (!input || !icon) return;

        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';

        icon.innerHTML = show
          ? '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>'
          : '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
      });
    });
  }

  // ============================================================
  // 9) Transições suaves entre páginas
  // ============================================================
  function initPageTransitions() {
    $$('a[href$=".html"]').forEach(link => {
      link.addEventListener('click', e => {
        if (link.hostname !== window.location.hostname) return;

        e.preventDefault();
        const href = link.getAttribute('href');

        document.body.style.opacity = '0';
        document.body.style.transition = 'opacity 0.3s ease';

        setTimeout(() => {
          window.location.href = href;
        }, 300);
      });
    });

    window.addEventListener('load', () => {
      document.body.style.opacity = '1';
    });
  }

  // ============================================================
  // 10) Tabs de Settings (nav lateral)
  // ============================================================
  function initSettingsTabs() {
    const tabLinks = $$('.settings-nav-link[data-tab]');
    if (tabLinks.length === 0) return;

    tabLinks.forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const tabId = link.getAttribute('data-tab');

        $$('.settings-nav-link').forEach(n => n.classList.remove('active'));
        link.classList.add('active');

        $$('.settings-tab-content').forEach(t => t.classList.remove('active'));
        const target = $('#tab-' + tabId);
        if (target) target.classList.add('active');
      });
    });

    const themeSelect = $('#theme-select');
    if (!themeSelect) return;

    const currentTheme = localStorage.getItem('theme') || 'dark';
    themeSelect.value = currentTheme;

    themeSelect.addEventListener('change', () => {
      const theme = themeSelect.value;

      if (theme === 'system') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
      } else {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
      }

      const iconSun = $('#theme-toggle .icon-sun');
      const iconMoon = $('#theme-toggle .icon-moon');
      if (iconSun && iconMoon) {
        const effectiveTheme = document.documentElement.getAttribute('data-theme');
        const isLight = effectiveTheme === 'light';
        iconSun.style.display = isLight ? 'none' : 'block';
        iconMoon.style.display = isLight ? 'block' : 'none';
      }
    });
  }

  // ============================================================
  // 11) Tabs genéricas
  // ============================================================
  function initGenericTabs() {
    const containers = document.querySelectorAll('.tabs-container');
    if (!containers.length) return;

    containers.forEach(container => {
      const tabBtns = container.querySelectorAll('.tab-btn');
      const tabContents = container.querySelectorAll('.tab-content');
      if (!tabBtns.length || !tabContents.length) return;

      tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          if (btn.dataset.locked === 'true') return; // bloqueia clique manual

          tabBtns.forEach(b => b.classList.remove('active'));
          tabContents.forEach(tc => tc.classList.remove('active'));

          btn.classList.add('active');

          const targetId = btn.getAttribute('data-tab');
          const target = container.querySelector('#' + targetId);
          if (target) target.classList.add('active');
          if (targetId === 'tab-new') setNewOcorrenciaDate();
        });
      });

    });
  }

  // ============================================================
  // 12) Registros: domínio de ocorrências/acessos
  // ============================================================
  function initOcorrenciasAjax() {
    window.SIOPOcorrencias?.core?.init?.();
  }

  const appInitializers = [
    initAutoDate,
    initDependentSelects,
    initThemeToggle,
    initTiltEffect,
    initCounters,
    initMobileMenu,
    initFormValidation,
    initPasswordToggle,
    initPageTransitions,
    initSettingsTabs,
    initGenericTabs,
    initOcorrenciasAjax,
  ];

  // ============================================================
  // Bootstrap
  // ============================================================
  function initApp() {
    appInitializers.forEach((initializer) => initializer());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp, { once: true });
  } else {
    initApp();
  }
})();
