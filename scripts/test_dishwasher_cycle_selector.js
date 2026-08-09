'use strict';

const assert = require('node:assert/strict');
const selector = require('../assets/dishwasher-cycle-selector.js');

function choose(overrides) {
  return selector.selectCycle(Object.assign({ soil: 'normal', load: 'everyday', priority: 'balanced', sensor: 'unknown' }, overrides));
}

assert.equal(choose({}).primary, 'Normal');
assert.equal(choose({ soil: 'mixed', sensor: 'yes' }).primary, 'Auto / Sensor');
assert.equal(choose({ soil: 'heavy' }).primary, 'Heavy / Pots & Pans');
assert.equal(choose({ load: 'cookware' }).primary, 'Heavy / Pots & Pans');
assert.equal(choose({ soil: 'light', priority: 'fast' }).primary, 'Quick / 1-Hour Wash');
assert.equal(choose({ soil: 'light', priority: 'efficiency' }).primary, 'Eco / Light');
assert.equal(choose({ load: 'delicate' }).primary, 'Delicate / China / Crystal');
assert.equal(choose({ load: 'hold' }).primary, 'Rinse Only / Pre-Rinse');
assert.ok(choose({ load: 'hold' }).checks.some((item) => item.includes('no detergent')));
assert.ok(choose({ priority: 'sanitize' }).avoid.some((item) => item.includes('medical sterilization')));
assert.ok(choose({ load: 'plastic', priority: 'drying' }).checks.some((item) => item.includes('dishwasher-safe plastic')));
assert.equal(selector.selectCycle({ soil: 'invalid', load: 'everyday', priority: 'balanced', sensor: 'yes' }), null);

console.log('Dishwasher cycle selector tests passed.');
