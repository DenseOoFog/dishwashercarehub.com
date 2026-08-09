(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherDetergentGuide = api;
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', api.init);
    else api.init();
  }
})(typeof window !== 'undefined' ? window : null, function () {
  var TO_GPG = { gpg: 1, ppm: 1 / 17.12, mgl: 1 / 17.12, dh: 17.848 / 17.12 };

  function normalizeHardness(value, unit) {
    var numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric < 0 || !TO_GPG[unit]) return null;
    var gpg = numeric * TO_GPG[unit];
    return gpg <= 584 ? gpg : null;
  }

  function hardnessBand(gpg) {
    if (!Number.isFinite(gpg) || gpg < 0) return null;
    if (gpg <= 3) return { key: 'soft', label: 'soft', cup: 'about one-third of the main-wash cup' };
    if (gpg <= 8) return { key: 'medium', label: 'medium', cup: 'about two-thirds of the main-wash cup' };
    if (gpg <= 12) return { key: 'hard', label: 'hard', cup: 'the full main-wash cup' };
    return { key: 'very-hard', label: 'very hard', cup: 'the full main-wash cup; check whether your manual also calls for the pre-wash cup' };
  }

  function buildGuide(input) {
    input = input || {};
    var gpg = normalizeHardness(input.hardness, input.unit);
    var validTypes = ['powder', 'gel', 'pod'];
    var validSoil = ['light', 'normal', 'heavy'];
    var validSymptoms = ['none', 'film', 'etching', 'food', 'undissolved'];
    if (gpg === null || validTypes.indexOf(input.type) < 0 || validSoil.indexOf(input.soil) < 0 || validSymptoms.indexOf(input.symptom) < 0) return null;

    var band = hardnessBand(gpg);
    var steps = [];
    var startingPoint;
    if (input.type === 'pod') {
      startingPoint = 'Use one intact, premeasured dishwasher pack only when its label and your dishwasher manual permit it.';
      steps.push('Do not cut, unwrap, or estimate a partial dose from a pack unless its manufacturer explicitly instructs you to do so.');
    } else {
      startingPoint = 'For a general starting point, use ' + band.cup + '.';
      steps.push('Use the fill marks in your own dispenser rather than converting cup fractions into a universal gram or tablespoon amount.');
    }

    if (input.soil === 'light') steps.push('For a lightly soiled load, choose the manual-approved light or normal cycle and avoid adding extra pre-wash detergent by habit.');
    if (input.soil === 'normal') steps.push('For a normal load, scrape large food pieces, keep spray paths open, and start with the normal or auto cycle.');
    if (input.soil === 'heavy') steps.push('Heavy soil may need the model’s heavy cycle or pre-wash instructions; do not simply exceed the detergent label maximum.');

    if (input.symptom === 'film') steps.push('For removable white film, verify hardness, rinse aid, salt or softener settings, and detergent amount—change one variable for the next load.');
    if (input.symptom === 'etching') steps.push('Permanent cloudy or rainbow glass damage can be etching. With soft water, reduce detergent only within label and manual guidance; etched glass cannot be restored.');
    if (input.symptom === 'food') steps.push('Food left behind is not automatically a low-dose problem. Check the filter, spray-arm movement, loading, cycle choice, and incoming hot water first.');
    if (input.symptom === 'undissolved') steps.push('Undissolved detergent often points to a blocked dispenser, damp or old product, low temperature, short cycle, or poor spray—not a need for more detergent.');
    if (band.key === 'very-hard') steps.push('Above 12 gpg, scale control may matter more than adding detergent. Check whether your model supports dishwasher salt or whether household water treatment is recommended.');
    if (band.key === 'soft') steps.push('Soft water needs special restraint: excess detergent can contribute to film and permanent glass etching.');

    return { gpg: gpg, ppm: gpg * 17.12, band: band, startingPoint: startingPoint, steps: steps };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character];
    });
  }

  function init() {
    var form = document.getElementById('detergent-guide-form');
    var output = document.getElementById('detergent-guide-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var result = buildGuide({
        hardness: data.get('hardness'), unit: data.get('unit'), type: data.get('type'),
        soil: data.get('soil'), symptom: data.get('symptom')
      });
      if (!result) {
        output.className = 'surface-card tool-result warning-card';
        output.innerHTML = '<h2>Check the hardness entry</h2><p>Enter a non-negative number and confirm the unit printed beside your result.</p>';
      } else {
        output.className = 'surface-card tool-result';
        output.innerHTML = '<p class="eyebrow">General starting guide</p>' +
          '<h2>' + escapeHtml(result.band.label.charAt(0).toUpperCase() + result.band.label.slice(1)) + ' water</h2>' +
          '<div class="result-metrics"><div class="mini-stat"><strong>' + result.gpg.toFixed(1) + '</strong><span>grains per U.S. gallon</span></div>' +
          '<div class="mini-stat"><strong>' + result.ppm.toFixed(0) + '</strong><span>ppm / mg/L as CaCO₃</span></div></div>' +
          '<h3>Your starting point</h3><p>' + escapeHtml(result.startingPoint) + '</p>' +
          '<h3>Adjustment checklist</h3><ol>' + result.steps.map(function (step) { return '<li>' + escapeHtml(step) + '</li>'; }).join('') + '</ol>' +
          '<p class="tool-disclaimer"><strong>Important:</strong> This is a general decision guide, not a model-specific dose. Your dishwasher manual and detergent label override it. Use only automatic dishwasher detergent—never hand dish soap.</p>';
      }
      output.hidden = false;
      output.focus();
    });
  }

  return { TO_GPG: TO_GPG, normalizeHardness: normalizeHardness, hardnessBand: hardnessBand, buildGuide: buildGuide, init: init };
});
