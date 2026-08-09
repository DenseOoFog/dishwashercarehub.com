(function () {
  var form = document.getElementById('repair-form');
  var result = document.getElementById('repair-result');
  if (!form || !result) return;

  function money(value) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
  }

  function percent(value) {
    return Math.round(value * 100) + '%';
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = new FormData(form);
    var age = Number(data.get('age'));
    var repair = Number(data.get('repair'));
    var replacement = Number(data.get('replacement'));
    var priorRepairs = Number(data.get('repairs'));
    var major = data.get('major') === 'yes';
    var hazard = data.get('hazard') === 'yes';
    if (![age, repair, replacement].every(Number.isFinite) || replacement <= 0 || repair < 0 || age < 0) return;

    var ratio = repair / replacement;
    var score = ratio * 5;
    if (age >= 10) score += 1.5;
    else if (age >= 7) score += 0.75;
    if (priorRepairs === 1) score += 0.6;
    if (priorRepairs >= 2) score += 1.4;
    if (major) score += 0.75;

    var heading;
    var explanation;
    if (hazard) {
      heading = 'Pause use and get a qualified inspection first';
      explanation = 'Safety and water-damage symptoms take priority over the price comparison. Disconnect power, shut off the water supply if it is safe to reach, and do not run another cycle until the source is identified.';
    } else if (score < 2.6) {
      heading = 'Repair appears economically reasonable';
      explanation = 'The quote is modest relative to an installed replacement and the age and repair history do not strongly argue against fixing it. Confirm the diagnosis and warranty before approving work.';
    } else if (score < 4.6) {
      heading = 'Compare one more quote before deciding';
      explanation = 'The numbers are in the middle. A second repair diagnosis and a complete installed replacement estimate could change the decision. Reliability, noise, rack condition, and fit also matter.';
    } else {
      heading = 'Replacement deserves serious consideration';
      explanation = 'The repair share, appliance age, or repeat-repair history makes another repair harder to justify. This is not an instruction to replace it—verify both estimates and any warranty coverage first.';
    }

    var ageContext = age < 5 ? 'relatively young' : age < 10 ? 'mid-life' : 'older';
    result.className = 'surface-card tool-result' + (hazard ? ' warning-card' : '');
    result.innerHTML = '<p class="eyebrow">Your comparison</p><h2>' + heading + '</h2><div class="result-metrics"><div class="mini-stat"><strong>' + percent(ratio) + '</strong><span>repair-to-replacement ratio</span></div><div class="mini-stat"><strong>' + money(replacement - repair) + '</strong><span>upfront difference</span></div><div class="mini-stat"><strong>' + age + ' years</strong><span>' + ageContext + ' appliance</span></div></div><p>' + explanation + '</p><h3>Questions to ask next</h3><ul><li>What exact failed part or condition produced the diagnosis?</li><li>How long are parts and labor covered after the repair?</li><li>Does the replacement estimate include every installation and disposal cost?</li></ul><p class="tool-disclaimer">This calculator provides a cost comparison, not financial, electrical, plumbing, or repair advice.</p>';
    result.hidden = false;
    result.focus();
  });
})();
