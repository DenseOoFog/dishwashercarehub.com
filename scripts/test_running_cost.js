const assert = require('assert');
const tool = require('../assets/dishwasher-running-cost.js');

const result = tool.calculate({ loads: 5, kwh: 1.2, electricRate: 0.17, gallons: 4, waterRate: 15 });
assert.ok(Math.abs(result.perLoad - 0.264) < 1e-9);
assert.ok(Math.abs(result.annual - 68.64) < 1e-9);
assert.strictEqual(result.annualLoads, 260);
assert.strictEqual(tool.calculate({ loads: -1, kwh: 1, electricRate: 1, gallons: 1, waterRate: 1 }), null);
assert.strictEqual(tool.calculate({ loads: 51, kwh: 1, electricRate: 1, gallons: 1, waterRate: 1 }), null);
assert.strictEqual(tool.calculate({ loads: 1, kwh: 'bad', electricRate: 1, gallons: 1, waterRate: 1 }), null);
console.log('Dishwasher running cost tests passed.');
