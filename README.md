# The Unofficial Lakemont Guide — Project 1

A RAG system that makes scattered, student-to-student campus knowledge searchable and
answerable, with cited, grounded responses.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then paste your free Groq key (console.groq.com)
python rag.py build             # embed documents -> ChromaDB
python app.py                   # Gradio UI at http://localhost:7860
```

Other entry points: `python rag.py retrieve "question"` (retrieval only, no key needed),
`python rag.py ask "question"` (full answer), `python evaluate.py` (the 5-question report).

| File | Role |
|------|------|
| `ingest.py` | load → clean → chunk (Milestone 3) |
| `rag.py` | embed + ChromaDB store, `retrieve()`, grounded `answer()` (Milestones 4–5) |
| `app.py` | Gradio query interface (Milestone 5) |
| `evaluate.py` | runs the 5 eval questions + out-of-scope check (Milestone 6) |

---

## Domain

**The Unofficial Lakemont Survival Guide** — the practical, experiential knowledge students pass to each other to survive a specific campus (fictional *Lakemont University*): registration tricks, dining wait times, study spots, transit/parking, on- and off-campus housing, picking professors, health services, money-saving, clubs, late-night safety, and what to bring.

This knowledge is valuable because it's **experiential and time-sensitive** ("the waitlist clears in the first week," "Hillcrest takes a meal swipe," "Sumner Property won't return your deposit") and **scattered** across subreddit megathreads, student wikis, and blog posts. The official catalog and admissions site never carry it. This system makes that diffuse oral tradition queryable *and* cited, so an answer traces back to where students actually said it.

> The documents are realistic samples written for this project against a **fictional** university, so the pipeline runs end-to-end without scraping JS-rendered/blocked sites or fabricating claims about real, named people. Architecture is identical for real documents — drop real `.txt` files into `documents/` and re-run `python rag.py build`.

---

## Document Sources

12 documents (exceeds the 10 minimum), each authored in the style of its real-world source type, **including authentic web noise** (nav menus, upvote/share bars, "Read more", `&nbsp;`/`&amp;` entities, footers) so the cleaning stage is meaningful.

| #  | Source | Type | File path |
|----|--------|------|-----------|
| 1  | r/LakemontUniversity megathread | Reddit-style thread | `documents/01_course_registration.txt` |
| 2  | Student dining review wiki | Wiki | `documents/02_dining_halls.txt` |
| 3  | Study-spot guide | Blog post | `documents/03_study_spots.txt` |
| 4  | r/LakemontUniversity thread | Reddit-style thread | `documents/04_transit_parking.txt` |
| 5  | On-campus housing review wiki | Wiki | `documents/05_dorms_housing_oncampus.txt` |
| 6  | Off-campus housing thread archive | Reddit-style thread | `documents/06_offcampus_housing.txt` |
| 7  | Advising wiki | Wiki | `documents/07_picking_professors.txt` |
| 8  | Student wellness FAQ | FAQ | `documents/08_health_wellness.txt` |
| 9  | r/LakemontUniversity thread | Reddit-style thread | `documents/09_saving_money.txt` |
| 10 | Student Life blog | Blog post | `documents/10_clubs_social.txt` |
| 11 | Campus safety FAQ | FAQ | `documents/11_safety_latenight.txt` |
| 12 | Incoming-student guide | Guide | `documents/12_weather_firstweek.txt` |

Sources deliberately span academics, food, housing, transit, money, health, social, and safety so the corpus answers a *range* of questions.

### Ingestion pipeline (how raw docs become clean text)

`ingest.py` does three things (`build_chunks()` chains them):
1. **`load_documents()`** — reads every `.txt` in `documents/`.
2. **`clean_text()`** — `html.unescape()` for entities, then drops any line matching a boilerplate regex set derived by reading the raw files (nav bars, `Posted by u/…`, `342 upvotes • … • Share`, `(212 points)` reply markers, `Read more`, `Was this helpful`, `© …`, `Last edited / Page views`, wiki toolbars, `Sorted by:`, share rows), then collapses whitespace.
3. **`chunk_text()`** — paragraph-aware chunking (below).

---

## Chunking Strategy

**Chunk size:** 350-char target, 550-char hard cap. **Overlap:** 70 chars. Lone title lines under 120 chars are merged into a neighbor so no chunk is a fragment.
**Preprocessing before chunking:** the full `clean_text()` pass above.
**Final chunk count:** **61 chunks** across 12 documents (avg 337 chars, min 123, max 527).

**Why these choices fit the documents.** These are short, tip-dense reviews/threads (1.3–1.7k cleaned chars each). The natural semantic unit is one *paragraph/reply* — one self-contained tip ("Hillcrest is grab-and-go, almost no wait, takes a meal swipe"). So I split on blank lines and greedily pack paragraphs up to ~350 chars; a paragraph already near that size becomes its own chunk.

- **Not 200:** would slice one tip into fragments ("Hillcrest is grab-and-go" / "takes a meal swipe") that match a query but can't answer it.
- **Not 1500+:** several docs bundle unrelated topics (the wellness FAQ has health center + CAPS + gym + pharmacy); one giant chunk blurs four topics into one diluted embedding. Small chunks preserve topical focus — this is exactly why Q5 ("gym weekend hours") retrieved cleanly at distance 0.236.
- **70-char overlap:** a fact occasionally straddles a paragraph break; overlap keeps the second half retrievable.

> *Diverged from planning.md:* I first specced ~600/100 but that produced only 40 chunks — under the 50 sanity floor and coarser than these reviews warrant. Lowered to 350/70 → 61 chunks. planning.md was updated to match.

### Sample chunks (5, labeled with source)

**1 — `01_course_registration.txt` [chunk 0]:**
> MEGATHREAD: How to actually get into full classes at Lakemont … waitlists almost always clear within the first week of classes. Do NOT panic if you get waitlisted #15. Professors over-enroll because they know 10-20% of people drop … show up to the first two lectures … and email the professor a short polite note saying you're on the waitlist and attending.

**2 — `02_dining_halls.txt` [chunk 2]:**
> Hillcrest takes a regular meal swipe, not just dining dollars. The Lakeside Cafe has the best actual food quality — made-to-order pasta and a rotating chef special — but it's small, gets loud, and the made-to-order line is slow. Worth it for dinner, not for a quick lunch.

**3 — `05_dorms_housing_oncampus.txt` [chunk 0]:**
> Lakemont On-Campus Housing — The Honest Dorm Tier List … Tier S: Riverside Hall. Newest dorm, built 2019. Air conditioning (rare on this campus!), suite-style … The catch: it's the farthest dorm from the academic core, a solid 12-minute walk. You trade convenience for comfort.

**4 — `06_offcampus_housing.txt` [chunk 2]:**
> … the shuttle only runs there until 7 PM, so plan around that. Biggest warning: start looking in JANUARY for a September lease. The good units in College Park are gone by February. People who wait until summer get stuck with the leftover units that didn't rent for a reason.

**5 — `09_saving_money.txt` [chunk 0]:**
> Broke at Lakemont: The Money-Saving Survival Thread. Textbooks first … NEVER buy from the campus bookstore at list price … (1) the Carver Library Reserve Desk lends the required textbook for most large intro courses for free — 2-hour in-library loans … The bookstore should be your absolute last resort.

Each chunk is readable, substantive, and self-contained — no HTML, no nav text, no fragments.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` — runs locally, no API key, no rate limits, 384-dim, fast on CPU. More than enough for a 61-chunk corpus, and keeps the whole retrieval path free and private.

**Production tradeoff reflection.** If this served real students and cost weren't a constraint, I'd weigh:
- **Accuracy on domain text** — a larger model (`bge-large`, OpenAI `text-embedding-3-large`, Voyage) better captures campus slang/nicknames ("the Rec", "the Gold Line") that MiniLM may under-represent. This is directly relevant to my failure case below.
- **Context length** — MiniLM truncates at ~256 tokens; longer guides would need a bigger window or careful chunking.
- **Multilingual** — an international student body would justify a multilingual model (`paraphrase-multilingual-MiniLM`, Cohere multilingual).
- **Local vs. API + latency** — local MiniLM is zero-cost and private but caps quality; an API model improves recall at the cost of money, latency, and sending student data off-box.

For a real campus tool I'd likely **stay local** for privacy/cost and instead improve recall with **hybrid search (semantic + BM25)** rather than a heavier embedding model.

Semantic search works without shared words because embeddings place *meaning* nearby: "Is the housing lottery rigged?" lands near "the lottery IS random within your class year … 'random' has an asterisk."

---

## Grounded Generation

**LLM:** Groq `llama-3.3-70b-versatile` (free tier), `temperature=0`.

**System prompt grounding instruction** (in `rag.py`, enforced not suggested):

> You answer student questions using ONLY the numbered context passages provided. … (1) Use ONLY information stated in the context. Do NOT use any outside or general knowledge. (2) If the context does not contain enough information, reply exactly: "I don't have enough information on that in the Unofficial Guide." Do not guess. (3) After your answer add a "Sources:" line listing the [source] filenames you actually used.

**Structural choices that reinforce grounding:**
- Each retrieved chunk is passed as a numbered block tagged `(source: filename)`, so the model has explicit, attributable units to cite.
- **Source attribution is guaranteed programmatically**: `answer()` returns `sources` built from the retrieved chunks' metadata, independent of whether the model remembers to print its own "Sources:" line. The UI shows this guaranteed list *plus* the retrieved passages with distances.
- The explicit refusal string gives the model a grounded "out" — verified working (see out-of-scope test below), so it declines instead of hallucinating.

> *Honest limitation:* the programmatic `sources` list is the set of all *retrieved* chunks, which can over-attribute (e.g. Q5 lists 4 sources though the answer used only one). The model's own inline citation is more precise but not guaranteed. A production version would intersect the two.

---

## Retrieval Test Results

Top-k = 4, cosine distance (lower = more similar). Full output: `python evaluate.py --retrieval-only`.

| Query | Top result (source · distance) | Retrieval quality |
|-------|-------------------------------|-------------------|
| Q1 waitlist | `01_course_registration.txt` ch0 · **0.383** | Relevant |
| Q2 fast lunch | `02_dining_halls.txt` ch0 · **0.304** | Relevant |
| Q3 silent study | `03_study_spots.txt` ch0 · **0.351** | Relevant |
| Q4 car / getting around | `04_transit_parking.txt` ch1 · **0.439** | Partially relevant |
| Q5 gym weekend hours | `08_health_wellness.txt` ch3 · **0.236** | Relevant |

**Why the retrieved chunks are relevant (3 explained):**

- **Q2 (fast lunch):** all four chunks come from `02_dining_halls.txt`, and the top one (0.304) directly contrasts dining halls by wait time — Northgate's 20-25 min lunch line vs. the alternatives. The chunk naming Hillcrest as grab-and-go is also retrieved. The query shares almost no exact words with "grab-and-go," yet semantic similarity surfaces the right passage.
- **Q3 (silent study):** top chunk (0.351) literally opens "If you want SILENCE, go to the 4th floor of Carver Library … designated silent floor." Exactly the needed fact; the contrasting "1st floor is the social floor" chunk is also pulled.
- **Q5 (gym weekend hours):** strongest match in the whole eval (0.236). Even though this chunk sits in a doc covering health center, CAPS, and pharmacy, small chunking isolated the Rec Center hours into their own chunk, so it dominates the query cleanly — direct evidence that the chunking strategy worked.

---

## Example Responses (with source attribution)

**In-scope #1 — Q2:**
> **Q:** Which dining hall should I go to if I only have 15 minutes for lunch?
> **A:** If you only have 15 minutes for lunch, you should go to Hillcrest Market. It's grab-and-go style with almost no wait, even at noon.
> **Sources:** `02_dining_halls.txt`

**In-scope #2 — Q5:**
> **Q:** What time does the campus gym close on weekends?
> **A:** On Saturdays, the campus gym (Rec Center) closes at 8 PM, and on Sundays, it isn't open until noon.
> **Sources:** `08_health_wellness.txt` (+ retrieved: 03, 06, 11)

**Out-of-scope (refusal) — verified:**
> **Q:** Who is the head coach of the Lakemont football team?
> **A:** I don't have enough information on that in the Unofficial Guide.
> **Sources:** *(none)*

The system declines on out-of-scope queries rather than inventing a plausible answer from training data.

---

## Query Interface

A **Gradio** web UI (`python app.py` → http://localhost:7860).

- **Input:** one textbox, "Your question" (Enter or the **Ask** button submits). Five example questions are clickable.
- **Output fields:** **"Answer"** (the grounded response) and **"Retrieved from (grounding)"** (the programmatic source list *plus* each retrieved passage with its source, chunk index, and distance — so grounding is visible, not trust-me).

**Sample interaction transcript:**
```
Your question:  Is bringing a car my first year worth it?

Answer:
It's not worth bringing a car your first year. There are only about 1,200 parking
permits available for a large number of applicants, and even if you pay $480/year,
you might still end up in the Outer West lot — a 15-minute walk from the academic core.

Retrieved from (grounding):
Sources: 04_transit_parking.txt
--- retrieved passages ---
• 04_transit_parking.txt (chunk 1, distance 0.439)  Student parking permits are sold by lottery…
• 04_transit_parking.txt (chunk 0, distance 0.482)  Hot take: do not bring a car your first year…
```

---

## Evaluation Report

Run with `python evaluate.py`. All 5 questions, expected vs. actual, honest judgments:

| # | Question | Expected | System response (summary) | Retrieval | Accuracy |
|---|----------|----------|---------------------------|-----------|----------|
| 1 | Waitlisted for a class I need — will I get in, what do I do? | Clears in first week; attend + email the professor (not registrar); only prof issues permission # | Show up to first 2 lectures, email the professor; profs over-enroll & 10-20% drop, so most get in | Relevant | **Accurate** (omits the registrar-vs-professor nuance, but core advice correct & grounded) |
| 2 | Dining hall for a 15-min lunch? | Hillcrest (grab-and-go, meal swipe); avoid Northgate 12–1 | Hillcrest Market — grab-and-go, almost no wait | Relevant | **Accurate** |
| 3 | Best place for total silence at finals? | 4th floor Carver (silent floor), not 1st | 4th floor Carver Library, designated silent floor | Relevant | **Accurate** |
| 4 | Is a car worth it, and how else do I get around? | Not worth it (permit lottery, $480, Outer West); use Gold Line shuttle / bike / Zipcar | Car not worth it (correct); "how else": **local bus is free** — wrong alternative | Partially relevant | **Partially accurate** ⚠️ |
| 5 | When does the gym close on weekends? | Sat 8 PM, not open before noon Sun | Sat closes 8 PM, Sun opens noon | Relevant | **Accurate** |

**Out-of-scope check:** "Who is the head coach…?" → correct refusal. ✅

4 of 5 fully accurate; **Q4 is a genuine partial failure** (analyzed next). Note Q5 — which I *designed* in planning.md to be the hard/failure case — actually succeeded, because small chunking isolated the gym hours. The real failure showed up somewhere I didn't predict, which is the point of evaluating honestly.

---

## Failure Case Analysis

**Question that failed:** Q4 — *"Is bringing a car my first year worth it, and how else do I get around?"*

**What the system returned:** It got the first half right (car not worth it — permit lottery, $480, far Outer West lot), but answered the second half — *how else to get around* — with **"you can use the local bus for free with your student ID."** The corpus's actual answer to that half is the **free Gold Line shuttle (every 10 min), biking, and Zipcar** in `04_transit_parking.txt`. The "local bus" line is a real but minor detail lifted from the *money-saving* doc.

**Root cause (retrieval stage, propagated to generation).** This is a **compound query** whose "is a car worth it" framing is semantically about parking/permits. With top-k=4, retrieval returned the two parking chunks of `04_transit_parking.txt` (0.439, 0.482) plus two weak off-target chunks — including `09_saving_money.txt` ch2 (0.669) which happens to contain "local bus is free." The chunk that actually answers "how else do I get around" — `04_transit_parking.txt` ch2, the Gold Line shuttle / bike / Zipcar reply — **ranked #12 at distance 0.759**, far outside top-4, because the dominant "car worth it" signal pushed the alternative-transit chunk down. The LLM grounded faithfully on what it was *given*, so it surfaced the only transit alternative present (the bus) — a grounded but incomplete/misleading answer. **Bad retrieval, not bad generation.**

**What I'd change to fix it:**
1. **Raise top-k** (e.g. 6–8) so a two-part question has room for both halves — cheap, immediate.
2. **Query decomposition / multi-query**: split a compound question into "is a car worth it" + "how else to get around," retrieve for each, and merge — directly addresses the cause.
3. **MMR / diversity re-ranking** so results aren't all near-duplicates of the dominant facet.
4. **Hybrid (BM25 + semantic)**: the keyword "shuttle"/"bus"/"bike" would lexically rank the transit-alternatives chunk higher than a semantic-only score does.

---

## Spec Reflection

> *Drafted from what happened during the build — rewrite in your own voice before submitting (per the course AI guardrail).*

**One way the spec helped me during implementation.** Writing the Chunking Strategy and Architecture sections *first* meant the ingestion/chunking code had concrete targets (paragraph-aware, ~size, overlap, per-stage tools) instead of me guessing mid-code. When the first numbers produced too few chunks, I had a written rationale to revise against rather than starting over — I changed one parameter and updated the rationale, not the whole approach.

**One way my implementation diverged from the spec, and why.** planning.md specced ~600-char chunks with 100 overlap, but that yielded only 40 chunks — below the 50-chunk sanity floor and too coarse for these short reviews. I lowered the target to 350/70 (→ 61 chunks), which keeps one self-contained tip per chunk, and updated planning.md to match. I also *predicted the wrong failure case*: I designed Q5 (gym hours) to fail via topic dilution, but small chunking made it the **best** retrieval in the set (0.236); the genuine failure surfaced at Q4's compound query instead.

---

## AI Usage

> *Drafted — replace with your own specific instances and edits before submitting (per the course AI guardrail).*

**Instance 1 — ingestion & chunking**
- *What I gave the AI:* the Documents and Chunking Strategy sections of planning.md (file types, the boilerplate/noise examples present in the raw docs, target ~size + overlap) and asked it to implement `load → clean → chunk` with an inspection mode.
- *What it produced:* `ingest.py` with regex boilerplate stripping, HTML unescaping, and paragraph-aware packing.
- *What I changed / directed:* after the first run produced 40 chunks (under the 50 floor) with a 51-char fragment, I directed lowering the target to 350/70 **and** adding a `_merge_short()` step so lone title lines fold into a neighbor instead of becoming fragments — then re-ran the inspection to confirm min length 123 and 0 fragments.

**Instance 2 — grounded generation**
- *What I gave the AI:* the grounding requirement (answer from retrieved context only; exact refusal string; guaranteed source attribution) and the desired return shape.
- *What it produced:* `answer()` with a strict system prompt and a Groq call.
- *What I changed / directed:* I required source attribution be built **programmatically** from chunk metadata rather than trusting the model's self-citation, and verified the refusal path with a real out-of-scope query rather than assuming it worked. I also kept `temperature=0` for reproducible eval results.
