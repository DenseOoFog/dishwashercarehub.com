(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherWaterHardness = api;
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', api.init);
    else api.init();
  }
})(typeof window !== 'undefined' ? window : null, function () {
  var MG_PER_UNIT = {
    mgl: 1,
    gpg: 17.12,
    dh: 17.848,
    fh: 10,
    clark: 14.254,
    mmol: 100.0869
  };

  function toMgL(value, unit) {
    var numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric < 0 || !MG_PER_UNIT[unit]) return null;
    return numeric * MG_PER_UNIT[unit];
  }

  function classify(mgL) {
    if (!Number.isFinite(mgL) || mgL < 0) return null;
    if (mgL <= 60) return { key: 'soft', label: 'Soft', range: '0–60 mg/L as CaCO₃' };
    if (mgL <= 120) return { key: 'moderate', label: 'Moderately hard', range: '61–120 mg/L as CaCO₃' };
    if (mgL <= 180) return { key: 'hard', label: 'Hard', range: '121–180 mg/L as CaCO₃' };
    return { key: 'very-hard', label: 'Very hard', range: 'More than 180 mg/L as CaCO₃' };
  }

  function calculate(value, unit) {
    var mgL = toMgL(value, unit);
    if (mgL === null || mgL > 10000) return null;
    return {
      mgL: mgL,
      ppm: mgL,
      gpg: mgL / MG_PER_UNIT.gpg,
      dh: mgL / MG_PER_UNIT.dh,
      fh: mgL / MG_PER_UNIT.fh,
      clark: mgL / MG_PER_UNIT.clark,
      mmol: mgL / MG_PER_UNIT.mmol,
      classification: classify(mgL)
    };
  }

  function advice(result, symptom) {
    var items = [];
    var level = result.classification.key;
    if (level === 'soft') {
      items.push('Use the low or soft-water guidance on the detergent label and in your owner’s manual; excess detergent in soft water can contribute to filming or glass damage.');
      items.push('Do not increase a built-in softener setting or add dishwasher salt unless your model manual calls for it.');
    } else if (level === 'moderate') {
      items.push('Start with the factory rinse-aid and water-hardness settings, then compare them with the table in your model’s manual.');
      items.push('Use the detergent package amount for this hardness range and change only one setting at a time.');
    } else if (level === 'hard') {
      items.push('Check whether your model has a programmable water-softening or salt system and set it from the model-specific hardness table.');
      items.push('Keep dishwasher rinse aid filled if the manufacturer recommends it, then adjust only one level at a time for persistent spots.');
    } else {
      items.push('Very hard water raises the chance of scale and white mineral film. Check the model’s water-hardness table, dishwasher-salt system, and rinse-aid instructions before changing detergent.');
      items.push('At 15 gpg or more, some manufacturer guidance recommends water softening to protect performance; confirm the threshold for your exact model.');
    }
    if (symptom === 'white-film') {
      items.push('For removable white film, compare detergent amount, rinse aid, filter condition, and water-softener settings before assuming a failed part.');
    } else if (symptom === 'spots') {
      items.push('For water spots, confirm the rinse-aid reservoir is filled and use the manual’s adjustment sequence rather than making a large jump.');
    } else if (symptom === 'streaks') {
      items.push('For colored or rainbow streaks, manufacturer guidance often points to excess rinse aid; lower only as your manual directs.');
    } else if (symptom === 'poor-cleaning') {
      items.push('For poor cleaning, also check loading, filter condition, spray-arm movement, cycle choice, and incoming water temperature.');
    }
    return items;
  }

  function format(value, digits) {
    return Number(value).toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    });
  }

  function init() {
    var form = document.getElementById('hardness-form');
    var output = document.getElementById('hardness-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var result = calculate(data.get('hardness'), data.get('unit'));
      if (!result) {
        output.className = 'surface-card tool-result warning-card';
        output.innerHTML = '<h2>Enter a valid hardness result</h2><p>Use a number from 0 to 10,000 after confirming the unit on your water report or test strip.</p>';
      } else {
        var tips = advice(result, data.get('symptom'));
        output.className = 'surface-card tool-result';
        output.innerHTML =
          '<p class="eyebrow">Converted result</p>' +
          '<h2>' + result.classification.label + ' water</h2>' +
          '<p>' + result.classification.range + ', using the U.S. Geological Survey classification.</p>' +
          '<div class="result-metrics">' +
            '<div class="mini-stat"><strong>' + format(result.mgL, 1) + '</strong><span>mg/L as CaCO₃ (≈ ppm)</span></div>' +
            '<div class="mini-stat"><strong>' + format(result.gpg, 2) + '</strong><span>grains per U.S. gallon</span></div>' +
            '<div class="mini-stat"><strong>' + format(result.dh, 2) + '</strong><span>German degrees (°dH)</span></div>' +
            '<div class="mini-stat"><strong>' + format(result.fh, 2) + '</strong><span>French degrees (°fH)</span></div>' +
            '<div class="mini-stat"><strong>' + format(result.clark, 2) + '</strong><span>Clark degrees (°e)</span></div>' +
            '<div class="mini-stat"><strong>' + format(result.mmol, 2) + '</strong><span>mmol/L as CaCO₃</span></div>' +
          '</div>' +
          '<h3>Dishwasher setup checklist</h3><ul>' + tips.map(function (tip) { return '<li>' + tip + '</li>'; }).join('') + '</ul>' +
          '<p class="tool-disclaimer">This converts a reported hardness value; it does not test your water. Model-specific owner documentation and product labels control exact salt, rinse-aid, and detergent settings.</p>';
      }
      output.hidden = false;
      output.focus();
    });
  }

  return { MG_PER_UNIT: MG_PER_UNIT, toMgL: toMgL, classify: classify, calculate: calculate, advice: advice, init: init };
});
