# Project 1 Planning: The Unofficial Guide

> Written before implementation. The Chunking Strategy and Retrieval Approach sections are
> updated to reflect the numbers actually used in code (noted inline where they changed).

---

## Domain

**The Unofficial Lakemont Survival Guide** — the practical, student-to-student knowledge you need to navigate a specific campus (fictional *Lakemont University*) that you cannot get from the official course catalog or admissions website. It spans registration tricks, dining hall wait times, study spots, transit/parking, on- and off-campus housing, picking professors, health services, money-saving, clubs, late-night safety, and what to bring.

This knowledge is valuable because it is **experiential and time-sensitive** — "the waitlist clears in the first week," "Hillcrest takes a meal swipe," "Sumner Property won't return your deposit." None of it appears in official channels, and it is **scattered** across subreddit megathreads, student-run wikis, blog posts, and word of mouth. A new student has the questions but no single searchable place to ask them. This system makes that diffuse oral tradition queryable and, critically, **cited** — so an answer can be traced back to where students actually said it.

> Note: documents are realistic samples authored for this project against a **fictional** university, so the pipeline runs end-to-end without scraping JS-rendered/blocked sites or fabricating claims about real, named people. The architecture is identical for real collected documents — drop real `.txt` files into `documents/` and re-run ingestion.

---

## Documents

12 documents (exceeds the 10 minimum), each written in the style and structure of its real-world source type, including authentic web noise (nav menus, upvote counts, "Read more", `&nbsp;`/`&amp;` entities, footers) so the cleaning stage is meaningful.

| #  | Source | Description | URL or location |
|----|--------|-------------|-----------------|
| 1  | r/LakemontUniversity megathread | Course registration / waitlist tactics | `documents/01_course_registration.txt` |
| 2  | Student dining wiki | Dining hall comparison, wait times, meal-swipe rules | `documents/02_dining_halls.txt` |
| 3  | Study-spot guide (blog) | Library floors, quiet vs. social, 24-hr spaces | `documents/03_study_spots.txt` |
| 4  | r/LakemontUniversity thread | Transit, parking permit lottery, shuttle, biking | `documents/04_transit_parking.txt` |
| 5  | Housing review wiki | On-campus dorm tier list, AC, laundry, lottery | `documents/05_dorms_housing_oncampus.txt` |
| 6  | Reddit thread archive | Off-campus neighborhoods, landlord warnings, leases | `documents/06_offcampus_housing.txt` |
| 7  | Advising wiki | How to choose professors / sections / exam style | `documents/07_picking_professors.txt` |
| 8  | Student-written wellness FAQ | Health center, CAPS, gym hours, pharmacy | `documents/08_health_wellness.txt` |
| 9  | r/LakemontUniversity thread | Textbooks, free food, student discounts, printing | `documents/09_saving_money.txt` |
| 10 | Student Life blog | Clubs, intramurals, making friends, Greek life | `documents/10_clubs_social.txt` |
| 11 | Campus safety FAQ | Safe-walk, SafeRide van, blue-light phones | `documents/11_safety_latenight.txt` |
| 12 | Incoming-student guide | What to bring, weather, first-week logistics | `documents/12_weather_firstweek.txt` |

Sources deliberately cover **different subtopics** (academics, food, housing, transit, money, health, social, safety) so the corpus answers a *range* of questions rather than one topic repeated.

---

## Chunking Strategy

**Chunk size:** 350-character target, 550-character hard cap, measured in characters.
**Overlap:** 70 characters. Lone title/heading lines under 120 chars are merged into a neighbor so no chunk is a fragment.
**Final chunk count:** 61 chunks across 12 documents (avg 337 chars, min 123, max 527).

> *Updated during Milestone 3.* I first specced ~600/100 but the 12 documents are short (1.3–1.7k cleaned chars each) and that produced only 40 chunks — under the 50-chunk sanity floor and coarser than these tip-dense reviews warrant. I lowered the target to 350/70, which keeps one self-contained tip per chunk and yields 61.

**Reasoning:**
These documents are **mixed-structure**: forum threads made of discrete short replies (each reply is one self-contained tip) and wiki/blog guides made of medium paragraphs (each paragraph is one self-contained topic — "Northgate Commons is...", "Hillcrest Market is..."). The natural semantic unit in *both* is the paragraph/reply, so I chunk **paragraph-aware**: split on blank lines, then greedily pack whole paragraphs up to ~350 characters; a paragraph already near that size becomes its own chunk.

- **Why ~350, not 200:** A single tip is usually one full sentence-or-two ("Hillcrest is grab-and-go, almost no wait, takes a meal swipe, closes 8 PM"). 200-char chunks would slice that into "Hillcrest is grab-and-go" / "takes a meal swipe" — fragments that match a query but can't answer it. ~350 chars keeps one complete tip intact while staying review-sized.
- **Why not 1500+:** Several docs cover many unrelated topics (the wellness FAQ has health center + CAPS + gym + pharmacy). One huge chunk per doc would blur four topics into one diluted embedding, so a query about "gym weekend hours" competes with pharmacy text in the same vector. Small chunks preserve topical focus.
- **Why 70-char overlap:** A fact occasionally straddles a paragraph break (a tip and its caveat). Overlap means a chunk boundary doesn't permanently sever the second half from the first.
- **How I'd know it's wrong:** too small → retrieved chunks are sentence fragments and distances cluster high (>0.6) because each embedding is low-signal. Too large → the right doc is retrieved but the answer's specific detail is buried among unrelated text and the LLM picks the wrong line.

---

## Retrieval Approach

**Embedding model:** `all-MiniLM-L6-v2` via `sentence-transformers` — local, no API key, no rate limits, 384-dim, fast on CPU. Plenty for a 12-doc corpus.

**Top-k:** 4 (tunable; chosen as a default per the milestone guidance).

**Production tradeoff reflection:**
If cost weren't a constraint and this served real users I'd weigh: **(1) Accuracy on domain text** — a larger model (e.g. `bge-large`, OpenAI `text-embedding-3-large`, or Voyage) better captures slang/nicknames ("the Rec", "the Gold Line") that MiniLM may under-represent. **(2) Context length** — MiniLM truncates at 256 tokens; longer guides would need a model with a larger window or careful chunking. **(3) Multilingual** — an international student body would justify a multilingual model (`paraphrase-multilingual-MiniLM` or Cohere multilingual). **(4) Local vs. API + latency** — local MiniLM has zero per-query cost and no network hop but caps quality; an API model adds cost and latency but improves recall. For a campus tool I'd likely stay local for privacy/cost and instead improve recall with **hybrid search** (semantic + BM25) rather than a bigger embedding model.

Semantic search finds relevant chunks even without shared words because embeddings place *meaning* nearby in vector space — "is the housing lottery rigged?" lands near "the lottery IS random within your class year… 'random' has an asterisk" despite almost no word overlap.

---

## Evaluation Plan

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | I got waitlisted for a class I need — will I actually get in, and what should I do? | Waitlists usually clear within the first week; attend the first 1–2 lectures and email the **professor** (not the registrar) saying you're waitlisted and attending. Only the professor/department issues permission numbers. *(doc 01)* |
| 2 | Which dining hall should I go to if I only have ~15 minutes for lunch? | **Hillcrest Market** — grab-and-go, almost no wait even at noon, and it takes a regular meal swipe. Avoid Northgate Commons 12–1 PM (20–25 min line). *(doc 02)* |
| 3 | Where's the best place to study in total silence during finals? | **4th floor of Carver Library** — designated silent floor, carrels with outlets. *Not* the 1st floor (that's the social/group floor). *(doc 03)* |
| 4 | Is bringing a car my first year worth it, and how else do I get around? | Generally **not worth it** — permits are a lottery (~1,200 spots, $480/yr) and losers get the far Outer West lot. Use the free **Gold Line shuttle**, bike (register it), or Zipcar. *(doc 04)* |
| 5 | What time does the campus gym close on weekends? | The **Rec Center** closes **8 PM Saturdays** and isn't open **before noon Sundays** (weekday hours 6 AM–11 PM). *(doc 08 — single buried line; chosen as the hard/likely-failure case)* |

Q5 is intentionally adversarial: the answer is one sentence inside a doc that also covers the health center, CAPS, flu shots, and the pharmacy — a strong test of whether chunking kept the gym paragraph topically isolated enough to retrieve.

---

## Anticipated Challenges

1. **Topic dilution within a single document.** Several docs (wellness FAQ, money thread) bundle 4–5 unrelated tips. If a chunk merges them, a narrow query ("gym weekend hours") retrieves a chunk whose embedding is averaged across pharmacy/CAPS/flu text and the specific hours get buried. Mitigation: paragraph-aware chunking to keep one tip per chunk.

2. **Web-noise leaking into chunks.** Raw docs contain nav menus, upvote counts, "Read more", and HTML entities (`&nbsp;`, `&amp;`). If cleaning misses them, a chunk like "Upvote 198 • Share • Report" wastes an embedding and can be retrieved instead of real content. Mitigation: a cleaning pass that strips boilerplate lines and unescapes HTML entities, then manual inspection of 5 chunks.

3. **(bonus) Grounding leakage.** The LLM "knows" generic college advice from training data and may answer plausibly even when retrieval missed. Mitigation: a strict system prompt + an explicit "say you don't have enough information" fallback, tested with an out-of-scope query.

---

## Architecture

```
 ┌──────────────────┐   ┌───────────────┐   ┌────────────────────────┐   ┌──────────────┐   ┌─────────────────┐
 │  1. INGESTION    │   │ 2. CHUNKING   │   │ 3. EMBED + VECTOR STORE│   │ 4. RETRIEVAL │   │ 5. GENERATION   │
 │                  │   │               │   │                        │   │              │   │                 │
 │ load .txt from   │──▶│ paragraph-    │──▶│ all-MiniLM-L6-v2       │──▶│ top-k=4 by   │──▶│ Groq            │
 │ documents/       │   │ aware pack    │   │ (sentence-transformers)│   │ cosine sim   │   │ llama-3.3-70b   │
 │ clean: strip     │   │ ~600 chars,   │   │        │               │   │ + metadata   │   │ grounded prompt │
 │ nav/noise,       │   │ 100 overlap   │   │        ▼               │   │ (source,     │   │ + source        │
 │ unescape HTML    │   │ + source meta │   │   ChromaDB (local)     │   │  chunk idx)  │   │ attribution     │
 └──────────────────┘   └───────────────┘   └────────────────────────┘   └──────────────┘   └─────────────────┘
        ingest.py            ingest.py              rag.py: build_store()      rag.py: retrieve()     rag.py: answer()
                                                                                                  app.py (Gradio UI)
```

---

## AI Tool Plan

**Milestone 3 — Ingestion and chunking:** Tool: Claude (Claude Code). Input: the *Documents* table (file types/structure) + the *Chunking Strategy* section (paragraph-aware, ~600 char / 100 overlap) + the noise examples to strip. Expected output: `ingest.py` with `load_documents()`, `clean_text()`, and `chunk_text()` matching the spec, plus a `--inspect` mode that prints 5 chunks and the total count. Verify: run it, read 5 printed chunks against the "good chunk" bar, confirm 50–2000 total.

**Milestone 4 — Embedding and retrieval:** Tool: Claude. Input: the *Retrieval Approach* section + architecture diagram. Expected output: `build_store()` (embed all chunks with MiniLM, persist to ChromaDB with source + chunk-index metadata) and `retrieve(query, k)` returning chunks + sources + distances. Verify: query 3 eval questions, confirm top results are on-topic with distances < 0.5.

**Milestone 5 — Generation and interface:** Tool: Claude. Input: the grounding requirement (answer from retrieved context only; explicit "not enough information" fallback), desired output shape (answer + source list), and "use Gradio Blocks". Expected output: `answer()` that builds a grounded prompt for Groq `llama-3.3-70b-versatile` and returns `{answer, sources}`, plus `app.py`. Verify: read the system prompt to confirm grounding is *enforced* not suggested, source list built programmatically from retrieval, and test an out-of-scope query for a refusal.
