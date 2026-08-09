(function () {
  var form = document.getElementById('symptom-form');
  var result = document.getElementById('tool-result');
  if (!form || !result) return;

  var plans = {
    water: {
      title: 'Start with the drain path',
      steps: ['Turn off power and compare the water level with the normal shallow water around the filter area.', 'Remove and rinse the filter according to the owner’s manual.', 'Check the visible drain hose and sink air gap for a kink or fresh blockage.', 'If a garbage disposal was just installed, confirm its dishwasher inlet knockout was removed.'],
      href: '../../articles/dishwasher-standing-water-after-cycle/',
      link: 'Open the complete standing-water guide'
    },
    smell: {
      title: 'Start with trapped soil and drainage',
      steps: ['Clean the filter and wipe the door gasket.', 'Inspect the sump area for labels, glass, or food debris without reaching into hidden components.', 'Run the manufacturer-recommended cleaning cycle.', 'A sewage odor that returns quickly may point to a drain-hose or plumbing connection problem.'],
      href: '../../articles/dishwasher-smells-bad-after-wash/',
      link: 'Open the bad-smell troubleshooting guide'
    },
    drying: {
      title: 'Check settings, rinse aid, and loading',
      steps: ['Confirm the selected cycle includes heated drying or an equivalent option.', 'Refill rinse aid if your model uses it.', 'Leave space between plastics and angle items so water can drain.', 'If every load is cold at the end, stop troubleshooting and arrange service.'],
      href: '../../articles/dishwasher-not-drying-dishes-completely/',
      link: 'Open the drying troubleshooting guide'
    },
    residue: {
      title: 'Separate mineral film from food residue',
      steps: ['Check your local water hardness or a recent water report.', 'Confirm rinse aid is filled and use only dishwasher detergent.', 'Clean the filter and spray-arm openings.', 'Use the detergent and softener settings specified for your model and water hardness.'],
      href: '../../articles/dishwasher-white-residue-on-dishes/',
      link: 'Open the white-residue guide'
    },
    start: {
      title: 'Rule out controls and the power source',
      steps: ['Confirm the door is fully latched and racks are not blocking it.', 'Check control lock, delay start, and sleep settings.', 'Check the household breaker once; do not repeatedly reset a breaker that trips again.', 'If power is present but the controls remain dead, arrange qualified service.'],
      href: '../../articles/dishwasher-wont-start-or-turn-on/',
      link: 'Open the no-start guide'
    },
    leak: {
      title: 'Stop the cycle and locate the visible source',
      steps: ['Stop the cycle and shut off the dishwasher water supply if leaking continues.', 'Wipe up water promptly to protect flooring.', 'Check for excess suds, an item blocking the door, and a dirty or folded gasket.', 'Leaks below the machine or behind cabinets require professional service.'],
      href: '../../articles/dishwasher-leaking-water-from-door/',
      link: 'Open the door-leak guide'
    }
  };

  function escapeText(value) {
    return String(value).replace(/[&<>"']/g, function (char) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]; });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var plan = plans[data.get('symptom')];
    if (!plan) return;
    if (data.get('hazard') === 'yes') {
      result.className = 'surface-card tool-result warning-card';
      result.innerHTML = '<p class="eyebrow">Stop here</p><h2>Disconnect power and do not run another cycle</h2><p>Active leaking, smoke, a burning smell, or a breaker that trips can create fire, shock, and water-damage risks. Shut off power at the breaker, close the water supply if it is safe to reach, and contact a qualified appliance technician. For smoke or fire, leave the area and contact emergency services.</p>';
    } else {
      var extra = [];
      if (data.get('filter') !== 'yes') extra.push('Because the filter has not been confirmed clean, make that your first maintenance check.');
      if (data.get('timing') === 'install') extra.push('Because this began after installation or sink work, recheck the visible drain-hose route, air gap, and disposal connection.');
      if (data.get('noise') === 'yes') extra.push('A new grinding or persistent humming noise raises the chance of an obstruction or component fault. Stop if the noise continues after visible debris is removed.');
      result.className = 'surface-card tool-result';
      result.innerHTML = '<p class="eyebrow">Your prioritized plan</p><h2>' + escapeText(plan.title) + '</h2>' + (extra.length ? '<div class="pro-note"><strong>Based on your answers</strong><ul>' + extra.map(function (x) { return '<li>' + escapeText(x) + '</li>'; }).join('') + '</ul></div>' : '') + '<ol class="numbered-list">' + plan.steps.map(function (step) { return '<li>' + escapeText(step) + '</li>'; }).join('') + '</ol><p><a class="pill-button primary-button" href="' + plan.href + '">' + escapeText(plan.link) + '</a></p><p class="tool-disclaimer">This is educational guidance, not a diagnosis. Stop if a step conflicts with your manual or requires removing service panels.</p>';
    }
    result.hidden = false;
    result.focus();
  });
})();
