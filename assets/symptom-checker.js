(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherSymptomChecker = api;
  if (root && root.document) api.attach(root.document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var plans = {
    water: { title: 'Start with the drain path', steps: ['Turn off power and compare the water level with the normal shallow water around the filter area.', 'Remove and rinse the filter according to the owner’s manual.', 'Check the visible drain hose and sink air gap for a kink or fresh blockage.', 'If a garbage disposal was just installed, confirm its dishwasher inlet knockout was removed.'], href: '../../articles/dishwasher-standing-water-after-cycle/', link: 'Open the complete standing-water guide' },
    smell: { title: 'Start with trapped soil and drainage', steps: ['Clean the filter and wipe the door gasket.', 'Inspect the sump area for labels, glass, or food debris without reaching into hidden components.', 'Run the manufacturer-recommended cleaning cycle.', 'A sewage odor that returns quickly may point to a drain-hose or plumbing connection problem.'], href: '../../articles/dishwasher-smells-bad-after-wash/', link: 'Open the bad-smell troubleshooting guide' },
    drying: { title: 'Check settings, rinse aid, and loading', steps: ['Confirm the selected cycle includes heated drying or an equivalent option.', 'Refill rinse aid if your model uses it.', 'Leave space between plastics and angle items so water can drain.', 'If every load is cold at the end, stop troubleshooting and arrange service.'], href: '../../articles/dishwasher-not-drying-dishes-completely/', link: 'Open the drying troubleshooting guide' },
    residue: { title: 'Separate mineral film from food residue', steps: ['Check your local water hardness or a recent water report.', 'Confirm rinse aid is filled and use only dishwasher detergent.', 'Clean the filter and spray-arm openings.', 'Use the detergent and softener settings specified for your model and water hardness.'], href: '../../articles/dishwasher-white-residue-on-dishes/', link: 'Open the white-residue guide' },
    start: { title: 'Rule out controls and the power source', steps: ['Confirm the door is fully latched and racks are not blocking it.', 'Check control lock, delay start, and sleep settings.', 'Check the household breaker once; do not repeatedly reset a breaker that trips again.', 'If power is present but the controls remain dead, arrange qualified service.'], href: '../../articles/dishwasher-wont-start-or-turn-on/', link: 'Open the no-start guide' },
    leak: { title: 'Stop the cycle and locate the visible source', steps: ['Stop the cycle and shut off the dishwasher water supply if leaking continues.', 'Wipe up water promptly to protect flooring.', 'Check for excess suds, an item blocking the door, and a dirty or folded gasket.', 'Leaks below the machine or behind cabinets require professional service.'], href: '../../articles/dishwasher-leaking-water-from-door/', link: 'Open the door-leak guide' }
  };
  var allowed = { timing: ['sudden', 'gradual', 'install'], filter: ['unknown', 'no', 'yes'], noise: ['no', 'yes'], hazard: ['no', 'yes'] };

  function buildPlan(input) {
    if (!input || !plans[input.symptom] || !Object.keys(allowed).every(function (key) { return allowed[key].indexOf(input[key]) !== -1; })) return null;
    if (input.hazard === 'yes') return { hazard: true, title: 'Disconnect power and do not run another cycle', explanation: 'Active leaking, smoke, a burning smell, or a breaker that trips can create fire, shock, and water-damage risks. Shut off power at the breaker, close the water supply if it is safe to reach, and contact a qualified appliance technician. For smoke or fire, leave the area and contact emergency services.' };
    var extra = [];
    if (input.filter !== 'yes') extra.push('Because the filter has not been confirmed clean, make that your first maintenance check.');
    if (input.timing === 'install') extra.push('Because this began after installation or sink work, recheck the visible drain-hose route, air gap, and disposal connection.');
    if (input.noise === 'yes') extra.push('A new grinding or persistent humming noise raises the chance of an obstruction or component fault. Stop if the noise continues after visible debris is removed.');
    return { hazard: false, title: plans[input.symptom].title, steps: plans[input.symptom].steps.slice(), href: plans[input.symptom].href, link: plans[input.symptom].link, extra: extra };
  }

  function escapeText(value) { return String(value).replace(/[&<>"']/g, function (char) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]; }); }

  function attach(doc) {
    var form = doc.getElementById('symptom-form');
    var output = doc.getElementById('tool-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var plan = buildPlan({ symptom: data.get('symptom'), timing: data.get('timing'), filter: data.get('filter'), noise: data.get('noise'), hazard: data.get('hazard') });
      if (!plan) return;
      if (plan.hazard) {
        output.className = 'surface-card tool-result warning-card';
        output.innerHTML = '<p class="eyebrow">Stop here</p><h2>' + escapeText(plan.title) + '</h2><p>' + escapeText(plan.explanation) + '</p>';
      } else {
        output.className = 'surface-card tool-result';
        output.innerHTML = '<p class="eyebrow">Your prioritized plan</p><h2>' + escapeText(plan.title) + '</h2>' + (plan.extra.length ? '<div class="pro-note"><strong>Based on your answers</strong><ul>' + plan.extra.map(function (item) { return '<li>' + escapeText(item) + '</li>'; }).join('') + '</ul></div>' : '') + '<ol class="numbered-list">' + plan.steps.map(function (step) { return '<li>' + escapeText(step) + '</li>'; }).join('') + '</ol><p><a class="pill-button primary-button" href="' + plan.href + '">' + escapeText(plan.link) + '</a></p><p class="tool-disclaimer">This is educational guidance, not a diagnosis. Stop if a step conflicts with your manual or requires removing service panels.</p>';
      }
      output.hidden = false;
      output.focus();
    });
  }

  return { buildPlan: buildPlan, attach: attach };
});
