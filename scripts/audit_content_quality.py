#!/usr/bin/env python3
"""Detect truncated or mechanically duplicated article content before publishing."""

from collections import defaultdict
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_ROOT = ROOT / "articles"
MIN_WORDS = 600
MIN_H2S = 8
MIN_CONTENT_BLOCKS = 15
MIN_DUPLICATE_PARAGRAPH_WORDS = 18
MAX_FIVE_GRAM_JACCARD = 0.25
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’.-][A-Za-z0-9]+)*")
UNIVERSAL_RECIPE_PATTERNS = {
    "anonymous technician authority claim": re.compile(
        r"\b(?:experienced (?:appliance )?technicians|technicians report|"
        r"four out of five .+? calls|service data from .+? networks)\b",
        re.IGNORECASE,
    ),
    "fixed detergent dose": re.compile(
        r"\b(?:one tablespoon per normal load|reduce detergent to one tablespoon)\b",
        re.IGNORECASE,
    ),
    "universal vinegar cleaning cycle": re.compile(
        r"\b(?:run (?:a|an|the) (?:empty |full )?vinegar cycle|"
        r"vinegar cleaning cycle)\b",
        re.IGNORECASE,
    ),
    "universal cleaner quantity": re.compile(
        r"\b(?:two cups white vinegar|one cup baking soda|"
        r"pour a cup of white vinegar)\b",
        re.IGNORECASE,
    ),
    "universal cycle or interval": re.compile(
        r"\b(?:hottest and longest cycle|monthly without exception)\b",
        re.IGNORECASE,
    ),
}


class ArticleParser(HTMLParser):
    """Collect visible text and structure from the first article element."""

    def __init__(self):
        super().__init__()
        self.article_depth = 0
        self.ignored_depth = 0
        self.h1_count = 0
        self.h2_count = 0
        self.blocks = []
        self._block_tag = None
        self._block_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.article_depth += 1
            return
        if not self.article_depth:
            return
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
        if self.ignored_depth:
            return
        if tag == "h1":
            self.h1_count += 1
        elif tag == "h2":
            self.h2_count += 1
        if tag in {"h1", "h2", "p", "li"} and self._block_tag is None:
            self._block_tag = tag
            self._block_parts = []

    def handle_data(self, data):
        if self.article_depth and not self.ignored_depth and self._block_tag:
            self._block_parts.append(data)

    def handle_endtag(self, tag):
        if not self.article_depth:
            return
        if tag in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1
            return
        if not self.ignored_depth and tag == self._block_tag:
            text = " ".join("".join(self._block_parts).split())
            if text:
                self.blocks.append((self._block_tag, text))
            self._block_tag = None
            self._block_parts = []
        if tag == "article":
            self.article_depth -= 1


def words(text):
    return [match.group(0).lower().replace("’", "'") for match in WORD_RE.finditer(text)]


def normalized_paragraph(text):
    return " ".join(words(text))


def ngrams(tokens, size=5):
    return set(zip(*(tokens[offset:] for offset in range(size))))


def jaccard(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def parse_article(path):
    parser = ArticleParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def main():
    paths = sorted(ARTICLE_ROOT.glob("*/index.html"))
    errors = []
    records = {}
    repeated_paragraphs = defaultdict(list)

    if not paths:
        errors.append("No article pages found")

    for path in paths:
        parser = parse_article(path)
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        visible_text = " ".join(text for _, text in parser.blocks)
        tokens = words(visible_text)
        content_blocks = [text for tag, text in parser.blocks if tag in {"p", "li"}]
        records[relative] = {
            "words": len(tokens),
            "five_grams": ngrams(tokens),
        }

        if parser.h1_count != 1:
            errors.append(f"{relative}: expected 1 h1, found {parser.h1_count}")
        if parser.h2_count < MIN_H2S:
            errors.append(f"{relative}: only {parser.h2_count} h2 headings (minimum {MIN_H2S})")
        if len(content_blocks) < MIN_CONTENT_BLOCKS:
            errors.append(
                f"{relative}: only {len(content_blocks)} paragraphs/list items "
                f"(minimum {MIN_CONTENT_BLOCKS})"
            )
        if len(tokens) < MIN_WORDS:
            errors.append(f"{relative}: only {len(tokens)} visible words (minimum {MIN_WORDS})")
        for label, pattern in UNIVERSAL_RECIPE_PATTERNS.items():
            if pattern.search(source):
                errors.append(f"{relative}: contains {label}")

        # Repeated source citations and short safety bullets are legitimate across
        # closely related guides. Prose paragraphs, however, should be original.
        for tag, text in parser.blocks:
            if tag != "p":
                continue
            normalized = normalized_paragraph(text)
            if len(normalized.split()) >= MIN_DUPLICATE_PARAGRAPH_WORDS:
                repeated_paragraphs[normalized].append(relative)

    for paragraph, owners in repeated_paragraphs.items():
        unique_owners = sorted(set(owners))
        if len(unique_owners) > 1:
            preview = paragraph[:100] + ("..." if len(paragraph) > 100 else "")
            errors.append(
                f"Exact paragraph duplicated across {', '.join(unique_owners)}: {preview}"
            )

    highest_pair = None
    highest_similarity = 0.0
    for left, right in combinations(records, 2):
        similarity = jaccard(records[left]["five_grams"], records[right]["five_grams"])
        if similarity > highest_similarity:
            highest_similarity = similarity
            highest_pair = (left, right)
        if similarity >= MAX_FIVE_GRAM_JACCARD:
            errors.append(
                f"{left} and {right}: five-gram similarity {similarity:.1%} "
                f"(maximum {MAX_FIVE_GRAM_JACCARD:.0%})"
            )

    if records:
        thinnest = min(records, key=lambda item: records[item]["words"])
        fullest = max(records, key=lambda item: records[item]["words"])
        print(
            f"Audited {len(records)} articles: "
            f"{records[thinnest]['words']}–{records[fullest]['words']} visible words."
        )
        print(f"Shortest: {thinnest}; longest: {fullest}.")
        if highest_pair:
            print(
                f"Highest five-gram similarity: {highest_similarity:.1%} "
                f"({highest_pair[0]} vs {highest_pair[1]})."
            )

    if errors:
        print("Content quality audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Content quality audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
