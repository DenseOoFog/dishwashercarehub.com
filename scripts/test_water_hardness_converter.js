'use strict';

const assert = require('node:assert/strict');
const converter = require('../assets/water-hardness-converter.js');

assert.equal(converter.calculate(0, 'mgl').classification.key, 'soft');
assert.equal(converter.calculate(60, 'mgl').classification.key, 'soft');
assert.equal(converter.calculate(61, 'mgl').classification.key, 'moderate');
assert.equal(converter.calculate(120, 'mgl').classification.key, 'moderate');
assert.equal(converter.calculate(121, 'mgl').classification.key, 'hard');
assert.equal(converter.calculate(180, 'mgl').classification.key, 'hard');
assert.equal(converter.calculate(181, 'mgl').classification.key, 'very-hard');
assert.ok(Math.abs(converter.calculate(10, 'gpg').mgL - 171.2) < 0.000001);
assert.ok(Math.abs(converter.calculate(21, 'dh').fh - 37.48) < 0.01);
assert.ok(Math.abs(converter.calculate(3.7, 'mmol').dh - 20.75) < 0.01);
assert.equal(converter.calculate(-1, 'mgl'), null);
assert.equal(converter.calculate(1, 'unknown'), null);
assert.equal(converter.calculate(10001, 'mgl'), null);
assert.ok(converter.advice(converter.calculate(260, 'mgl'), 'white-film').some(item => item.includes('15 gpg')));

console.log('Water hardness conversion tests passed.');
