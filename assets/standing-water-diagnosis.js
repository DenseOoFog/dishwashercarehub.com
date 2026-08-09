(function () {
  var form = document.getElementById('water-form');
  var result = document.getElementById('water-result');
  if (!form || !result) return;

  var paths = {
    normal: {
      label: 'Likely normal retained sump water',
      text: 'A small amount below the visible filter surface can be normal. Compare it with the model manual and watch for a rising level, odor, or dirty water across the tub floor before treating it as a clog.',
      href: '../../articles/standing-water-in-dishwasher-filter-area/',
      link: 'Understand water around the filter area'
    },
    filter: {
      label: 'Start with the filter and filter well',
      text: 'Food soil, labels, grease, and small fragments commonly slow the first part of the drain path. Disconnect power, remove standing water safely, and clean only the removable parts described in the owner’s manual.',
      href: '../../articles/how-to-clean-dishwasher-filter/',
      link: 'Follow the filter-cleaning guide'
    },
    disposal: {
      label: 'Recheck the new disposal connection',
      text: 'A new garbage disposal often still has its dishwasher-inlet knockout in place, or the hose was reconnected with a kink. Do not strike or remove anything until you have confirmed the disposal manufacturer’s instructions.',
      href: '../../articles/dishwasher-not-draining-after-garbage-disposal-replaced/',
      link: 'Check the disposal connection safely'
    },
    airgap: {
      label: 'The air gap or downstream drain is restricted',
      text: 'Water spilling from a sink-top air gap means the dishwasher is pushing water out, but the route from the air gap toward the disposal or drain is restricted. Stop repeated cycles until the visible connection is cleared.',
      href: '../../articles/dishwasher-air-gap-overflowing/',
      link: 'Open the air-gap overflow guide'
    },
    sink: {
      label: 'Treat this as a shared plumbing-path problem first',
      text: 'A slow or gurgling sink can prevent the dishwasher from emptying. The dishwasher may be working while the shared drain path is backed up. Avoid chemical drain cleaners that conflict with appliance or plumbing instructions.',
      href: '../../articles/dishwasher-drains-into-sink-when-running/',
      link: 'Review sink-side drainage clues'
    },
    backflow: {
      label: 'Water is likely returning through the drain path',
      text: 'If the tub empties and later refills, inspect the visible hose routing, high loop, air gap, disposal connection, and sink backup. That pattern is different from a pump that never drains.',
      href: '../../articles/dishwasher-drains-then-fills-back-up/',
      link: 'Diagnose water that returns'
    },
    obstruction: {
      label: 'Stop if the new noise persists',
      text: 'A persistent hum or grinding sound can mean debris near the pump or a failing component. Remove only visible debris after disconnecting power. Do not open the pump, base, or wiring compartments.',
      href: '../../articles/dishwasher-making-grinding-noise/',
      link: 'Review grinding-noise safety checks'
    },
    service: {
      label: 'The next useful check likely requires service',
      text: 'With a clean filter, normal sink, and no drain sound, the remaining possibilities include the drain pump, control, wiring, or a concealed restriction. Those checks require electrical testing or disassembly.',
      href: '../../articles/dishwasher-drain-not-working-after-cycle/',
      link: 'See when a drain failure needs service'
    },
    hazard: {
      label: 'Stop the cycle and protect the area',
      text: 'Water close to overflowing or leaking outside the machine can damage flooring and create electrical risk. Disconnect power, close the water supply if it is safe to reach, and arrange qualified service.',
      href: '../../articles/dishwasher-leaking-water-from-door/',
      link: 'Review immediate leak precautions'
    },
    hose: {
      label: 'Inspect the visible drain-hose route next',
      text: 'A clean filter with a normal sink shifts attention to the visible hose route. Look for a fresh kink, a low sag that encourages backflow, or a connection disturbed during cabinet or sink work.',
      href: '../../articles/dishwasher-drain-hose-clogged-symptoms/',
      link: 'Check drain-hose symptoms'
    }
  };

  function choose(data) {
    if (data.get('amount') === 'overflow') return 'hazard';
    if (data.get('filter') === 'fixed') return 'normal';
    if (data.get('amount') === 'sump' && data.get('timing') === 'after') return 'normal';
    if (data.get('disposal') === 'yes') return 'disposal';
    if (data.get('airgap') === 'yes') return 'airgap';
    if (data.get('sink') === 'slow') return 'sink';
    if (data.get('timing') === 'returns' || data.get('timing') === 'morning') return 'backflow';
    if (data.get('filter') === 'no') return 'filter';
    if (data.get('sound') === 'hum') return 'obstruction';
    if (data.get('sound') === 'silent') return 'service';
    return 'hose';
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var key = choose(data);
    var path = paths[key];
    result.className = 'surface-card tool-result' + (key === 'hazard' ? ' warning-card' : '');
    result.innerHTML = '<p class="eyebrow">Most useful next path</p><h2>' + path.label + '</h2><p>' + path.text + '</p><p><a class="pill-button primary-button" href="' + path.href + '">' + path.link + '</a></p><p class="tool-disclaimer">This result is based on observable patterns, not a component diagnosis. Model-specific instructions always take priority.</p>';
    result.hidden = false;
    result.focus();
  });
})();
