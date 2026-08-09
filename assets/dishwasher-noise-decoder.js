(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherNoiseDecoder = api;
  if (root && root.document) api.attach(root.document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var valid = {
    sound: ['swish', 'click', 'hum', 'rattle', 'knock', 'grind', 'bang', 'squeal', 'beep', 'fan'],
    timing: ['fill', 'wash', 'drain', 'end', 'idle', 'unknown'],
    condition: ['normal', 'standing-water', 'no-water', 'new-install', 'plumbing-work', 'loose-item'],
    pattern: ['brief', 'repeating', 'continuous', 'louder'],
    hazard: ['none', 'leak', 'burning', 'breaker', 'smoke']
  };

  function hasValid(config) {
    return config && Object.keys(valid).every(function (key) {
      return valid[key].indexOf(config[key]) !== -1;
    });
  }

  function result(level, title, explanation, steps, guide, guideLabel) {
    return { level: level, title: title, explanation: explanation, steps: steps, guide: guide, guideLabel: guideLabel };
  }

  function decode(config) {
    if (!hasValid(config)) return null;

    if (config.hazard !== 'none') {
      return result('stop', 'Stop the dishwasher and disconnect power',
        'Noise together with smoke, a burning smell, repeated breaker trips, or active leaking is not a routine sound check.',
        ['Stop the cycle.', 'Disconnect power at the breaker if it is safe to do so.', 'Close the water supply if leaking continues and the valve is safely accessible.', 'Arrange qualified service; for smoke or fire, leave the area and contact emergency services.'],
        '../../safety/', 'Read the safety guidance');
    }

    if (config.sound === 'knock' && config.timing === 'wash') {
      return result('check', 'Check spray-arm clearance and loading',
        'A rhythmic knock during washing commonly occurs when a rotating spray arm touches a utensil, pan, or tall plate.',
        ['Turn power off before reaching into the tub.', 'Secure light items and move tall utensils or cookware clear of every spray arm.', 'Rotate each accessible spray arm gently by hand to confirm clearance.', 'Run a normal load again; arrange service if the knock remains with clear arms.'],
        '../../articles/how-to-clean-dishwasher-spray-arms/', 'Open the spray-arm guide');
    }

    if (config.sound === 'rattle' && (config.timing === 'wash' || config.condition === 'loose-item')) {
      return result('check', 'Secure the load before suspecting the pump',
        'Water movement can make utensils, lightweight lids, and dishes chatter. A loose item can also contact a spray arm.',
        ['Turn power off and inspect the racks and tub for a loose item.', 'Secure lightweight plastics and separate utensils and dishes.', 'Confirm the spray arms can rotate freely.', 'If the sound remains when the tub is safely empty, use the owner manual or arrange service.'],
        '../../articles/dishwasher-top-rack-not-getting-clean/', 'Review loading and spray coverage');
    }

    if ((config.sound === 'swish' && config.timing === 'wash') ||
        (config.sound === 'click' && ['fill', 'wash', 'drain'].indexOf(config.timing) !== -1) ||
        (config.sound === 'hum' && config.timing === 'drain' && config.condition === 'normal' && config.pattern !== 'louder')) {
      return result('normal', 'This combination often matches normal operation',
        'Water spray, valve or control changes, and a drain pump can create swishing, clicking, or a short hum during the matching cycle stage.',
        ['Compare the timing and sound with the normal-sounds section of the owner manual.', 'Check that the cycle completes, the tub drains, and wash performance remains normal.', 'Record the sound only if it becomes louder, continuous, or appears with a performance problem.'],
        '../../articles/dishwasher-making-grinding-noise/', 'Compare normal and abnormal sounds');
    }

    if (config.sound === 'fan' && config.timing === 'end' && config.condition === 'normal') {
      return result('normal', 'A drying fan may continue after the cycle',
        'Some models run a low fan or hum after the clean indicator appears. The duration is model-specific.',
        ['Check whether a fan-assisted or extended-dry option was selected.', 'Use the model manual to confirm the expected fan duration.', 'Arrange service if the sound becomes harsh, scraping, or continues beyond the documented behavior.'],
        '../../articles/dishwasher-not-drying-dishes-completely/', 'Review the drying guide');
    }

    if (config.sound === 'beep') {
      return result('check', 'Check the door, cycle status, and display',
        'A beep can mark cycle completion, a door opened mid-cycle, or a model-specific alert. The display or light pattern is more useful than the beep alone.',
        ['Close and latch the door, then press Start once if the cycle was interrupted.', 'Write down any error code or repeating light pattern.', 'Check the model manual before resetting power.', 'Arrange service if the alert returns with a leak, no-fill, no-drain, or no-start condition.'],
        '../../articles/dishwasher-wont-start-or-turn-on/', 'Open the no-start guide');
    }

    if (config.sound === 'bang' && (config.timing === 'fill' || config.timing === 'idle' || config.condition === 'plumbing-work')) {
      return result('service', 'The sound may be in the household plumbing',
        'A bang in nearby pipes as a valve opens or closes can be water hammer, especially after plumbing work. This is different from a knock inside the tub.',
        ['Do not dismantle the dishwasher or household pipes.', 'Note whether the pipe moves or bangs when other fixtures shut off.', 'Confirm the dishwasher is securely mounted only if that check is described in the installation instructions.', 'Ask a qualified plumber to assess recurring pipe hammer.'],
        '../../articles/dishwasher-drains-into-sink-when-running/', 'Review dishwasher and sink plumbing clues');
    }

    if (config.sound === 'grind' && (config.condition === 'no-water' || config.timing === 'fill')) {
      return result('service', 'Stop and resolve the no-fill condition first',
        'A circulation pump running without enough water can sound like grinding or buzzing. Repeated dry operation can worsen a fault.',
        ['Stop the cycle.', 'Confirm the household supply valve is open and the inlet hose is not visibly kinked.', 'Check the display for a model-specific error code.', 'Do not access the inlet valve or internal wiring; arrange service if water still does not enter.'],
        '../../articles/dishwasher-not-filling-with-water/', 'Open the no-fill guide');
    }

    if ((config.sound === 'grind' || config.sound === 'hum') &&
        (config.timing === 'drain' || config.condition === 'standing-water')) {
      return result('service', 'Check the user-accessible drain path, then stop if the sound persists',
        'A drain pump can hum normally, but persistent grinding or humming together with retained water points to an obstruction or pump problem.',
        ['Disconnect power.', 'Remove standing water and clean only the user-removable filter as described in the manual.', 'Check the visible air gap, disposal inlet, and drain hose for a fresh blockage or kink.', 'Do not reach into a hidden pump or remove service panels; arrange service if drainage does not recover.'],
        '../../tools/standing-water-diagnosis/', 'Use the standing-water diagnosis tool');
    }

    if (config.sound === 'squeal' && (config.condition === 'new-install' || config.pattern === 'brief')) {
      return result('check', 'Use the model instructions for first-use pump noise',
        'Some new or long-unused models can make a brief pump-seal noise, but first-use procedures vary by model.',
        ['Stop if the tub is not filling normally.', 'Check the installation and first-use instructions for the exact model.', 'Do not add water or lubricant unless the manufacturer specifically instructs it.', 'Arrange service if the squeal is loud, continuous, or returns on later cycles.'],
        '../../articles/dishwasher-making-grinding-noise/', 'Review abnormal noise warning signs');
    }

    return result('service', 'Document the sound and use the model-specific service path',
      'This combination does not have a reliable household-only conclusion. Timing, error codes, drainage, and wash performance are stronger clues than the sound name alone.',
      ['Stop the cycle if the sound is loud or worsening.', 'Check for a loose item and clear spray-arm movement with power disconnected.', 'Record a short video from a safe distance and note the exact cycle stage.', 'Use the owner manual or arrange qualified service if the sound repeats.'],
      '../../articles/dishwasher-making-grinding-noise/', 'Open the detailed noise guide');
  }

  function escapeText(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char];
    });
  }

  function attach(doc) {
    var form = doc.getElementById('noise-form');
    var output = doc.getElementById('noise-result');
    if (!form || !output) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var data = new FormData(form);
      var decoded = decode({ sound: data.get('sound'), timing: data.get('timing'), condition: data.get('condition'), pattern: data.get('pattern'), hazard: data.get('hazard') });
      if (!decoded) return;
      output.className = 'surface-card tool-result' + (decoded.level === 'stop' ? ' warning-card' : '');
      output.innerHTML = '<p class="eyebrow">' + escapeText(decoded.level === 'normal' ? 'Often normal' : decoded.level === 'stop' ? 'Stop now' : decoded.level === 'service' ? 'Higher-priority check' : 'Safe first check') + '</p><h2>' + escapeText(decoded.title) + '</h2><p>' + escapeText(decoded.explanation) + '</p><ol class="numbered-list">' + decoded.steps.map(function (step) { return '<li>' + escapeText(step) + '</li>'; }).join('') + '</ol><p><a class="pill-button primary-button" href="' + decoded.guide + '">' + escapeText(decoded.guideLabel) + '</a></p><p class="tool-disclaimer">This result organizes observable clues; it does not identify a failed part. Your model manual takes priority.</p>';
      output.hidden = false;
      output.focus();
    });
  }

  return { decode: decode, attach: attach };
});
