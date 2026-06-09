"""
Milestone 3 — Document ingestion and chunking.

Pipeline:
  load_documents()  -> read every .txt in documents/ as {source, raw}
  clean_text()      -> strip web boilerplate (nav, upvote/share bars, footers,
                       "Read more"), unescape HTML entities, normalize whitespace
  chunk_text()      -> paragraph-aware packing to ~600 chars with 100-char overlap

Run `python ingest.py` to clean + chunk every document and print 5 sample chunks
plus the total count (the Milestone 3 inspection step).
"""

import html
import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "documents"

# Chunking parameters — see planning.md "Chunking Strategy".
# These documents are short, tip-dense reviews/threads (~1.3–1.7k chars each), so a
# small target keeps one self-contained tip per chunk and yields fine-grained recall.
TARGET_CHARS = 350   # aim to pack paragraphs up to this size
MAX_CHARS = 550      # hard cap; a single paragraph longer than this is char-split
OVERLAP = 70         # characters of overlap carried between consecutive chunks
MIN_CHARS = 120      # chunks shorter than this (e.g. lone titles) are merged into a neighbor


# --- Cleaning -------------------------------------------------------------

# A line is dropped if it matches any of these boilerplate patterns. These were
# derived by reading the raw documents (forum chrome, wiki toolbars, blog footers).
_BOILERPLATE_PATTERNS = [
    r"^\s*(home|navigation|table of contents)\b.*[\|>]",   # nav bars / breadcrumbs
    r"\bsign in to comment\b",
    r"\b(log\s?in|sign\s?up)\b.*\]",                        # auth chrome
    r"\bposted (by|in)\b",                                  # "Posted by u/... / in r/..."
    r"\bupvotes?\b.*•",                                     # "342 upvotes • 87 comments •"
    r"^\s*upvote\b.*\bdownvote\b",                          # vote bar
    r"\(\s*\d+\s*points?\s*\)",                             # "(212 points)" reply markers
    r"^\s*reply\s*↳",                                       # reply arrow markers
    r"\bread more\b",                                       # "[Read more]" / "Read more ▼"
    r"\b(was this (helpful|guide useful)|found this (helpful|useful)|reactions)\b",
    r"\bshare on\b",                                        # social share rows
    r"^\s*\[?\s*(print|share|report|save|hide)\b",          # toolbar rows
    r"\b(load more|view \d+ more|continue this thread|older posts|crosspost)\b",
    r"\b(last (edited|updated|revised)|page views)\b",      # wiki/blog footers
    r"\bedit \| history\b|\[ ?edit this page ?\]",          # wiki toolbars
    r"^\s*sort(ed)? (by)?\s*:",                             # "Sorted by: Top"
    r"\bcookie (preferences|settings)\b",
    r"©",                                                   # copyright footers
    r"^\s*comments?\s*\(\d+\)\s*$",                         # "Comments (43)"
    r"^\s*search the wiki",
    r"\bsubscribe to\b",
    r"\badd a (comment|correction)\b",
    r"\bback to (top|housing|incoming)",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE_PATTERNS), re.IGNORECASE)

# Inline junk to delete even when a line is otherwise good content.
_INLINE_JUNK_RE = re.compile(r"\[\s*read more\s*\]|read more\s*[▼▾]|\bedit\b\s*\|", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Remove web boilerplate, unescape HTML entities, normalize whitespace."""
    text = html.unescape(text)  # &nbsp; &amp; &#39; -> real characters
    text = text.replace(" ", " ")  # leftover non-breaking spaces

    kept = []
    for line in text.splitlines():
        if _BOILERPLATE_RE.search(line):
            continue
        line = _INLINE_JUNK_RE.sub("", line)
        kept.append(line)

    text = "\n".join(kept)
    # collapse 3+ blank lines to a single blank line (paragraph separator)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    # strip trailing spaces on each line
    text = "\n".join(l.rstrip() for l in text.splitlines())
    return text.strip()


# --- Loading --------------------------------------------------------------

def load_documents(docs_dir: Path = DOCS_DIR):
    """Return [{source, raw}] for every .txt file, sorted by filename."""
    docs = []
    for path in sorted(docs_dir.glob("*.txt")):
        docs.append({"source": path.name, "raw": path.read_text(encoding="utf-8")})
    if not docs:
        raise FileNotFoundError(f"No .txt documents found in {docs_dir}")
    return docs


# --- Chunking -------------------------------------------------------------

def _char_split(paragraph: str, size: int):
    """Split an oversize paragraph into <=size pieces (overlap added later)."""
    return [paragraph[i:i + size].strip() for i in range(0, len(paragraph), size)]


def _apply_overlap(chunks, overlap: int):
    """Prepend the last `overlap` chars of each chunk to the next one.

    Trimmed to a word boundary so we don't start mid-word. This is what keeps a
    fact that straddles a chunk boundary retrievable from the following chunk.
    """
    if overlap <= 0 or len(chunks) < 2:
        return chunks
    out = [chunks[0]]
    for prev, cur in zip(chunks, chunks[1:]):
        tail = prev[-overlap:]
        space = tail.find(" ")
        if space != -1:
            tail = tail[space + 1:]
        out.append((tail + " " + cur).strip())
    return out


def _merge_short(chunks, min_chars: int):
    """Fold any chunk shorter than min_chars into the next chunk (or the previous
    one if it's the last). Stops lone title/heading lines from becoming fragments."""
    if min_chars <= 0:
        return chunks
    merged = []
    carry = ""
    for c in chunks:
        c = (carry + "\n\n" + c).strip() if carry else c
        carry = ""
        if len(c) < min_chars:
            carry = c            # too short — push it onto the next chunk
        else:
            merged.append(c)
    if carry:                    # leftover short tail -> attach to previous
        if merged:
            merged[-1] = (merged[-1] + "\n\n" + carry).strip()
        else:
            merged.append(carry)
    return merged


def chunk_text(text, source, target=TARGET_CHARS, max_size=MAX_CHARS, overlap=OVERLAP):
    """Paragraph-aware chunking. Returns [{text, source, chunk_index}]."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    raw_chunks = []
    current = ""
    for para in paragraphs:
        if len(para) > max_size:
            if current:
                raw_chunks.append(current)
                current = ""
            raw_chunks.extend(_char_split(para, max_size))
        elif not current:
            current = para
        elif len(current) + 2 + len(para) <= target:
            current += "\n\n" + para
        else:
            raw_chunks.append(current)
            current = para
    if current:
        raw_chunks.append(current)

    raw_chunks = [c.strip() for c in raw_chunks if len(c.strip()) > 0]
    raw_chunks = _merge_short(raw_chunks, MIN_CHARS)
    raw_chunks = _apply_overlap(raw_chunks, overlap)

    return [
        {"text": c, "source": source, "chunk_index": i}
        for i, c in enumerate(raw_chunks)
    ]


def build_chunks(docs_dir: Path = DOCS_DIR):
    """Full ingestion: load -> clean -> chunk every document. Returns flat list."""
    all_chunks = []
    for doc in load_documents(docs_dir):
        cleaned = clean_text(doc["raw"])
        all_chunks.extend(chunk_text(cleaned, doc["source"]))
    return all_chunks


# --- Inspection (Milestone 3 checkpoint) ----------------------------------

if __name__ == "__main__":
    import random

    docs = load_documents()
    chunks = build_chunks()

    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks "
          f"(target {TARGET_CHARS} chars, {OVERLAP} overlap)\n")

    lengths = [len(c["text"]) for c in chunks]
    print(f"Chunk length  min={min(lengths)}  max={max(lengths)}  "
          f"avg={sum(lengths) // len(lengths)}")
    if not (50 <= len(chunks) <= 2000):
        print("  ⚠ chunk count outside the 50–2000 sanity range — revisit chunk size")
    print()

    random.seed(7)
    for c in random.sample(chunks, 5):
        print(f"--- {c['source']} [chunk {c['chunk_index']}] · {len(c['text'])} chars ---")
        print(c["text"])
        print()
