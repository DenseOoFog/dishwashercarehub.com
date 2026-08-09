const assert = require('assert');
const tool = require('../assets/standing-water-diagnosis.js');

function diagnose(overrides) {
  return tool.diagnose(Object.assign({ amount: 'floor', timing: 'after', sink: 'normal', disposal: 'no', airgap: 'no', sound: 'normal', filter: 'yes' }, overrides));
}

assert.strictEqual(diagnose({ amount: 'overflow' }).label, 'Stop the cycle and protect the area');
assert.strictEqual(diagnose({ amount: 'sump' }).label, 'Likely normal retained sump water');
assert.strictEqual(diagnose({ disposal: 'yes' }).href, '../../articles/dishwasher-not-draining-after-garbage-disposal-replaced/');
assert.strictEqual(diagnose({ airgap: 'yes' }).href, '../../articles/dishwasher-air-gap-overflowing/');
assert.strictEqual(diagnose({ sink: 'slow' }).href, '../../articles/dishwasher-drains-into-sink-when-running/');
assert.strictEqual(diagnose({ timing: 'morning' }).href, '../../articles/dishwasher-drains-then-fills-back-up/');
assert.strictEqual(diagnose({ filter: 'no' }).href, '../../articles/how-to-clean-dishwasher-filter/');
assert.strictEqual(diagnose({ sound: 'hum' }).label, 'Stop if the new noise persists');
assert.strictEqual(diagnose({ sound: 'silent' }).label, 'The next useful check likely requires service');
assert.strictEqual(diagnose({}).label, 'Inspect the visible drain-hose route next');
assert.strictEqual(tool.diagnose({}), null);
console.log('Standing water diagnosis tests passed.');
