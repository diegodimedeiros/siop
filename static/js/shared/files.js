(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const files = root.files = root.files || {};

  function rebuildInputFiles(input, selectedFiles) {
    if (!input) return;

    const dataTransfer = new DataTransfer();
    (selectedFiles || []).forEach((file) => dataTransfer.items.add(file));
    input.files = dataTransfer.files;
  }

  function syncFileCounter(counterNode, selectedFiles, labels) {
    if (!counterNode) return;

    const total = (selectedFiles || []).length;
    const singular = labels?.singular || 'item';
    const plural = labels?.plural || `${singular}s`;
    counterNode.textContent = `${total} ${total === 1 ? singular : plural}`;
  }

  function updateFileStatus(inputOrInputs, statusNode, singularLabel, pluralLabel) {
    if (!statusNode) return;

    const inputs = Array.isArray(inputOrInputs) ? inputOrInputs : [inputOrInputs];
    const total = inputs.reduce((sum, input) => sum + (input?.files?.length || 0), 0);

    if (!total) {
      statusNode.textContent = singularLabel === 'foto'
        ? 'Nenhuma foto capturada'
        : 'Nenhum anexo selecionado';
      return;
    }

    if (singularLabel === 'foto') {
      statusNode.textContent = `${total} ${total === 1 ? 'foto adicionada' : 'fotos adicionadas'}`;
      return;
    }

    statusNode.textContent = `${total} ${total === 1 ? singularLabel : pluralLabel} selecionado${total === 1 ? '' : 's'}`;
  }

  function renderFileList(config) {
    const {
      files: selectedFiles,
      listNode,
      emptyNode,
      onRemove,
      itemClass = 'manejo-list-item',
      nameClass = 'manejo-list-name',
      removeClass = 'manejo-list-remove',
      removeText = 'x',
      removeLabelFormatter,
    } = config || {};

    if (!listNode || !emptyNode) return;

    const files = selectedFiles || [];
    listNode.innerHTML = '';
    emptyNode.style.display = files.length ? 'none' : '';

    files.forEach((file, index) => {
      const item = document.createElement('div');
      item.className = itemClass;

      const name = document.createElement('strong');
      name.className = nameClass;
      name.textContent = file.name;

      const removeButton = document.createElement('button');
      removeButton.className = removeClass;
      removeButton.type = 'button';
      removeButton.textContent = removeText;
      removeButton.setAttribute(
        'aria-label',
        typeof removeLabelFormatter === 'function'
          ? removeLabelFormatter(file, index)
          : `Remover ${file.name}`
      );
      if (typeof onRemove === 'function') {
        removeButton.addEventListener('click', () => onRemove(index, file));
      }

      item.appendChild(name);
      item.appendChild(removeButton);
      listNode.appendChild(item);
    });
  }

  files.rebuildInputFiles = rebuildInputFiles;
  files.syncFileCounter = syncFileCounter;
  files.updateFileStatus = updateFileStatus;
  files.renderFileList = renderFileList;
})();
