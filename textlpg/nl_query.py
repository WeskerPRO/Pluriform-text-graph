"""
TextLPG — Natural Language Query Module

Converts plain English questions into Cypher queries using a local LLM,
then executes them on Neo4j and returns the results.

Flow:
    1. User asks: "What does Genesis 1:1 say in German?"
    2. LLM generates Cypher:S
           MATCH (v:Verse {id: "b.GEN.001.001"})
                 -[:HAS_PASSAGE]->(p:Passage)
                 -[:IN_TEXT]->(t:Text {version: "de"})
           RETURN p.content
    3. We run that Cypher on Neo4j
    4. Return the results to the user

The key challenge: the LLM needs to know our graph schema to write
correct Cypher. We solve this by putting the schema in the prompt.

Usage:
    python -m textlpg.nl_query                          # interactive mode
    python -m textlpg.nl_query --question "How many books?"
"""

import time
import argparse
import requests

try:
    from textlpg.queries import run_raw_cypher
except ImportError:
    from queries import run_raw_cypher


# ── Ollama Configuration ─────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma2:9b"


# ── Schema Description ───────────────────────────────────
# This is what we feed to the LLM so it knows our graph structure.
# Without this, the LLM would guess node/relationship names and fail.
# Think of it like giving someone your SQL CREATE TABLE statements
# before asking them to write a SELECT query.
# SCHEMA_PROMPT is the rules for our LLM to follow.

SCHEMA_PROMPT = """You are a Cypher query generator for a Neo4j Bible database.

GRAPH SCHEMA:
- (:Corpus {id})
- (:Book {id, code})              — 66 books, code like "GEN", "PSA", "JHN", "REV"
- (:Chapter {id, number})         — number is zero-padded: "001", "002", ...
- (:Verse {id, number})           — number is zero-padded: "001", "002", ...
- (:Text {id, version, work_id})  — version is a language code: "en", "de", "fr", "ar", ...
- (:Passage {id, content})        — holds the actual verse text
- (:Annotation {id, type, content, author}) — LLM-generated annotations

RELATIONSHIPS:
- (:Corpus)-[:HAS_BOOK]->(:Book)
- (:Corpus)-[:HAS_TEXT]->(:Text)
- (:Book)-[:HAS_CHAPTER]->(:Chapter)
- (:Chapter)-[:HAS_VERSE]->(:Verse)
- (:Verse)-[:HAS_PASSAGE]->(:Passage)
- (:Passage)-[:IN_TEXT]->(:Text)
- (:Text)-[:VERSION_OF]->(:Book)
- (:Annotation)-[:ANNOTATES]->(:Verse)

ID FORMATS:
- Book: "b.GEN", "b.PSA", "b.JHN"
- Chapter: "b.GEN.001", "b.PSA.023"
- Verse: "b.GEN.001.001", "b.JHN.003.016"

BOOK CODES (all 66 — use these EXACTLY):
OLD TESTAMENT:
GEN=Genesis, EXO=Exodus, LEV=Leviticus, NUM=Numbers, DEU=Deuteronomy,
JOS=Joshua, JDG=Judges, RUT=Ruth, 1SA=1Samuel, 2SA=2Samuel,
1KI=1Kings, 2KI=2Kings, 1CH=1Chronicles, 2CH=2Chronicles,
EZR=Ezra, NEH=Nehemiah, EST=Esther, JOB=Job, PSA=Psalms,
PRO=Proverbs, ECC=Ecclesiastes, SON=SongOfSolomon, ISA=Isaiah,
JER=Jeremiah, LAM=Lamentations, EZE=Ezekiel, DAN=Daniel,
HOS=Hosea, JOE=Joel, AMO=Amos, OBA=Obadiah, JON=Jonah,
MIC=Micah, NAH=Nahum, HAB=Habakkuk, ZEP=Zephaniah, HAG=Haggai,
ZEC=Zechariah, MAL=Malachi
NEW TESTAMENT:
MAT=Matthew, MAR=Mark, LUK=Luke, JOH=John, ACT=Acts,
ROM=Romans, 1CO=1Corinthians, 2CO=2Corinthians, GAL=Galatians,
EPH=Ephesians, PHI=Philippians, COL=Colossians, 1TH=1Thessalonians,
2TH=2Thessalonians, 1TI=1Timothy, 2TI=2Timothy, TIT=Titus,
PHM=Philemon, HEB=Hebrews, JAM=James, 1PE=1Peter, 2PE=2Peter,
1JO=1John, 2JO=2John, 3JO=3John, JUD=Jude, REV=Revelation

KEY PATTERN — to get verse content:
    MATCH (v:Verse {id: "b.GEN.001.001"})
          -[:HAS_PASSAGE]->(p:Passage)
          -[:IN_TEXT]->(t:Text {version: "en"})
    RETURN p.content

CRITICAL RULES:
1. Output ONLY the Cypher query, nothing else — no explanation, no markdown.
2. Always use the Passage pattern for verse content (never put content on relationships).
3. Use parameters $param style when possible, but hardcoded values are also fine.
4. For text search, use: WHERE p.content CONTAINS "word"
5. Always add LIMIT when the result could be large.
6. Chapter and verse numbers are zero-padded strings: "001" not 1.
7. IMPORTANT: John = JOH (NOT JHN), Mark = MAR (NOT MRK), Philippians = PHI (NOT PHP). Always use the EXACT book codes listed above.
"""


def call_ollama(prompt, model=MODEL):
    """Send a prompt to Ollama and return the response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=180)
    response.raise_for_status()
    return response.json()["response"].strip()


def extract_cypher(llm_response):
    """
    Extract the Cypher query from the LLM response.

    Sometimes the LLM wraps the query in ```cypher ... ``` blocks
    or adds extra text. This cleans it up.
    """
    text = llm_response.strip() # Remove leading/trailing whitespace for example " " --> ""

    # Remove markdown code blocks if present
    if "```" in text:
        # Find content between ``` markers
        parts = text.split("```")
        for part in parts:
            # Skip empty parts and the "cypher" language tag
            cleaned = part.strip()
            if cleaned.lower().startswith("cypher"):
                cleaned = cleaned[6:].strip()
            if cleaned and any(kw in cleaned.upper() for kw in ["MATCH", "RETURN", "CREATE", "MERGE"]): 
                return cleaned

    # If no code blocks, return as-is (hopefully just the query)
    return text


def nl_query(question):
    """
    Convert a natural language question to Cypher, execute it, return results.

    This is the main function — it does everything:
        1. Builds a prompt with our schema + the user's question
        2. Sends it to the LLM
        3. Extracts the Cypher query from the response
        4. Runs the query on Neo4j
        5. Returns the results

    Args:
        question: e.g., "What does John 3:16 say in English?"

    Returns:
        dict with keys: question, cypher, results, time
    """
    full_prompt = SCHEMA_PROMPT + f"\nQUESTION: {question}\nCYPHER:" # Building the prompt
    print(f"  [LLM] Generating Cypher...") # Asking the LLM to generate Cypher
    start = time.time() # get the time before Ollama response
    raw_response = call_ollama(full_prompt)
    stop = time.time() # get the time after Ollama response
    llm_time = stop - start # get the time spent for the LLM
    print(f"  [LLM] Response in {llm_time:.1f}s")
    cypher = extract_cypher(raw_response) # Cleaning up the Cypher
    print(f"  [Cypher] {cypher}")

    # Step 4: Run on Neo4j
    try:
        start = time.time()
        results = run_raw_cypher(cypher) # run the query on Neo4j provided by the LLM 
        stop = time.time()
        db_time = stop - start
        print(f"  [Neo4j] {len(results)} results in {db_time:.3f}s")
    except Exception as e:
        print(f"  [Neo4j] Query failed: {e}")
        return {
            "question": question,
            "cypher": cypher,
            "error": str(e),
            "results": [],
            "llm_time": llm_time,
        }

    return {
        "question": question,
        "cypher": cypher,
        "results": results,
        "llm_time": llm_time,
        "db_time": db_time,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="TextLPG — Natural Language Query")
    parser.add_argument("--question", "-q", type=str, help="Ask a question")
    args = parser.parse_args()

    print("\n")
    print("=" * 50)
    print("TextLPG — Natural Language Query")
    print(f"Model: {MODEL}")
    print("=" * 50)

    if args.question:
        # Single question mode
        print(f"\nQ: {args.question}")
        result = nl_query(args.question)
        print(f"\nResults:")
        for row in result["results"][:20]:
            print(f"  {row}")
    else:
        # Interactive mode
        print("\nAsk questions about the Bible database in plain English.")
        print("Type 'quit' to exit.\n")

        while True:
            try:
                question = input("Q: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not question or question.lower() in ("quit", "exit", "q"):
                break

            result = nl_query(question)
            print(f"\nResults:")
            if result["results"]:
                for row in result["results"][:20]:
                    print(f"  {row}")
            else:
                print("  (no results)")
            print()

    print("\nDone!")
