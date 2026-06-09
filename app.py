"""
Milestone 5 — Gradio query interface for The Unofficial Lakemont Guide.

Run:  python app.py   then open http://localhost:7860
(Requires the vector store to exist — run `python rag.py build` first, and set
GROQ_API_KEY in .env for generation.)
"""

import gradio as gr

from rag import answer


def handle_query(question):
    question = (question or "").strip()
    if not question:
        return "Type a question above and press Ask.", ""

    try:
        result = answer(question)
    except RuntimeError as e:          # missing API key, etc.
        return f"⚠ {e}", ""

    # Show which chunks were retrieved, with their source + distance, so the
    # grounding is visible in the demo (not just trust-me sourcing).
    retrieved = "\n\n".join(
        f"• {c['source']} (chunk {c['chunk_index']}, distance {c['distance']:.3f})\n"
        f"  {c['text'][:160]}{'…' if len(c['text']) > 160 else ''}"
        for c in result["chunks"]
    )
    sources = "Sources: " + ", ".join(result["sources"])
    return result["answer"], f"{sources}\n\n--- retrieved passages ---\n\n{retrieved}"


with gr.Blocks(title="The Unofficial Lakemont Guide") as demo:
    gr.Markdown(
        "# 🎓 The Unofficial Lakemont Guide\n"
        "Ask a question about surviving campus — registration, dining, housing, "
        "transit, study spots, money, health, safety. Answers come **only** from "
        "collected student documents, with sources shown."
    )
    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. Which dining hall is fastest at lunch?",
    )
    btn = gr.Button("Ask", variant="primary")
    answer_box = gr.Textbox(label="Answer", lines=8)
    sources_box = gr.Textbox(label="Retrieved from (grounding)", lines=12)

    gr.Examples(
        examples=[
            "I got waitlisted for a class I need — what should I do?",
            "Which dining hall should I go to if I only have 15 minutes for lunch?",
            "Where's the best place to study in total silence during finals?",
            "Is bringing a car my first year worth it?",
            "What's the cheapest way to get textbooks?",
        ],
        inputs=inp,
    )

    btn.click(handle_query, inputs=inp, outputs=[answer_box, sources_box])
    inp.submit(handle_query, inputs=inp, outputs=[answer_box, sources_box])


if __name__ == "__main__":
    demo.launch()
