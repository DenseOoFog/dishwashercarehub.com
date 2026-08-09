const assert = require('assert');
const tool = require('../assets/symptom-checker.js');

function plan(overrides) {
  return tool.buildPlan(Object.assign({ symptom: 'water', timing: 'sudden', filter: 'yes', noise: 'no', hazard: 'no' }, overrides));
}
assert.strictEqual(plan({}).href, '../../articles/dishwasher-standing-water-after-cycle/');
assert.strictEqual(plan({ symptom: 'smell' }).href, '../../articles/dishwasher-smells-bad-after-wash/');
assert.strictEqual(plan({ symptom: 'leak', hazard: 'yes' }).hazard, true);
assert.strictEqual(plan({ timing: 'install' }).extra.length, 1);
assert.strictEqual(plan({ filter: 'unknown', noise: 'yes' }).extra.length, 2);
assert.strictEqual(plan({ symptom: 'unknown' }), null);
assert.strictEqual(plan({ hazard: 'maybe' }), null);
console.log('Dishwasher symptom checker tests passed.');
