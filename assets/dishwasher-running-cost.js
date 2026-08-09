(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherRunningCost = api;
  if (root && root.document) api.attach(root.document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var limits = { loads: 50, kwh: 10, electricRate: 5, gallons: 50, waterRate: 500 };

  function calculate(input) {
    if (!input) return null;
    var values = {};
    var valid = Object.keys(limits).every(function (key) {
      values[key] = Number(input[key]);
      return Number.isFinite(values[key]) && values[key] >= 0 && values[key] <= limits[key];
    });
    if (!valid) return null;
    var electricityPerLoad = values.kwh * values.electricRate;
    var waterPerLoad = values.gallons / 1000 * values.waterRate;
    var perLoad = electricityPerLoad + waterPerLoad;
    var annualLoads = values.loads * 52;
    return {
      electricityPerLoad: electricityPerLoad,
      waterPerLoad: waterPerLoad,
      perLoad: perLoad,
      annualLoads: annualLoads,
      annual: perLoad * annualLoads,
      monthly: perLoad * annualLoads / 12,
      annualWater: values.gallons * annualLoads,
      annualKwh: values.kwh * annualLoads
    };
  }

  function money(value, digits) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
  }

  function attach(doc) {
    var form = doc.getElementById('running-cost-form');
    var output = doc.getElementById('running-cost-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var estimate = calculate({ loads: data.get('loads'), kwh: data.get('kwh'), electricRate: data.get('electricRate'), gallons: data.get('gallons'), waterRate: data.get('waterRate') });
      if (!estimate) return;
      output.innerHTML = '<p class="eyebrow">Your estimate</p><h2>' + money(estimate.annual, 2) + ' per year</h2><div class="result-metrics"><div class="mini-stat"><strong>' + money(estimate.perLoad, 2) + '</strong><span>per load</span></div><div class="mini-stat"><strong>' + money(estimate.monthly, 2) + '</strong><span>average month</span></div><div class="mini-stat"><strong>' + money(estimate.annual, 2) + '</strong><span>per year</span></div></div><h3>Annual usage behind the estimate</h3><ul><li>' + Math.round(estimate.annualLoads) + ' loads</li><li>' + estimate.annualKwh.toFixed(1) + ' kWh of electricity</li><li>' + Math.round(estimate.annualWater).toLocaleString('en-US') + ' gallons of water</li></ul><p>Per load, electricity contributes <strong>' + money(estimate.electricityPerLoad, 2) + '</strong> and water/sewer contributes <strong>' + money(estimate.waterPerLoad, 2) + '</strong>.</p><p class="tool-disclaimer">This is an estimate based entirely on the inputs shown above. It is not a utility quote or an appliance efficiency certification.</p>';
      output.hidden = false;
      output.focus();
    });
  }

  return { calculate: calculate, attach: attach };
});
