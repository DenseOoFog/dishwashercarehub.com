(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherResultActions = api;
  if (root && root.document) api.attach(root.document, root);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function normalizeText(value) {
    return String(value || '')
      .replace(/\r/g, '')
      .split('\n')
      .map(function (line) { return line.trim().replace(/[ \t]+/g, ' '); })
      .filter(Boolean)
      .join('\n');
  }

  function resultText(output) {
    var clone = output.cloneNode(true);
    Array.prototype.forEach.call(
      clone.querySelectorAll('.tool-result-actions, .print-actions'),
      function (item) { item.remove(); }
    );
    return normalizeText(clone.innerText || clone.textContent);
  }

  function fallbackCopy(text, doc) {
    var field = doc.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    doc.body.appendChild(field);
    field.select();
    var copied = Boolean(doc.execCommand && doc.execCommand('copy'));
    field.remove();
    return copied;
  }

  function writeText(text, browser, doc) {
    if (browser.navigator && browser.navigator.clipboard && browser.navigator.clipboard.writeText) {
      return browser.navigator.clipboard.writeText(text).then(function () { return true; });
    }
    return Promise.resolve(fallbackCopy(text, doc));
  }

  function ensureActions(output, doc) {
    if (output.hidden || output.querySelector('.tool-result-actions')) return;
    var actions = doc.createElement('div');
    actions.className = 'hero-actions print-actions tool-result-actions';
    actions.innerHTML = '<button type="button" class="pill-button secondary-button" data-copy-result>Copy result</button>' +
      (output.querySelector('[data-print-plan]') ? '' : '<button type="button" class="pill-button secondary-button" data-print-result>Print result</button>') +
      '<p class="tool-action-status" role="status" aria-live="polite"></p>';
    output.appendChild(actions);
  }

  function attach(doc, browser) {
    var outputs = doc.querySelectorAll('.tool-result[id]');
    Array.prototype.forEach.call(outputs, function (output) {
      if (output.dataset.resultActionsAttached === 'true') return;
      output.dataset.resultActionsAttached = 'true';
      output.addEventListener('click', function (event) {
        var copyButton = event.target.closest('[data-copy-result]');
        var printButton = event.target.closest('[data-print-result]');
        if (printButton) {
          browser.print();
          return;
        }
        if (!copyButton) return;
        var status = output.querySelector('.tool-action-status');
        var text = resultText(output);
        writeText(text, browser, doc).then(function (copied) {
          status.textContent = copied ? 'Result copied to your clipboard.' : 'Copy was unavailable in this browser.';
        }).catch(function () {
          status.textContent = 'Copy was unavailable in this browser.';
        });
      });
      ensureActions(output, doc);
      if (browser.MutationObserver) {
        new browser.MutationObserver(function () { ensureActions(output, doc); })
          .observe(output, { childList: true, attributes: true, attributeFilter: ['hidden'] });
      }
    });
  }

  return {
    normalizeText: normalizeText,
    resultText: resultText,
    fallbackCopy: fallbackCopy,
    writeText: writeText,
    ensureActions: ensureActions,
    attach: attach
  };
});
