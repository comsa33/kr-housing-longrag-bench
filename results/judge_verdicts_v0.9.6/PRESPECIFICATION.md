# Pre-specification document: k=50 + announcement page on the 18 uncovered items

The text below is copied verbatim from the paper's results registry (shared/roadmap/03_results_registry_v09.md
in the paper repository), as committed before any generation call of this run. The registry heading says
"Pre-registered"; no external registry was used, so this paper and release call it a pre-specification.

- Written on 2026-10-12, before any generation call of this run.

---

### Pre-registered (2026-10-12, before any generation call): k=50 + announcement page on the 18 uncovered items (user: run now, decide later whether to report)
- Items: the 18 aggregation items whose k=50 passages lack the announcement page (two pairs: LH 0000061086 × HUG, LH 0000061016 × HUG; registry 1ab0cca). The other 63 items already contain the page, so their prompts would not change.
- Prompt: the exact k=50 prompt of each item (same bge-m3 passages, v0.9.2 chunker, same template), with the item's gold announcement page added as one more passage in reading order. Nothing else changes.
- Models and settings: the six full-window models with their k=50 settings (minimax-m3 reasoning on, as reported; glm-5.2 reasoning on), same caps (gpt-5.5 16,000; Claude 16,384; glm 16,384; minimax 32,768), Ollama num_ctx 131,072; OpenAI/Anthropic via Batch APIs; empty answers: one retry at a doubled cap, still-empty counts wrong; every empty or capped answer is reported.
- Judges: primary claude-sonnet-5-5 and secondary gpt-4.1-mini (Batch); the four panel judges on the Claude predictions.
- Reported quantity: correct of 18 per model under the primary judge, next to k=50 (0 of 18 for every model) and open-region (18/18/17/17/7/2). No interval (two pairs). Secondary and panel counts alongside. Descriptive wording only; any write-up must keep the two-announcement caveat.
- Whether the result enters the manuscript is decided after the run; the result is recorded here whichever way it falls.
