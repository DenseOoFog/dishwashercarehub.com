const assert = require('assert');
const actions = require('../assets/result-actions.js');

assert.strictEqual(
  actions.normalizeText('  Annual estimate  \n\n  $68.64   per year \r\n  260 loads  '),
  'Annual estimate\n$68.64 per year\n260 loads'
);
assert.strictEqual(actions.normalizeText(null), '');

let copied = '';
actions.writeText('private local result', {
  navigator: { clipboard: { writeText(value) { copied = value; return Promise.resolve(); } } }
}, {}).then((success) => {
  assert.strictEqual(success, true);
  assert.strictEqual(copied, 'private local result');
  console.log('Result action tests passed.');
}).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
