(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const forms = root.forms = root.forms || {};

  function populateSelect(select, options, placeholder) {
    if (!select) return;

    select.innerHTML = '';

    const base = document.createElement('option');
    base.value = '';
    base.textContent = placeholder || 'Selecione...';
    select.appendChild(base);

    (options || []).forEach((item) => {
      const option = document.createElement('option');
      option.value = item;
      option.textContent = item;
      select.appendChild(option);
    });
  }

  function isTrue(value) {
    return String(value).toLowerCase() === 'true';
  }

  function toggleGroup(group, show, options) {
    if (!group) return;

    const config = options || {};
    const shouldReset = config.reset !== false;
    const fields = group.querySelectorAll('input, select, textarea');

    group.hidden = !show;
    group.style.display = show ? '' : 'none';

    fields.forEach((field) => {
      field.disabled = !show;

      if (!show && shouldReset) {
        if (field.tagName === 'SELECT') {
          field.selectedIndex = 0;
        } else if (field.type === 'checkbox' || field.type === 'radio') {
          field.checked = false;
        } else {
          field.value = '';
        }
        clearFieldError(field);
      }
    });
  }

  function getFieldWrapper(field) {
    return field?.closest('.form-group-settings, .form-group');
  }

  function getFieldErrorNode(field) {
    const wrapper = getFieldWrapper(field);
    if (!wrapper) return null;

    let errorNode = wrapper.querySelector('.field-error-message');
    if (!errorNode) {
      errorNode = document.createElement('div');
      errorNode.className = 'field-error-message';
      errorNode.hidden = true;
      wrapper.appendChild(errorNode);
    }
    return errorNode;
  }

  function clearFieldError(field) {
    if (!field) return;

    field.classList.remove('field-invalid');
    field.removeAttribute('aria-invalid');
    const errorNode = getFieldErrorNode(field);
    if (errorNode) {
      errorNode.textContent = '';
      errorNode.hidden = true;
    }
  }

  function setFieldError(field, message) {
    if (!field) return;

    field.classList.add('field-invalid');
    field.setAttribute('aria-invalid', 'true');
    const errorNode = getFieldErrorNode(field);
    if (errorNode) {
      errorNode.textContent = message || 'Campo invalido.';
      errorNode.hidden = false;
    }
  }

  function getFieldMessage(field) {
    if (!field) return 'Campo invalido.';
    if (field.validity?.valueMissing) return 'Campo obrigatorio.';
    if (field.validity?.typeMismatch) return 'Formato invalido.';
    if (field.validity?.tooShort) return 'Valor menor que o permitido.';
    if (field.validity?.tooLong) return 'Valor maior que o permitido.';
    if (field.validity?.patternMismatch) return 'Formato invalido.';
    if (field.validity?.rangeUnderflow || field.validity?.rangeOverflow) return 'Valor fora do intervalo permitido.';
    if (field.validationMessage) return field.validationMessage;
    return 'Campo invalido.';
  }

  function attachConstraintValidation(form) {
    if (!form || form.dataset.constraintValidationBound === '1') return;
    form.dataset.constraintValidationBound = '1';

    form.addEventListener('invalid', (event) => {
      const field = event.target;
      if (!(field instanceof HTMLElement)) return;
      setFieldError(field, getFieldMessage(field));
    }, true);

    form.addEventListener('input', (event) => {
      const field = event.target;
      if (!(field instanceof HTMLElement)) return;
      if (field.validity?.valid) {
        clearFieldError(field);
      }
    }, true);

    form.addEventListener('change', (event) => {
      const field = event.target;
      if (!(field instanceof HTMLElement)) return;
      if (field.validity?.valid) {
        clearFieldError(field);
      }
    }, true);

    form.addEventListener('reset', () => {
      window.setTimeout(() => {
        form.querySelectorAll('.field-invalid').forEach((field) => {
          clearFieldError(field);
        });
      }, 0);
    });
  }

  forms.populateSelect = populateSelect;
  forms.isTrue = isTrue;
  forms.toggleGroup = toggleGroup;
  forms.attachConstraintValidation = attachConstraintValidation;
  forms.setFieldError = setFieldError;
  forms.clearFieldError = clearFieldError;
})();
