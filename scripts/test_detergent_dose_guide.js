'use strict';

const assert = require('node:assert/strict');
const guide = require('../assets/detergent-dose-guide.js');

assert.ok(Math.abs(guide.normalizeHardness(171.2, 'ppm') - 10) < 0.000001);
assert.ok(Math.abs(guide.normalizeHardness(10, 'dh') - 10.425) < 0.001);
assert.equal(guide.normalizeHardness(-1, 'gpg'), null);
assert.equal(guide.normalizeHardness(1, 'unknown'), null);
assert.equal(guide.hardnessBand(3).key, 'soft');
assert.equal(guide.hardnessBand(3.1).key, 'medium');
assert.equal(guide.hardnessBand(8).key, 'medium');
assert.equal(guide.hardnessBand(12).key, 'hard');
assert.equal(guide.hardnessBand(12.1).key, 'very-hard');

const softPowder = guide.buildGuide({ hardness: 2, unit: 'gpg', type: 'powder', soil: 'light', symptom: 'etching' });
assert.equal(softPowder.band.key, 'soft');
assert.match(softPowder.startingPoint, /one-third/);
assert.ok(softPowder.steps.some((step) => step.includes('etching')));

const hardPod = guide.buildGuide({ hardness: 250, unit: 'ppm', type: 'pod', soil: 'heavy', symptom: 'food' });
assert.equal(hardPod.band.key, 'very-hard');
assert.match(hardPod.startingPoint, /one intact/);
assert.ok(hardPod.steps.some((step) => step.includes('water treatment')));
assert.equal(guide.buildGuide({ hardness: 5, unit: 'gpg', type: 'soap', soil: 'normal', symptom: 'none' }), null);

console.log('Detergent dose guide tests passed.');
