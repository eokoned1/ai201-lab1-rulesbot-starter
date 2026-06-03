from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def generate_response(query, retrieved_chunks):
    """
    Generate a grounded answer from retrieved rule chunks.

    TODO — Milestone 3:

    `retrieved_chunks` is the list returned by retrieve(). Each item is a dict:
      - "text"     : the chunk text
      - "game"     : the game name
      - "distance" : similarity score (you can use this to filter weak matches)

    Before writing code, talk through these with your group:
      - How will you format the chunks into a context block for the prompt?
      - What instructions will stop the model from answering beyond what the
        rules say? (Grounding is the whole point — a confident wrong answer
        is worse than an honest "I don't know.")
      - How will you surface which game each answer comes from?

    Your response should:
      1. Answer using only the retrieved context — not the model's general knowledge
      2. Make clear which game the answer comes from
      3. Say so clearly when the answer isn't in the loaded rules

    Return the response as a plain string.
    """
    if not retrieved_chunks:
        return (
            "I couldn't find anything relevant in the loaded rule books. "
            "Try rephrasing your question — or check that your ingestion pipeline is working."
        )

    # Build a context block: each chunk is labeled with the game it came from
    # and numbered, so the model can tell sources apart and cite the right one.
    context_block = "\n\n".join(
        f"[Source {i + 1} — {chunk['game']}]\n{chunk['text']}"
        for i, chunk in enumerate(retrieved_chunks)
    )

    system_prompt = (
        "You are RulesBot, an assistant that answers board game rules questions. "
        "Answer using ONLY the rule text provided in the context below. "
        "Do not draw on any outside knowledge or anything you know about board "
        "games from training — even if you are confident the answer is something "
        "else. If the answer is not contained in the provided rule text, say so "
        "explicitly: reply that the loaded rule books don't cover it and do not "
        "guess or fill in the gap.\n\n"
        "Always state which game your answer comes from (cite the game named in "
        "the source label, e.g. \"According to the Catan rules...\"). If the "
        "provided sources are about a different game than the question asks "
        "about, point that out rather than answering anyway."
    )

    user_prompt = (
        f"Rule text (the only information you may use):\n\n{context_block}\n\n"
        f"---\n\nQuestion: {query}\n\n"
        "Answer using only the rule text above, and name the game it comes from."
    )

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content
