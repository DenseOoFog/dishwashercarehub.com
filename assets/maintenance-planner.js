(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherMaintenancePlanner = api;
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', api.init);
    else api.init();
  }
})(typeof window !== 'undefined' ? window : null, function () {
  var GUIDE_LINKS = { odor: '../../articles/dishwasher-smells-bad-after-wash/', residue: '../../articles/dishwasher-white-residue-on-dishes/', 'poor-cleaning': '../../articles/dishwasher-leaving-food-particles-on-dishes/', drainage: '../standing-water-diagnosis/', drying: '../../articles/dishwasher-not-drying-dishes-completely/' };
  function validDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null;
    var parts = value.split('-').map(Number);
    var parsed = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
    if (parsed.getUTCFullYear() !== parts[0] || parsed.getUTCMonth() !== parts[1] - 1 || parsed.getUTCDate() !== parts[2]) return null;
    return parsed;
  }
  function isoDate(date) { return date.toISOString().slice(0, 10); }
  function addDays(start, days) { var result = new Date(start.getTime()); result.setUTCDate(result.getUTCDate() + days); return result; }
  function formatDate(value) { var date = typeof value === 'string' ? validDate(value) : value; return date ? date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }) : ''; }
  function filterInterval(usage, filter) { if (filter === 'maintenance-free') return 90; if (filter === 'unknown') return usage === 'heavy' ? 30 : 60; if (usage === 'heavy') return 14; if (usage === 'light') return 60; return 30; }
  function armInterval(usage) { return usage === 'heavy' ? 60 : usage === 'light' ? 120 : 90; }
  function task(id, title, days, note, start, link) { return { id: id, title: title, cadenceDays: days, due: isoDate(addDays(start, days)), note: note, link: link || null }; }
  function buildPlan(config) {
    var start = validDate(config.start);
    if (!start || !['light', 'regular', 'heavy'].includes(config.usage) || !['manual', 'maintenance-free', 'unknown'].includes(config.filter) || !['soft', 'hard', 'unknown'].includes(config.hardness) || (!Object.prototype.hasOwnProperty.call(GUIDE_LINKS, config.symptom) && config.symptom !== 'none')) return null;
    var tasks = [];
    var filterNote = config.filter === 'maintenance-free' ? 'Inspect the manual and visible filter or object-cup area; do not remove a maintenance-free system unless the model instructions allow it.' : config.filter === 'unknown' ? 'Identify the filter type in the owner manual before removing anything; clean only a user-removable filter.' : 'Inspect and clean the removable filter as the owner manual directs, then lock it correctly before use.';
    tasks.push(task('filter', 'Filter-system check', filterInterval(config.usage, config.filter), filterNote, start, '../../articles/how-to-clean-dishwasher-filter/'));
    tasks.push(task('interior', 'Interior, door edge, and seal wipe', 30, 'Use a damp soft cloth and only model-approved cleaner; never mix cleaning products.', start, '../../articles/monthly-dishwasher-maintenance-checklist/'));
    tasks.push(task('rinse-aid', 'Rinse-aid and detergent storage check', 30, 'Check the reservoir if your model uses rinse aid and confirm detergent is fresh, dry, and intended for automatic dishwashers.', start));
    tasks.push(task('spray-arms', 'Spray-arm clearance and nozzle check', armInterval(config.usage), 'Confirm the arms turn freely and inspect visible nozzles; follow the manual before removing an arm.', start, '../../articles/how-to-clean-dishwasher-spray-arms/'));
    tasks.push(task('drain-path', 'Visible drain-path and air-gap check', 90, 'Look for a moved hose, slow sink, or air-gap buildup without disconnecting plumbing or opening panels.', start, '../standing-water-diagnosis/'));
    tasks.push(task('hardness', 'Water-hardness and scale review', config.hardness === 'hard' ? 90 : 180, config.hardness === 'hard' ? 'Compare the model hardness setting, salt system, rinse aid, and approved descaling interval with your manual.' : 'Confirm local hardness and use the model manual before changing salt, rinse aid, detergent, or descaling products.', start, '../dishwasher-water-hardness-converter/'));
    if (config.symptom !== 'none') {
      var labels = { odor: 'Diagnose the current odor before routine cleaning', residue: 'Identify the current film or spotting before changing products', 'poor-cleaning': 'Diagnose the current cleaning pattern', drainage: 'Diagnose the current standing-water pattern', drying: 'Diagnose the current drying result' };
      tasks.unshift({ id: 'symptom', title: labels[config.symptom], cadenceDays: 0, due: isoDate(start), note: 'A current symptom should be diagnosed now rather than postponed until the next routine maintenance date.', link: GUIDE_LINKS[config.symptom] });
    }
    return { start: isoDate(start), usage: config.usage, filter: config.filter, hardness: config.hardness, symptom: config.symptom, tasks: tasks };
  }
  function cadence(days) { var values = { 0: 'Now', 14: 'Every 2 weeks', 30: 'Every month', 60: 'Every 2 months', 90: 'Every 3 months', 120: 'Every 4 months', 180: 'Every 6 months' }; return values[days] || 'Every ' + days + ' days'; }
  function render(plan) {
    var rows = plan.tasks.map(function (item) { var title = item.link ? '<a href="' + item.link + '">' + item.title + '</a>' : item.title; return '<li class="maintenance-task"><label><input type="checkbox"> <strong>' + title + '</strong></label><span class="maintenance-due">' + cadence(item.cadenceDays) + ' · next due ' + formatDate(item.due) + '</span><p>' + item.note + '</p></li>'; }).join('');
    return '<p class="eyebrow">Your dated care plan</p><h2>Start ' + formatDate(plan.start) + '</h2><ol class="maintenance-plan">' + rows + '</ol><div class="hero-actions print-actions"><button type="button" class="pill-button secondary-button" data-print-plan>Print this checklist</button></div><p class="tool-disclaimer">The dates are planning defaults based on your answers. Your model manual and product labels control exact intervals, removal steps, and approved products.</p>';
  }
  function todayLocalIso() { var now = new Date(); return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-'); }
  function init() {
    var form = document.getElementById('maintenance-form'); var output = document.getElementById('maintenance-result'); if (!form || !output) return;
    if (!form.elements.start.value) form.elements.start.value = todayLocalIso();
    form.addEventListener('submit', function (event) { event.preventDefault(); var data = new FormData(form); var plan = buildPlan({ start: data.get('start'), usage: data.get('usage'), filter: data.get('filter'), hardness: data.get('hardness'), symptom: data.get('symptom') }); output.className = plan ? 'surface-card tool-result' : 'surface-card tool-result warning-card'; output.innerHTML = plan ? render(plan) : '<h2>Check the plan inputs</h2><p>Choose a valid start date and one option in every field.</p>'; output.hidden = false; output.focus(); });
    output.addEventListener('click', function (event) { if (event.target.closest('[data-print-plan]')) window.print(); });
  }
  return { validDate: validDate, isoDate: isoDate, addDays: addDays, filterInterval: filterInterval, armInterval: armInterval, buildPlan: buildPlan, cadence: cadence, render: render, init: init };
});
