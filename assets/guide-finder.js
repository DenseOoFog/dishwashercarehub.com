(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.DishwasherGuideFinder = api;
  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', api.init);
    } else {
      api.init();
    }
  }
})(typeof window !== 'undefined' ? window : null, function () {
  function normalize(value) {
    return String(value || '')
      .toLowerCase()
      .replace(/[’']/g, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim();
  }

  function score(query, searchableText) {
    var normalizedQuery = normalize(query);
    if (!normalizedQuery) return 1;
    var normalizedText = normalize(searchableText);
    var tokens = normalizedQuery.split(' ').filter(Boolean);
    var matched = tokens.filter(function (token) {
      return normalizedText.indexOf(token) !== -1;
    });
    if (matched.length !== tokens.length) return 0;
    var phraseBonus = normalizedText.indexOf(normalizedQuery) !== -1 ? 20 : 0;
    return phraseBonus + matched.reduce(function (total, token) {
      return total + (normalizedText.split(token).length - 1);
    }, 0);
  }

  function filterGuides(guides, query, category) {
    return guides
      .map(function (guide, index) {
        var categoryMatch = !category || category === 'all' ||
          String(guide.category || '').split(' ').indexOf(category) !== -1;
        return {
          guide: guide,
          index: index,
          score: categoryMatch ? score(query, guide.searchText) : 0
        };
      })
      .filter(function (item) { return item.score > 0; })
      .sort(function (a, b) { return b.score - a.score || a.index - b.index; });
  }

  function init() {
    var input = document.getElementById('guide-search');
    var list = document.getElementById('guide-results');
    var count = document.getElementById('guide-count');
    var empty = document.getElementById('guide-empty');
    var buttons = Array.prototype.slice.call(document.querySelectorAll('[data-guide-filter]'));
    if (!input || !list || !count || !empty) return;

    var cards = Array.prototype.slice.call(list.querySelectorAll('[data-guide-card]'));
    var guides = cards.map(function (card) {
      return {
        element: card,
        category: card.getAttribute('data-category') || '',
        searchText: card.getAttribute('data-search') || card.textContent
      };
    });
    var activeCategory = 'all';

    function render() {
      var matches = filterGuides(guides, input.value, activeCategory);
      var visible = new Set(matches.map(function (item) { return item.guide.element; }));
      cards.forEach(function (card) { card.hidden = !visible.has(card); });
      matches.forEach(function (item) { list.appendChild(item.guide.element); });
      count.textContent = matches.length + (matches.length === 1 ? ' matching guide' : ' matching guides');
      empty.hidden = matches.length !== 0;
    }

    input.addEventListener('input', render);
    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        activeCategory = button.getAttribute('data-guide-filter') || 'all';
        buttons.forEach(function (candidate) {
          var selected = candidate === button;
          candidate.setAttribute('aria-pressed', selected ? 'true' : 'false');
        });
        render();
      });
    });
    render();
  }

  return { normalize: normalize, score: score, filterGuides: filterGuides, init: init };
});
