(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RepairOrReplace = api;
  if (root && root.document) api.attach(root.document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function compare(input) {
    if (!input) return null;
    var age = Number(input.age);
    var repair = Number(input.repair);
    var replacement = Number(input.replacement);
    var priorRepairs = Number(input.repairs);
    if (!Number.isFinite(age) || age < 0 || age > 30 || !Number.isFinite(repair) || repair < 0 || repair > 10000 || !Number.isFinite(replacement) || replacement <= 0 || replacement > 20000 || [0, 1, 2].indexOf(priorRepairs) === -1 || ['yes', 'no'].indexOf(input.major) === -1 || ['yes', 'no'].indexOf(input.hazard) === -1) return null;
    var ratio = repair / replacement;
    var score = ratio * 5;
    if (age >= 10) score += 1.5;
    else if (age >= 7) score += 0.75;
    if (priorRepairs === 1) score += 0.6;
    if (priorRepairs >= 2) score += 1.4;
    if (input.major === 'yes') score += 0.75;
    var level = input.hazard === 'yes' ? 'hazard' : score < 2.6 ? 'repair' : score < 4.6 ? 'compare' : 'replace';
    var copy = {
      hazard: ['Pause use and get a qualified inspection first', 'Safety and water-damage symptoms take priority over the price comparison. Disconnect power, shut off the water supply if it is safe to reach, and do not run another cycle until the source is identified.'],
      repair: ['Repair appears economically reasonable', 'The quote is modest relative to an installed replacement and the age and repair history do not strongly argue against fixing it. Confirm the diagnosis and warranty before approving work.'],
      compare: ['Compare one more quote before deciding', 'The numbers are in the middle. A second repair diagnosis and a complete installed replacement estimate could change the decision. Reliability, noise, rack condition, and fit also matter.'],
      replace: ['Replacement deserves serious consideration', 'The repair share, appliance age, or repeat-repair history makes another repair harder to justify. This is not an instruction to replace it—verify both estimates and any warranty coverage first.']
    };
    return { level: level, heading: copy[level][0], explanation: copy[level][1], ratio: ratio, difference: replacement - repair, age: age, ageContext: age < 5 ? 'relatively young' : age < 10 ? 'mid-life' : 'older' };
  }

  function money(value) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value); }
  function percent(value) { return Math.round(value * 100) + '%'; }

  function attach(doc) {
    var form = doc.getElementById('repair-form');
    var output = doc.getElementById('repair-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var decision = compare({ age: data.get('age'), repair: data.get('repair'), replacement: data.get('replacement'), repairs: data.get('repairs'), major: data.get('major'), hazard: data.get('hazard') });
      if (!decision) return;
      output.className = 'surface-card tool-result' + (decision.level === 'hazard' ? ' warning-card' : '');
      output.innerHTML = '<p class="eyebrow">Your comparison</p><h2>' + decision.heading + '</h2><div class="result-metrics"><div class="mini-stat"><strong>' + percent(decision.ratio) + '</strong><span>repair-to-replacement ratio</span></div><div class="mini-stat"><strong>' + money(decision.difference) + '</strong><span>upfront difference</span></div><div class="mini-stat"><strong>' + decision.age + ' years</strong><span>' + decision.ageContext + ' appliance</span></div></div><p>' + decision.explanation + '</p><h3>Questions to ask next</h3><ul><li>What exact failed part or condition produced the diagnosis?</li><li>How long are parts and labor covered after the repair?</li><li>Does the replacement estimate include every installation and disposal cost?</li></ul><p class="tool-disclaimer">This calculator provides a cost comparison, not financial, electrical, plumbing, or repair advice.</p>';
      output.hidden = false;
      output.focus();
    });
  }

  return { compare: compare, attach: attach };
});
