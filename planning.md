# RulesBot — Planning Doc

Use this file to record your design decisions as you work through the lab.
There are no wrong answers — write enough that you could explain your reasoning to another group.

---

## Chunking Strategy

**Chunk size:** 300 characters (sliding window, advance by chunk_size − overlap = 250).

**Overlap:** 50 characters, so a rule that straddles a boundary stays recoverable in one of the two chunks.

**Why this strategy fits rule book text:** Rule books are semantically dense — a
single rule is usually 1–3 sentences, which fits in ~300 chars. Smaller windows
fragment a rule into meaningless pieces; larger ones merge unrelated rules and
blur retrieval. Across the 8 books this produced 149 chunks. The known cost is
that character-based splitting ignores sentence boundaries (chunks start
mid-sentence), which is why distances run higher than textbook examples — but
the right game still ranks first, which is what matters.

---

## Retrieval Observations

After implementing retrieval, try these test queries and record what comes back:

| Query | Top result game | Does it make sense? |
|-------|----------------|---------------------|
| "How do you win?" | Monopoly (0.507), then Risk (0.509), Ticket to Ride (0.522) | Yes — winning conditions exist in every game, so an even spread of near-tied games is correct semantic search, not a failure. |
| "What happens when you roll a 7?" | Catan (0.466) | Yes — Catan is the top hit (the no-resources rule); Risk dice chunks follow because "roll dice" is loosely related. |
| "What happens when you run out of disease cubes in Pandemic?" | Pandemic (0.373) | Yes — all 3 results are Pandemic, top one is the exact loss-condition rule. Specific, game-named queries retrieve cleanly. |

**Anything surprising?** Absolute distance scores were higher than the lab's
example numbers (~0.4–0.5 vs ~0.14). That's a property of the character-based
chunker, not a bug — rankings are still correct. Distance is meaningful
*relative to your own chunking*, not on a universal scale.


---

## Response Quality

After implementing generation, try 2–3 questions and assess the answers:

| Query | Answer accurate? | Properly grounded? | Cited the right game? |
|-------|-----------------|-------------------|----------------------|
| "How do you get out of Jail in Monopoly?" | Yes — $50 fine / Get Out of Jail Free card / roll doubles, 3-turn limit | Yes — every detail is in the retrieved Monopoly chunks | Yes — "According to the Monopoly rules…" |
| "What is the best opening chess move?" (not in corpus) | N/A — correctly refused | Yes — said the loaded books don't cover it instead of guessing | N/A — flagged sources were Risk/Clue, not chess |

**What would you change about the prompt to improve grounding?** It already
holds well on both the in-corpus and out-of-corpus tests, so no change needed
for correctness. If pushing further: ask the model to quote the specific
source label it used (e.g. "[Source 2 — Monopoly]") so citations are traceable
to an exact chunk, not just the game — useful for debugging retrieval vs.
generation failures.

