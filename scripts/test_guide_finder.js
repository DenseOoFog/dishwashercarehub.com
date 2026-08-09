'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const finder = require('../assets/guide-finder.js');

const guides = [
  { title: 'Standing water', category: 'water drain', searchText: 'dishwasher standing water after cycle drain filter hose' },
  { title: 'White residue', category: 'wash', searchText: 'dishwasher white residue hard water detergent dishes' },
  { title: 'Door leak', category: 'operation', searchText: 'dishwasher leaking water from door gasket latch' }
];

assert.equal(finder.normalize("Won't drain"), 'wont drain');
assert.ok(finder.score('standing water', guides[0].searchText) > finder.score('water', guides[0].searchText));
assert.deepEqual(finder.filterGuides(guides, 'standing water', 'all').map(item => item.guide.title), ['Standing water']);
assert.deepEqual(finder.filterGuides(guides, 'water', 'operation').map(item => item.guide.title), ['Door leak']);
assert.deepEqual(finder.filterGuides(guides, 'no matching phrase', 'all'), []);

const page = fs.readFileSync(
  path.join(__dirname, '..', 'tools', 'dishwasher-guide-finder', 'index.html'),
  'utf8'
);
const publishedGuides = Array.from(page.matchAll(
  /<article class="card surface-card guide-result-card" data-guide-card data-category="([^"]+)" data-search="([^"]+)">\s*<h2><a href="([^"]+)">([^<]+)<\/a>/g
)).map(match => ({
  category: match[1],
  searchText: match[2],
  href: match[3],
  title: match[4]
}));

assert.equal(publishedGuides.length, 32);
function matchingTitles(query, category = 'all') {
  return finder.filterGuides(publishedGuides, query, category).map(item => item.guide.title);
}
assert.ok(matchingTitles('sewer smell').includes('Dishwasher Smells Like Sewer After a Cycle'));
assert.deepEqual(matchingTitles('disposal replaced'), ['Not Draining After Garbage Disposal Replacement']);
assert.deepEqual(matchingTitles('grinding noise'), ['Dishwasher Making a Grinding Noise']);
assert.ok(matchingTitles('wet dishes', 'performance').includes('Dishwasher Not Drying Dishes'));

console.log('Guide finder ranking tests passed.');
