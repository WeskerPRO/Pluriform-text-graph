"""
TextLPG — LLM Enrichment Module

Uses a local LLM (Ollama) to generate annotations for Bible verses,
then stores them in the graph as :Annotation nodes.

Flow:
    1. Fetch verse content from Neo4j
    2. Send to LLM with a prompt (summarize, extract themes, etc.)
    3. Store the response as an Annotation node linked to the Verse

The Annotation schema (from queries.py):
    (:Annotation {id, type, content, author})-[:ANNOTATES]->(:Verse)

Usage:
    python -m textlpg.enrich                     # enrich a few demo verses
    python -m textlpg.enrich --verse b.GEN.001.001 --type summary
"""

# import json
import time
import argparse
import requests 

try:
    from textlpg.queries import get_verse_text, add_annotation, get_annotations
except ImportError:
    from queries import get_verse_text, add_annotation, get_annotations


# ── Ollama Configuration ─────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma2:9b"


# ── Prompt Templates ─────────────────────────────────────
# Each annotation type has a prompt that tells the LLM what to produce.
# The {verse_text} placeholder gets replaced with actual content.

PROMPTS = {
    "summary": (
        "You are a Bible scholar. Summarize the following Bible verse "
        "in one clear sentence. Only output the summary, nothing else.\n\n"
        "Verse: {verse_text}"
    ),
    "themes": (
        "You are a Bible scholar. List the main themes of this Bible verse "
        "as a comma-separated list. Only output the themes, nothing else.\n\n"
        "Verse: {verse_text}"
    ),
    "keywords": (
        "Extract 3-5 important keywords from this Bible verse. "
        "Output them as a comma-separated list, nothing else.\n\n"
        "Verse: {verse_text}"
    ),
    "sentiment": (
        "Classify the sentiment/tone of this Bible verse using one word "
        "(e.g., hopeful, commanding, sorrowful, joyful, warning). "
        "Only output the one word, nothing else.\n\n"
        "Verse: {verse_text}"
    ),
}


def call_ollama(prompt, model=MODEL):
    """
    Send a prompt to Ollama and return the response text.

    This is a simple HTTP POST — Ollama runs a REST API on port 11434.
    We set stream=False so we get the full response in one JSON object.

    Equivalent curl:
        curl http://localhost:11434/api/generate -d '{
            "model": "gemma2:9b",
            "prompt": "...",
            "stream": false
        }'
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["response"].strip()


def enrich_verse(verse_id, annotation_type="summary", language="en"):
    """
    Generate an LLM annotation for a single verse and store it in Neo4j.

    Steps:
        1. Fetch the verse content from the graph
        2. Build a prompt using the template for this annotation type
        3. Send to Ollama
        4. Store the response as an Annotation node

    Args:
        verse_id: e.g., "b.GEN.001.001"
        annotation_type: one of "summary", "themes", "keywords", "sentiment"
        language: which language version to use as input (default: "en")

    Returns:
        dict with the annotation details, or None if verse not found
    """
    # Step 1: Get the verse text
    results = get_verse_text(verse_id, language=language)
    if not results:
        print(f"  [!] No content found for {verse_id} in '{language}'")
        return None

    verse_text = results[0]["content"]

    # Step 2: Build the prompt
    if annotation_type not in PROMPTS:
        print(f"  [!] Unknown annotation type: {annotation_type}")
        print(f"      Available: {list(PROMPTS.keys())}")
        return None

    prompt = PROMPTS[annotation_type].format(verse_text=verse_text)

    # Step 3: Call the LLM
    print(f"  [{annotation_type}] Asking LLM about {verse_id}...")
    start = time.time()
    llm_response = call_ollama(prompt)
    elapsed = time.time() - start
    print(f"  [{annotation_type}] Got response in {elapsed:.1f}s")

    # Step 4: Store in Neo4j
    annotation_id = f"{verse_id}:{annotation_type}"
    add_annotation(
        annotation_id=annotation_id,
        annotation_type=annotation_type,
        content=llm_response,
        author=f"ollama/{MODEL}",
        target_verse_id=verse_id,
    )
    print(f"  [{annotation_type}] Saved annotation: {annotation_id}")

    return {
        "annotation_id": annotation_id,
        "verse_id": verse_id,
        "type": annotation_type,
        "content": llm_response,
        "author": f"ollama/{MODEL}",
    }


def enrich_batch(verse_ids, annotation_types=None, language="en"):
    """
    Enrich multiple verses with multiple annotation types.

    Args:
        verse_ids: list of verse IDs
        annotation_types: list of types (default: all types)
        language: language version to use

    Returns:
        list of annotation dicts
    """
    if annotation_types is None:
        annotation_types = list(PROMPTS.keys())

    results = []
    total = len(verse_ids) * len(annotation_types)
    count = 0

    for verse_id in verse_ids:
        for ann_type in annotation_types:
            count += 1
            print(f"\n[{count}/{total}] {verse_id} — {ann_type}")
            result = enrich_verse(verse_id, ann_type, language)
            if result:
                results.append(result)

    return results


# ── Main — demo enrichment ───────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="TextLPG — LLM Enrichment")
    parser.add_argument("--verse", type=str, help="Verse ID (e.g., b.GEN.001.001)")
    parser.add_argument("--type", type=str, choices=list(PROMPTS.keys()),
                        help="Annotation type")
    parser.add_argument("--language", type=str, default="en", help="Language (default: en)")
    args = parser.parse_args()

    print("=" * 50)
    print("TextLPG — LLM Enrichment")
    print(f"Model: {MODEL}")
    print("=" * 50)

    if args.verse:
        # Single verse mode
        types = [args.type] if args.type else list(PROMPTS.keys())
        enrich_batch([args.verse], types, args.language)
    else:
        # Demo mode — enrich a few famous verses
        demo_verses = [
            "b.GEN.001.001",   # In the beginning...
            "b.PSA.023.001",   # The Lord is my shepherd...
            "b.JHN.003.016",   # For God so loved the world...
        ]
        # Just summaries for the demo (faster)
        enrich_batch(demo_verses, ["summary", "themes"], args.language)

    # Show what we created
    print("\n" + "=" * 50)
    print("Annotations in the graph:")
    print("=" * 50)
    check_verses = [args.verse] if args.verse else [
        "b.GEN.001.001", "b.PSA.023.001", "b.JHN.003.016"
    ]
    for vid in check_verses:
        annotations = get_annotations(vid)
        if annotations:
            print(f"\n{vid}:")
            for a in annotations:
                print(f"  [{a['type']}] {a['content'][:100]}")
