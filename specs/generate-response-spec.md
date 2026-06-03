# Spec: `generate_response()`

**File:** `generator.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user query and a list of retrieved rule chunks, generate a response that directly answers the question using only the retrieved text as context. The response must be grounded — it should not draw on the model's general knowledge of board games, only on what was retrieved.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's original question |
| `retrieved_chunks` | `list[dict]` | Ranked list of chunks from `retrieve()`, each with `"text"`, `"game"`, and `"distance"` |

**Output:** `str`

A plain string containing the response to show the user. The response should:
- Answer the question using only the retrieved rule text
- Identify which game the answer comes from
- Acknowledge clearly when the answer is not found in the loaded rules

Returns a fallback string (not an error) when `retrieved_chunks` is empty.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Context formatting

*How will you format the retrieved chunks before passing them to the LLM? Describe the structure — not the code. Consider: will you label chunks by game? Include distance scores? Separate chunks with delimiters?*

```
Each chunk becomes a clearly delimited, labeled block:

  [Source 1 — Catan]
  <chunk text>

  [Source 2 — Risk]
  <chunk text>

Blocks are separated by a blank line. Labeling each source by game is the key
choice: it gives the model the game name *inline with the text*, so it can
cite the right game and can notice when the sources don't match the question's
game. Numbering ("Source 1/2/3") helps the model keep distinct passages
separate instead of blending them.

I do NOT pass the distance scores into the prompt — a raw float is noise to
the model and could be misread as content. Relevance is handled by which
chunks made the top-k, not by showing numbers to the LLM.
```

---

### System prompt — grounding instruction

*Write the exact system prompt instruction you will use to prevent the model from answering beyond the retrieved text. This is the most important design decision in this function.*

```
"Answer using ONLY the rule text provided in the context below. Do not draw
on any outside knowledge or anything you know about board games from training
— even if you are confident the answer is something else. If the answer is
not contained in the provided rule text, say so explicitly: reply that the
loaded rule books don't cover it and do not guess or fill in the gap."

This is phrased as a *prohibition of a specific behavior* ("do not draw on
outside knowledge", "do not guess or fill in the gap"), not a vague goal like
"be accurate." The "even if you are confident the answer is something else"
clause closes the most common loophole: the model deciding its training
knowledge is better than the messy retrieved chunk.
```

---

### System prompt — citation instruction

*Write the exact instruction you will use to tell the model to identify which game its answer comes from.*

```
"Always state which game your answer comes from (cite the game named in the
source label, e.g. \"According to the Catan rules...\"). If the provided
sources are about a different game than the question asks about, point that
out rather than answering anyway."

Citing the game makes the answer verifiable — the user can open that rulebook
and check — and the second sentence guards against the wrong-game failure mode
(retrieval surfaced Monopoly chunks for a Catan question; the model should
flag the mismatch instead of confidently answering from the wrong game).
```

---

### Fallback behavior

*What should the response say when the answer isn't found in the loaded rule books? Write the exact fallback message.*

```
Two distinct cases:

1. retrieve() returned [] (nothing in the store / empty collection) — this
   never reaches the model. The function returns, verbatim:
   "I couldn't find anything relevant in the loaded rule books. Try
   rephrasing your question — or check that your ingestion pipeline is
   working."

2. Chunks came back but none actually answer the question — this is handled
   by the model, instructed by the grounding prompt to say the loaded rule
   books don't cover it (rather than inventing an answer). I let the model
   phrase it because it can name *what* it does/doesn't see in the sources.
```

---

### Handling low-relevance chunks

*`retrieved_chunks` may include chunks with high distance scores (weak relevance). Will you filter these out before building context, pass them all in, or handle them another way? What are the tradeoffs?*

```
Pass all retrieved chunks into the context; let the grounding prompt handle
weak ones. I do not apply a distance threshold here.

Reasoning: with this chunker, distances are high across the board (correct
matches sit around 0.37–0.5), so a numeric cutoff would be brittle and risk
dropping the one chunk that holds the answer. Instead the prompt tells the
model to use only what genuinely answers the question and to say so when
nothing does — so an irrelevant chunk gets ignored rather than forced into
the answer.

Tradeoff: the model occasionally sees a loosely-related passage, which costs
a few tokens and a small distraction risk. That's cheaper and more robust
than a magic-number filter that silently discards good context.
```

---

### Message structure

*Describe how you will structure the messages list for the API call — what goes in the system message vs. the user message?*

```
Two messages:

  system: the standing rules of the job — who RulesBot is, the grounding
          instruction, and the citation instruction. These are behavioral
          constraints that don't change per request, so they belong in the
          system role where the model weights them most heavily.

  user:   the per-request payload — the formatted context block (the labeled
          source chunks) followed by the actual question, with a closing
          reminder to answer only from the text above and name the game.

Keeping the retrieved context in the user message (not the system prompt)
mirrors how the data actually flows: the rules of behavior are fixed; the
evidence is what varies each turn.
```

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Test query and response:**

```
Query: How do you get out of Jail in Monopoly?
Response: "According to the Monopoly rules, to get out of Jail, you can: pay
a $50 fine before rolling on any of your next three turns, use a Get Out of
Jail Free card, or roll doubles..."
Correctly grounded? Yes — every detail (the $50 fine, the card, rolling
doubles, the three-turn limit) is present in the retrieved Monopoly chunks.
Cited the right game? Yes — opens with "According to the Monopoly rules".

Out-of-corpus check — Query: "What is the best opening chess move?"
Response: "The loaded rule books don't cover it. The provided rule texts are
for Risk and Clue, but the question is about chess..." — refused instead of
guessing, and named the mismatched games. Grounding held.
```

**One thing you changed from your original spec after seeing the actual output:**

```
The grounding prompt worked on the first try, so the change was about
*confidence* rather than fixing a failure: I'd worried a distance filter
would be needed to stop weak chunks from derailing the answer, but the
chess test showed the model handled clearly-irrelevant context correctly on
its own (it called out that the sources were Risk/Clue, not chess). That
confirmed the decision to push relevance handling into the prompt instead of
a brittle numeric threshold in code.
```
