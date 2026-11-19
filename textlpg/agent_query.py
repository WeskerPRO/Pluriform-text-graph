"""
TextLPG — Agentic Query Module (Self-Healing Queries)

=== WHAT IS AN "AGENT" IN AI? ===

An agent is a program that can:
    1. OBSERVE   — look at the result of its action
    2. REFLECT   — decide if the result is good or bad
    3. ACT       — take a corrective action if needed
    4. LOOP      — repeat until success or give up

A regular program: input -> process -> output (one shot, no feedback)
An agent:          input -> process -> check -> fix -> check -> fix -> output (done or give up)

=== WHAT IS "SELF-HEALING"? ===

Our nl_query.py sends a question to the LLM, gets Cypher, runs it.
If the Cypher has a syntax error... it just fails. The user sees an error.

A self-healing agent does this instead:

    1. User asks: "How many books?"
    2. LLM generates: MATCH (b:Book) RETRUN count(b)    <-- typo!
    3. Neo4j returns: SyntaxError: "RETRUN" is not valid
    4. Agent catches the error and tells the LLM:
       "Your query failed with this error: ... Please fix it."
    5. LLM generates: MATCH (b:Book) RETURN count(b)    <-- fixed!
    6. Neo4j returns: [{count(b): 66}]                  <-- success!

This is called a "feedback loop" — the agent learns from its mistakes
within a single conversation. It's NOT training — the model doesn't
permanently learn. It just gets more context to work with.

=== HOW THIS RELATES TO RAG ===

RAG = Retrieval-Augmented Generation
    - Before answering, retrieve relevant context from a knowledge base
    - Feed that context to the LLM so it gives better answers

Our agent does something similar:
    - The "retrieved context" is the ERROR MESSAGE from Neo4j
    - We feed it back to the LLM as extra context
    - The LLM uses that context to generate a better query

This pattern is sometimes called "Agentic RAG" because the agent
decides WHAT to retrieve (the error) and WHEN to retrieve it (on failure).

Usage:
    python -m textlpg.agent_query                             # interactive mode
    python -m textlpg.agent_query --question "How many books?" # single question
"""

import time
import argparse
# import requests -- not needed for now

try:
    from textlpg.queries import run_raw_cypher
    from textlpg.nl_query import SCHEMA_PROMPT, MODEL, extract_cypher, call_ollama # OLLAMA_URL
except ImportError:
    from queries import run_raw_cypher
    from nl_query import SCHEMA_PROMPT, MODEL, extract_cypher, call_ollama # OLLAMA_URL


# ── Agent Configuration ─────────────────────────────────
MAX_RETRIES = 3     # How many times the agent will try to fix a failed query
                     # Why 3? Diminishing returns — if 3 attempts fail,
                     # the question is probably too hard for the model.


# ── The Repair Prompt ───────────────────────────────────
# This is what we send to the LLM when a query fails.
# Notice: we give it the ORIGINAL question, the FAILED query, and the ERROR.
# This is the "reflection" step — giving the agent memory of what went wrong.

REPAIR_PROMPT = """You are a Cypher query repair agent.

The previous Cypher query FAILED. Fix it based on the error message.

ORIGINAL QUESTION: {question}

FAILED QUERY:
{failed_query}

ERROR MESSAGE:
{error}

{schema}

RULES:
1. Output ONLY the corrected Cypher query — no explanation, no markdown.
2. Fix the specific error mentioned above.
3. Keep the query logic the same — only fix what's broken.
4. If the error is about a missing variable, make sure all variables are defined in MATCH.
5. If the error is about syntax, check for typos in keywords (MATCH, RETURN, WHERE, etc.).
6. Chapter and verse numbers are zero-padded strings: "001" not 1.
7. John = JOH (NOT JHN), Mark = MAR (NOT MRK), Philippians = PHI (NOT PHP).
"""


# ── Validation Prompt ───────────────────────────────────
# After a query returns results, the agent can optionally check
# if the results actually answer the question (semantic validation).

VALIDATE_PROMPT = """You are a result validator. Given a question and query results,
determine if the results correctly answer the question.

QUESTION: {question}
RESULTS: {results}

Reply with ONLY "YES" or "NO".
"""


def agent_query(question, max_retries=MAX_RETRIES, verbose=True):
    """
    The main agent function — self-healing query pipeline.

    This is the "agent loop":

        ┌─────────────────────────────────────────────┐
        │  1. Generate Cypher from question            │
        │  2. Execute on Neo4j                         │
        │  3. Success? ──> Return results              │
        │     Failure? ──> Feed error back to LLM      │
        │                  Go to step 1 (with context) │
        │  4. After max_retries, give up               │
        └─────────────────────────────────────────────┘

    Args:
        question: Natural language question (e.g., "How many books?")
        max_retries: Max number of repair attempts (default: 3)
        verbose: Print progress to console

    Returns:
        dict with keys:
            - question: the original question
            - cypher: the final Cypher query (last attempt)
            - results: list of result dicts (empty if all attempts failed)
            - attempts: list of all attempts with details
            - total_time: total time for all attempts
            - success: True if we got results
    """
    total_start = time.time()

    # This list records every attempt — like a "memory" of what the agent tried.
    # Each attempt is a dict with: cypher, error (if any), results (if any), time.
    # This is useful for debugging and for the research notebook.
    attempts = []

    # ── ATTEMPT 1: Initial query generation (same as nl_query.py) ──
    if verbose:
        print(f"\n  [Agent] Attempt 1/{max_retries + 1}: Generating initial Cypher...")

    full_prompt = SCHEMA_PROMPT + f"\nQUESTION: {question}\nCYPHER:"

    start = time.time()
    raw_response = call_ollama(full_prompt)
    llm_time = time.time() - start

    cypher = extract_cypher(raw_response)

    if verbose:
        print(f"  [Agent] LLM responded in {llm_time:.1f}s")
        print(f"  [Agent] Cypher: {cypher[:80]}...")

    # Try to execute it
    attempt_result = _try_execute(cypher, verbose)
    attempts.append({
        "attempt": 1,
        "cypher": cypher,
        "llm_time": llm_time,
        **attempt_result,
    })

    # ── SUCCESS on first try ──
    if attempt_result["success"]:
        if verbose:
            print(f"  [Agent] Success on first attempt! {len(attempt_result['results'])} results")
        return _build_result(question, cypher, attempts, total_start)

    # ── REPAIR LOOP: Try to fix the query ──
    # This is the "agentic" part — the agent reflects on the error
    # and tries to fix it, up to max_retries times.
    for retry in range(max_retries):
        attempt_num = retry + 2  # attempt 2, 3, 4...

        if verbose:
            print(f"\n  [Agent] Attempt {attempt_num}/{max_retries + 1}: Repairing query...")
            print(f"  [Agent] Error was: {attempt_result['error'][:100]}...")

        # Build the repair prompt — this is the KEY part.
        # We give the LLM:
        #   1. The original question (so it remembers what to do)
        #   2. The failed query (so it can see what went wrong)
        #   3. The error message (so it knows HOW it failed)
        #   4. The full schema (so it has the reference)
        repair = REPAIR_PROMPT.format(
            question=question,
            failed_query=cypher,
            error=attempt_result["error"],
            schema=SCHEMA_PROMPT,
        )

        start = time.time()
        raw_response = call_ollama(repair)
        llm_time = time.time() - start

        cypher = extract_cypher(raw_response)

        if verbose:
            print(f"  [Agent] LLM responded in {llm_time:.1f}s") # LLM response time
            print(f"  [Agent] Fixed Cypher: {cypher[:80]}...") # only print the first 80 chars

        # Try the fixed query
        attempt_result = _try_execute(cypher, verbose)
        attempts.append({
            "attempt": attempt_num,
            "cypher": cypher,
            "llm_time": llm_time,
            **attempt_result,
        })

        if attempt_result["success"]:
            if verbose:
                print(f"  [Agent] Self-healed on attempt {attempt_num}! {len(attempt_result['results'])} results")
            return _build_result(question, cypher, attempts, total_start)

    # ── ALL ATTEMPTS FAILED ──
    if verbose:
        print(f"\n  [Agent] All {max_retries + 1} attempts failed. Giving up.")

    return _build_result(question, cypher, attempts, total_start)


def _try_execute(cypher, verbose=True):
    """
    Try to execute a Cypher query on Neo4j.

    Returns a dict with:
        - success: True/False
        - results: list of result dicts (empty on failure)
        - error: error message string (empty on success)
        - db_time: execution time in seconds

    This is a helper — it separates "running the query" from
    "deciding what to do about the result" (the agent's job).
    """
    try:
        start = time.time()
        results = run_raw_cypher(cypher)
        db_time = time.time() - start

        if verbose:
            print(f"  [Neo4j] {len(results)} results in {db_time:.3f}s")

        # Query ran but returned nothing — might be wrong but not an error
        if not results:
            return {
                "success": False,
                "results": [],
                "error": "Query returned 0 results — possibly wrong query logic",
                "db_time": db_time,
            }

        return {
            "success": True,
            "results": results,
            "error": "",
            "db_time": db_time,
        }

    except Exception as e:
        if verbose:
            print(f"  [Neo4j] Query failed: {e}")
        return {
            "success": False,
            "results": [],
            "error": str(e),
            "db_time": 0,
        }


def _build_result(question, final_cypher, attempts, total_start):
    """
    Build the final result dict from all attempts.

    This is what the caller (UI, notebook, CLI) receives.
    The 'attempts' list gives full transparency into what the agent tried.
    """
    last_attempt = attempts[-1]
    return {
        "question": question,
        "cypher": final_cypher,
        "results": last_attempt["results"],
        "success": last_attempt["success"],
        "attempts": attempts,
        "total_attempts": len(attempts),
        "total_time": time.time() - total_start,
        "llm_time": sum(a["llm_time"] for a in attempts),
    }


# ── Main — interactive mode ──────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="TextLPG — Agentic Query (Self-Healing)")
    parser.add_argument("--question", "-q", type=str, help="Ask a question")
    parser.add_argument("--retries", "-r", type=int, default=MAX_RETRIES, help="Max repair attempts")
    args = parser.parse_args()

    print("\n")
    print("=" * 55)
    print("TextLPG — Agentic Query (Self-Healing)")
    print(f"Model: {MODEL} | Max retries: {args.retries}")
    print("=" * 55)

    if args.question:
        # Single question mode
        print(f"\nQ: {args.question}")
        result = agent_query(args.question, max_retries=args.retries)

        print(f"\n{'=' * 55}")
        print(f"Final: {'SUCCESS' if result['success'] else 'FAILED'} "
              f"in {result['total_attempts']} attempt(s), {result['total_time']:.1f}s total")

        if result["results"]:
            print(f"\nResults:")
            for row in result["results"][:20]:
                print(f"  {row}")
    else:
        # Interactive mode
        print("\nAsk questions in plain English. The agent will self-heal on errors.")
        print("Type 'quit' to exit.\n")

        while True:
            try:
                question = input("Q: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not question or question.lower() in ("quit", "exit", "q"):
                break

            result = agent_query(question, max_retries=args.retries)

            print(f"\n{'─' * 55}")
            print(f"{'SUCCESS' if result['success'] else 'FAILED'} | "
                  f"{result['total_attempts']} attempt(s) | "
                  f"{result['total_time']:.1f}s total")

            if result["results"]:
                print(f"\nResults:")
                for row in result["results"][:20]:
                    print(f"  {row}")
            else:
                print("  (no results)")
            print()

    print("\nDone!")
