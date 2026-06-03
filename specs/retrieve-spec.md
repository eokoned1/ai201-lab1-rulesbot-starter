# Spec: `retrieve()`

**File:** `retriever.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user's natural language query, find the most relevant chunks from the vector store using semantic similarity search. Return them ranked by relevance so that `generate_response()` can use them as context.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's natural language question |
| `n_results` | `int` | Maximum number of chunks to return (default: `N_RESULTS` from `config.py`) |

**Output:** `list[dict]`

Each dict in the returned list must contain exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text |
| `"game"` | `str` | The game name this chunk came from |
| `"distance"` | `float` | Cosine distance score — lower means more similar to the query |

Results should be ordered from most to least relevant (lowest to highest distance). Returns an empty list `[]` if the collection contains no documents.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Query approach

*Describe how you will use `_collection.query()` to find relevant chunks. What arguments will you pass, and why?*

```
Call _collection.query() with:
  - query_texts=[query] — a list with the single user question. ChromaDB
    embeds it with the same all-MiniLM-L6-v2 model used at ingestion, so the
    query vector lives in the same space as the stored chunk vectors.
  - n_results=n_results — defaults to N_RESULTS (3) from config.py. Caps how
    many chunks come back.
  - include=["documents", "metadatas", "distances"] — I need all three: the
    chunk text to answer with, the metadata to know which game it's from, and
    the distance so I (and generate_response) can judge relevance.
ChromaDB returns matches already sorted closest-first, so I don't re-sort.
```

---

### Return structure

*Sketch out what one item in your return list looks like as a concrete example. Where does each field come from in the query results?*

```
One item looks like:

  {
    "text":     "x, that hex produces no resources that turn, regardless...",
    "game":     "Catan",
    "distance": 0.466,
  }

Where each field comes from, after indexing into [0] (see next field):
  - "text"     <- results["documents"][0][i]
  - "game"     <- results["metadatas"][0][i]["game"]   (the dict stored at
                  ingestion time by embed_and_store)
  - "distance" <- results["distances"][0][i]

I zip the three parallel lists together and build one dict per match.
```

---

### Handling the nested result structure

*`_collection.query()` returns nested lists. Describe what index you need to access to get the actual list of results for a single query, and why the nesting exists.*

```
query() is built to accept *many* queries at once, so every field it returns
is a list-of-lists: one inner list per query string in query_texts. I pass
exactly one query, so all my results live at index [0]:

  results["documents"][0]  -> list of chunk texts for my query
  results["metadatas"][0]  -> list of metadata dicts
  results["distances"][0]  -> list of distance floats

Forgetting the [0] is the classic bug here: results["documents"] is
[[chunk, chunk, chunk]], so iterating it gives you the inner list as a single
item instead of the chunks themselves.
```

---

### Relevance threshold

*Will you filter out results above a certain distance score, or return all `n_results` regardless of how relevant they are? What are the tradeoffs of each approach?*

```
retrieve() returns all n_results regardless of distance — no threshold here.
I keep the distance on each chunk so the *next* stage (generate_response /
the prompt) can decide what to do with weak matches.

Why not filter in retrieve(): with this character-based chunker, distances
run higher than the idealized 0.1–0.2 (real "roll a 7" top hit was 0.466).
A hard cutoff like 0.5 would have dropped genuinely correct chunks. Filtering
too aggressively risks returning [] for a question that *is* answerable,
which is a worse failure than passing a slightly-loose chunk to a model that's
instructed to ignore irrelevant context.

Tradeoff: returning everything means the model sometimes sees a marginally
related chunk. That's acceptable because grounding is enforced downstream in
the system prompt, and keeping retrieve() simple/predictable is worth more
than a brittle magic-number threshold.
```

---

### Edge cases

*How does your implementation behave when: (a) the collection is empty, (b) the query matches no chunks well, (c) the query matches chunks from multiple games?*

```
(a) Empty collection: the guard `if _collection.count() == 0: return []`
    short-circuits before querying, so generate_response gets [] and shows
    its fallback message instead of crashing.

(b) Nothing matches well: query() still returns its n_results closest chunks,
    just with high distances. retrieve() passes them through unfiltered; the
    high distance is the signal, and the grounding prompt downstream lets the
    model say "the rules don't cover that."

(c) Multiple games (e.g. "how do you win?"): each game has its own winning-
    condition chunk, so the top 3 came back from Monopoly, Risk, and Ticket
    to Ride — all near 0.51. That's correct semantic-search behavior, not a
    bug: the question genuinely matches all of them about equally.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**Test query and top result returned:**

```
Query: What happens when you run out of disease cubes in Pandemic?
Top result game: Pandemic
Distance score: 0.373
Does it make sense? Yes — all three returned chunks were Pandemic, and the
top one is exactly the loss-condition rule ("...any color of disease cubes
runs out..."). Specific, game-named queries retrieve cleanly.

(Cross-game check) Query: How do you win?
Top results: Monopoly (0.507), Risk (0.509), Ticket to Ride (0.522) — three
different games' victory rules, scores nearly tied. Correct behavior for a
question that applies to every game.
```

**One thing about the query results that surprised you:**

```
The distance scores were higher than the lab's example numbers (the "roll a
7" top hit was 0.466, not ~0.14). At first that looked like a bug, but it's a
direct consequence of the character-based chunker: chunks start mid-sentence,
so even a correct match isn't a tight embedding match. The *ranking* is still
right — Catan is the top result for the roll-7 query — which is what actually
matters. Absolute distance is relative to your chunking, not a universal scale.
```
