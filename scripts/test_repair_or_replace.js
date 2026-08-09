const assert = require('assert');
const tool = require('../assets/repair-or-replace.js');

function compare(overrides) {
  return tool.compare(Object.assign({ age: 4, repair: 150, replacement: 1000, repairs: '0', major: 'no', hazard: 'no' }, overrides));
}
assert.strictEqual(compare({}).level, 'repair');
assert.strictEqual(compare({ age: 8, repair: 400, repairs: '1' }).level, 'compare');
assert.strictEqual(compare({ age: 12, repair: 700, repairs: '2', major: 'yes' }).level, 'replace');
assert.strictEqual(compare({ hazard: 'yes' }).level, 'hazard');
assert.strictEqual(compare({ repair: 1200, replacement: 1000 }).difference, -200);
assert.strictEqual(compare({ replacement: 0 }), null);
assert.strictEqual(compare({ age: 31 }), null);
assert.strictEqual(compare({ repairs: '3' }), null);
console.log('Repair or replace tests passed.');
