(function () {
  'use strict';

  const root = window.SIOPShared = window.SIOPShared || {};
  const signaturePad = root.signaturePad = root.signaturePad || {};

  function createSignaturePad(canvas, options) {
    if (!canvas) return null;

    const context = canvas.getContext('2d');
    if (!context) return null;

    const config = options || {};
    const strokeStyle = config.strokeStyle || '#111827';
    const guideLineColor = config.guideLineColor || '#cbd5e1';
    const lineWidth = Number.isFinite(config.lineWidth) ? config.lineWidth : 2;
    const guideLineWidth = Number.isFinite(config.guideLineWidth) ? config.guideLineWidth : 1;

    context.lineJoin = 'round';
    context.lineCap = 'round';
    context.lineWidth = lineWidth;
    context.strokeStyle = strokeStyle;

    let drawing = false;
    let hasStroke = false;

    function drawGuideLine() {
      const guideY = canvas.height / 2;
      context.save();
      context.beginPath();
      context.strokeStyle = guideLineColor;
      context.lineWidth = guideLineWidth;
      context.setLineDash([8, 6]);
      context.moveTo(24, guideY);
      context.lineTo(canvas.width - 24, guideY);
      context.stroke();
      context.restore();
    }

    function getPoint(event) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      if (event.touches && event.touches.length) {
        return {
          x: (event.touches[0].clientX - rect.left) * scaleX,
          y: (event.touches[0].clientY - rect.top) * scaleY,
        };
      }

      return {
        x: (event.clientX - rect.left) * scaleX,
        y: (event.clientY - rect.top) * scaleY,
      };
    }

    function getDataURL() {
      return hasStroke ? canvas.toDataURL('image/png') : '';
    }

    function hasValue() {
      return hasStroke;
    }

    function startDraw(event) {
      event.preventDefault();
      drawing = true;
      const point = getPoint(event);
      context.beginPath();
      context.moveTo(point.x, point.y);
      context.lineTo(point.x + 0.01, point.y + 0.01);
      context.stroke();
      hasStroke = true;
    }

    function moveDraw(event) {
      if (!drawing) return;
      event.preventDefault();
      const point = getPoint(event);
      context.lineTo(point.x, point.y);
      context.stroke();
    }

    function endDraw() {
      drawing = false;
    }

    function clear() {
      context.clearRect(0, 0, canvas.width, canvas.height);
      hasStroke = false;
      drawGuideLine();
    }

    function loadFromDataURL(dataURL) {
      clear();
      const value = String(dataURL || '').trim();
      if (!value) return;

      const image = new Image();
      image.onload = function () {
        context.clearRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        hasStroke = true;
      };
      image.src = value;
    }

    clear();

    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mousemove', moveDraw);
    window.addEventListener('mouseup', endDraw);
    canvas.addEventListener('mouseleave', endDraw);
    canvas.addEventListener('touchstart', startDraw, { passive: false });
    canvas.addEventListener('touchmove', moveDraw, { passive: false });
    canvas.addEventListener('touchend', endDraw);

    return {
      clear,
      getDataURL,
      hasValue,
      loadFromDataURL,
    };
  }

  signaturePad.createSignaturePad = createSignaturePad;
})();
