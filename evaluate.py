"""
Milestone 6 — Evaluation harness.

Runs the 5 test questions from planning.md through the full system and prints, for
each: the question, the expected answer, the retrieved chunks (source + distance),
and the system's generated response. Use the output to fill the README eval table.

Run:  python evaluate.py            (needs GROQ_API_KEY in .env)
      python evaluate.py --retrieval-only   (no LLM/key; retrieval inspection only)
"""

import sys

from rag import answer, retrieve

# (question, expected answer) — mirrors planning.md "Evaluation Plan".
EVAL = [
    (
        "I got waitlisted for a class I need — will I actually get in, and what should I do?",
        "Waitlists usually clear within the first week; attend the first 1-2 lectures and "
        "email the professor (not the registrar). Only the professor/department issues "
        "permission numbers.",
    ),
    (
        "Which dining hall should I go to if I only have 15 minutes for lunch?",
        "Hillcrest Market — grab-and-go, almost no wait, takes a regular meal swipe. "
        "Avoid Northgate Commons 12-1 PM.",
    ),
    (
        "Where's the best place to study in total silence during finals?",
        "The 4th floor of Carver Library (designated silent floor). NOT the 1st floor "
        "(social/group floor).",
    ),
    (
        "Is bringing a car my first year worth it, and how else do I get around?",
        "Generally not worth it — permits are a lottery (~1,200 spots, $480/yr) and losers "
        "get the far Outer West lot. Use the free Gold Line shuttle, bike, or Zipcar.",
    ),
    (
        "What time does the campus gym close on weekends?",
        "The Rec Center closes 8 PM Saturdays and isn't open before noon Sundays "
        "(weekday hours 6 AM-11 PM).",
    ),
]

# An out-of-scope question to verify the system refuses instead of hallucinating.
OUT_OF_SCOPE = "Who is the head coach of the Lakemont football team?"


def main(retrieval_only=False):
    for i, (q, expected) in enumerate(EVAL, 1):
        print(f"\n{'=' * 78}\nQ{i}: {q}")
        print(f"EXPECTED: {expected}\n")

        chunks = retrieve(q)
        print("RETRIEVED:")
        for c in chunks:
            print(f"  • {c['source']} (chunk {c['chunk_index']}) · distance={c['distance']:.3f}")

        if not retrieval_only:
            result = answer(q)
            print(f"\nSYSTEM ANSWER:\n{result['answer']}")
            print(f"\nSOURCES: {', '.join(result['sources'])}")

    if not retrieval_only:
        print(f"\n{'=' * 78}\nOUT-OF-SCOPE CHECK: {OUT_OF_SCOPE}")
        print(f"\nSYSTEM ANSWER:\n{answer(OUT_OF_SCOPE)['answer']}")


if __name__ == "__main__":
    main(retrieval_only="--retrieval-only" in sys.argv)
