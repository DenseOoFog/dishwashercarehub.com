const assert = require('assert');
const decoder = require('../assets/dishwasher-noise-decoder.js');

function decode(overrides) {
  return decoder.decode(Object.assign({ sound: 'hum', timing: 'drain', condition: 'normal', pattern: 'brief', hazard: 'none' }, overrides));
}

assert.strictEqual(decode({}).level, 'normal');
assert.strictEqual(decode({ sound: 'knock', timing: 'wash' }).title, 'Check spray-arm clearance and loading');
assert.strictEqual(decode({ sound: 'rattle', timing: 'wash', condition: 'loose-item' }).level, 'check');
assert.strictEqual(decode({ sound: 'grind', timing: 'fill', condition: 'no-water' }).guide, '../../articles/dishwasher-not-filling-with-water/');
assert.strictEqual(decode({ sound: 'grind', timing: 'drain', condition: 'standing-water' }).level, 'service');
assert.strictEqual(decode({ sound: 'bang', timing: 'fill', condition: 'plumbing-work' }).level, 'service');
assert.strictEqual(decode({ sound: 'fan', timing: 'end' }).level, 'normal');
assert.strictEqual(decode({ hazard: 'smoke' }).level, 'stop');
assert.strictEqual(decoder.decode({}), null);
console.log('Dishwasher noise decoder tests passed.');
