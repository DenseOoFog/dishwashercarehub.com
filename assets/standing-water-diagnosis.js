(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.StandingWaterDiagnosis = api;
  if (root && root.document) api.attach(root.document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var valid = {
    amount: ['floor', 'sump', 'overflow'],
    timing: ['after', 'returns', 'morning'],
    sink: ['normal', 'slow', 'unknown'],
    disposal: ['no', 'yes', 'none'],
    airgap: ['no', 'yes', 'none'],
    sound: ['normal', 'hum', 'silent', 'unknown'],
    filter: ['no', 'yes', 'fixed']
  };

  var paths = {
    normal: { label: 'Likely normal retained sump water', text: 'A small amount below the visible filter surface can be normal. Compare it with the model manual and watch for a rising level, odor, or dirty water across the tub floor before treating it as a clog.', href: '../../articles/standing-water-in-dishwasher-filter-area/', link: 'Understand water around the filter area' },
    filter: { label: 'Start with the filter and filter well', text: 'Food soil, labels, grease, and small fragments can slow the first part of the drain path. Disconnect power, remove standing water safely, and clean only the removable parts described in the owner’s manual.', href: '../../articles/how-to-clean-dishwasher-filter/', link: 'Follow the filter-cleaning guide' },
    disposal: { label: 'Recheck the new disposal connection', text: 'A new garbage disposal may still have its dishwasher-inlet knockout in place, or the hose may have been reconnected with a kink. Do not strike or remove anything until you have confirmed the disposal manufacturer’s instructions.', href: '../../articles/dishwasher-not-draining-after-garbage-disposal-replaced/', link: 'Check the disposal connection safely' },
    airgap: { label: 'The air gap or downstream drain is restricted', text: 'Water spilling from a sink-top air gap means the dishwasher is pushing water out, but the route from the air gap toward the disposal or drain is restricted. Stop repeated cycles until the visible connection is checked.', href: '../../articles/dishwasher-air-gap-overflowing/', link: 'Open the air-gap overflow guide' },
    sink: { label: 'Treat this as a shared plumbing-path problem first', text: 'A slow or gurgling sink can prevent the dishwasher from emptying. The dishwasher may be working while the shared drain path is backed up. Avoid chemical drain cleaners that conflict with appliance or plumbing instructions.', href: '../../articles/dishwasher-drains-into-sink-when-running/', link: 'Review sink-side drainage clues' },
    backflow: { label: 'Water may be returning through the drain path', text: 'If the tub empties and later refills, inspect the visible hose routing, high loop, air gap, disposal connection, and sink backup. That pattern is different from a pump that never drains.', href: '../../articles/dishwasher-drains-then-fills-back-up/', link: 'Diagnose water that returns' },
    obstruction: { label: 'Stop if the new noise persists', text: 'A persistent hum or grinding sound together with standing water can indicate an obstruction or component fault. Remove only visible debris after disconnecting power. Do not open the pump, base, or wiring compartments.', href: '../../articles/dishwasher-making-grinding-noise/', link: 'Review grinding-noise safety checks' },
    service: { label: 'The next useful check likely requires service', text: 'With a clean filter, normal sink, and no drain sound, the remaining possibilities include the drain pump, control, wiring, or a concealed restriction. Those checks require electrical testing or disassembly.', href: '../../articles/dishwasher-wont-drain-completely/', link: 'See when a drain failure needs service' },
    hazard: { label: 'Stop the cycle and protect the area', text: 'Water close to overflowing or leaking outside the machine can damage flooring and create electrical risk. Disconnect power, close the water supply if it is safe to reach, and arrange qualified service.', href: '../../articles/dishwasher-leaking-water-from-door/', link: 'Review immediate leak precautions' },
    hose: { label: 'Inspect the visible drain-hose route next', text: 'A clean filter with a normal sink shifts attention to the visible hose route. Look for a fresh kink, a low sag that encourages backflow, or a connection disturbed during cabinet or sink work.', href: '../../articles/dishwasher-drain-hose-clogged-symptoms/', link: 'Check drain-hose symptoms' }
  };

  function isValid(config) {
    return config && Object.keys(valid).every(function (key) {
      return valid[key].indexOf(config[key]) !== -1;
    });
  }

  function diagnose(config) {
    if (!isValid(config)) return null;
    if (config.amount === 'overflow') return paths.hazard;
    if (config.filter === 'fixed') return paths.normal;
    if (config.amount === 'sump' && config.timing === 'after') return paths.normal;
    if (config.disposal === 'yes') return paths.disposal;
    if (config.airgap === 'yes') return paths.airgap;
    if (config.sink === 'slow') return paths.sink;
    if (config.timing === 'returns' || config.timing === 'morning') return paths.backflow;
    if (config.filter === 'no') return paths.filter;
    if (config.sound === 'hum') return paths.obstruction;
    if (config.sound === 'silent') return paths.service;
    return paths.hose;
  }

  function escapeText(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char];
    });
  }

  function attach(doc) {
    var form = doc.getElementById('water-form');
    var output = doc.getElementById('water-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var diagnosis = diagnose({ amount: data.get('amount'), timing: data.get('timing'), sink: data.get('sink'), disposal: data.get('disposal'), airgap: data.get('airgap'), sound: data.get('sound'), filter: data.get('filter') });
      if (!diagnosis) return;
      output.className = 'surface-card tool-result' + (diagnosis === paths.hazard ? ' warning-card' : '');
      output.innerHTML = '<p class="eyebrow">Most useful next path</p><h2>' + escapeText(diagnosis.label) + '</h2><p>' + escapeText(diagnosis.text) + '</p><p><a class="pill-button primary-button" href="' + diagnosis.href + '">' + escapeText(diagnosis.link) + '</a></p><p class="tool-disclaimer">This result is based on observable patterns, not a component diagnosis. Model-specific instructions always take priority.</p>';
      output.hidden = false;
      output.focus();
    });
  }

  return { diagnose: diagnose, attach: attach };
});
