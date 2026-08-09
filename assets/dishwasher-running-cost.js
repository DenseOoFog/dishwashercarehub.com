(function () {
  var form = document.getElementById('running-cost-form');
  var result = document.getElementById('running-cost-result');
  if (!form || !result) return;

  function money(value, digits) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    }).format(value);
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var loads = Number(data.get('loads'));
    var kwh = Number(data.get('kwh'));
    var electricRate = Number(data.get('electricRate'));
    var gallons = Number(data.get('gallons'));
    var waterRate = Number(data.get('waterRate'));
    var values = [loads, kwh, electricRate, gallons, waterRate];
    if (!values.every(Number.isFinite) || values.some(function (value) { return value < 0; })) return;

    var electricityPerLoad = kwh * electricRate;
    var waterPerLoad = gallons / 1000 * waterRate;
    var perLoad = electricityPerLoad + waterPerLoad;
    var annualLoads = loads * 52;
    var annual = perLoad * annualLoads;
    var monthly = annual / 12;
    var annualWater = gallons * annualLoads;
    var annualKwh = kwh * annualLoads;

    result.innerHTML = '<p class="eyebrow">Your estimate</p><h2>' + money(annual, 2) + ' per year</h2>' +
      '<div class="result-metrics"><div class="mini-stat"><strong>' + money(perLoad, 2) + '</strong><span>per load</span></div>' +
      '<div class="mini-stat"><strong>' + money(monthly, 2) + '</strong><span>average month</span></div>' +
      '<div class="mini-stat"><strong>' + money(annual, 2) + '</strong><span>per year</span></div></div>' +
      '<h3>Annual usage behind the estimate</h3><ul><li>' + Math.round(annualLoads) + ' loads</li><li>' + annualKwh.toFixed(1) + ' kWh of electricity</li><li>' + Math.round(annualWater).toLocaleString('en-US') + ' gallons of water</li></ul>' +
      '<p>Per load, electricity contributes <strong>' + money(electricityPerLoad, 2) + '</strong> and water/sewer contributes <strong>' + money(waterPerLoad, 2) + '</strong>.</p>' +
      '<p class="tool-disclaimer">This is an estimate based entirely on the inputs shown above. It is not a utility quote or an appliance efficiency certification.</p>';
    result.hidden = false;
    result.focus();
  });
})();
