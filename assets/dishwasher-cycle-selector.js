(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherCycleSelector = api;
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', api.init);
    else api.init();
  }
})(typeof window !== 'undefined' ? window : null, function () {
  var VALID = {
    soil: ['light', 'normal', 'mixed', 'heavy'],
    load: ['everyday', 'cookware', 'delicate', 'plastic', 'hold'],
    priority: ['balanced', 'fast', 'efficiency', 'drying', 'sanitize'],
    sensor: ['yes', 'no', 'unknown']
  };

  function includes(list, value) { return list.indexOf(value) >= 0; }

  function selectCycle(input) {
    input = input || {};
    if (!includes(VALID.soil, input.soil) || !includes(VALID.load, input.load) ||
        !includes(VALID.priority, input.priority) || !includes(VALID.sensor, input.sensor)) return null;

    var result = { primary: '', alternate: '', why: '', checks: [], avoid: [] };
    if (input.load === 'hold') {
      result.primary = 'Rinse Only / Pre-Rinse';
      result.alternate = 'Wait and run Normal when you have a full load';
      result.why = 'You want to keep food from drying on before a later full wash, not clean and dry the load now.';
      result.checks.push('Use no detergent unless the exact owner manual says otherwise for this rinse program.');
      result.avoid.push('Do not treat Rinse Only as a finished wash or sanitizing cycle.');
      return result;
    }

    if (input.load === 'delicate') {
      result.primary = 'Delicate / China / Crystal';
      result.alternate = 'Hand wash if the item or dishwasher manual does not approve machine washing';
      result.why = 'A model-approved delicate cycle generally uses gentler wash action and less heat than a standard cycle.';
      result.checks.push('Confirm every item is marked dishwasher-safe and follow its rack-placement instructions.');
      result.avoid.push('Skip Sanitize, High Temp, and heated-dry options unless both the item and appliance instructions allow them.');
    } else if (input.soil === 'heavy' || input.load === 'cookware') {
      result.primary = 'Heavy / Pots & Pans';
      result.alternate = input.sensor === 'yes' ? 'Auto / Sensor for a mixed load without baked-on soil' : 'Normal after soaking only as the cookware maker permits';
      result.why = 'Heavy programs are designed for dried-on, baked-on, or greasy soil and usually run longer or more vigorously.';
      result.checks.push('Scrape large debris and verify the cookware is dishwasher-safe before loading.');
      result.avoid.push('Do not use Quick for baked-on soil simply to shorten the displayed time.');
    } else if (input.soil === 'mixed' && input.sensor === 'yes') {
      result.primary = 'Auto / Sensor';
      result.alternate = 'Normal for an ordinary mixed tableware load';
      result.why = 'A soil-sensing program can adjust time, water, or energy after evaluating the wash water.';
      result.checks.push('Keep the filter clean so recirculated debris does not distort performance.');
    } else if (input.priority === 'fast' && input.soil === 'light' && input.load === 'everyday') {
      result.primary = 'Quick / 1-Hour Wash';
      result.alternate = 'Normal when speed is no longer the main constraint';
      result.why = 'Quick programs target lightly soiled essentials when turnaround matters more than maximum efficiency.';
      result.checks.push('Check whether drying is included; some quick programs leave items wetter unless an option is added.');
      result.avoid.push('A shorter label does not guarantee lower water or energy use.');
    } else if (input.priority === 'efficiency' && input.soil === 'light') {
      result.primary = 'Eco / Light';
      result.alternate = 'Normal with heated dry off, if the manual identifies that as the efficient choice';
      result.why = 'A light or energy-saving program can suit lightly soiled loads when time is flexible.';
      result.checks.push('Expect some efficient cycles to run longer while using less heat or water.');
    } else {
      result.primary = 'Normal';
      result.alternate = input.sensor === 'yes' && input.soil === 'mixed' ? 'Auto / Sensor' : 'Light for genuinely light soil';
      result.why = 'Normal is the general starting point for a full, everyday load with typical soil.';
      result.checks.push('Use the cycle table in your exact manual because names and included drying options vary.');
    }

    if (input.load === 'plastic') {
      result.checks.push('Load only dishwasher-safe plastic in the manufacturer-approved rack position, commonly away from exposed heating elements.');
      if (input.priority === 'drying') result.checks.push('Use the model-approved plastic or extended-dry option; plastic naturally retains less heat than glass or ceramic.');
    }
    if (input.priority === 'drying') result.checks.push('Fill rinse aid if recommended and choose the model-approved dry option; this can add time and energy.');
    if (input.priority === 'sanitize') {
      result.checks.push('Add Sanitize only when your model offers it, the items tolerate it, and the cycle/option combination is approved in the manual.');
      result.avoid.push('A household dishwasher sanitize option is not a substitute for medical sterilization.');
    }
    if (input.priority === 'fast' && result.primary !== 'Quick / 1-Hour Wash') {
      result.checks.push('The load needs a stronger or gentler program than Quick; plan around the longer cycle instead of sacrificing the match.');
    }
    return result;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character];
    });
  }

  function init() {
    var form = document.getElementById('cycle-selector-form');
    var output = document.getElementById('cycle-selector-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var result = selectCycle({ soil: data.get('soil'), load: data.get('load'), priority: data.get('priority'), sensor: data.get('sensor') });
      if (!result) {
        output.className = 'surface-card tool-result warning-card';
        output.innerHTML = '<h2>Choose one answer in every field</h2><p>No cycle recommendation was generated because an answer is missing or invalid.</p>';
      } else {
        output.className = 'surface-card tool-result';
        output.innerHTML = '<p class="eyebrow">Best general match</p><h2>' + escapeHtml(result.primary) + '</h2>' +
          '<p>' + escapeHtml(result.why) + '</p><h3>Reasonable alternative</h3><p>' + escapeHtml(result.alternate) + '</p>' +
          '<h3>Before you press Start</h3><ul>' + result.checks.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>' +
          (result.avoid.length ? '<h3>Avoid this mismatch</h3><ul>' + result.avoid.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>' : '') +
          '<p class="tool-disclaimer">Cycle names, temperatures, duration, energy use, and included drying vary by model. Your appliance and dishware instructions override this general selector.</p>';
      }
      output.hidden = false;
      output.focus();
    });
  }

  return { VALID: VALID, selectCycle: selectCycle, init: init };
});
