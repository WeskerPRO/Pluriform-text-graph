import json
import os
import time

try:
    from textlpg.config import get_session
except ImportError:
    from config import get_session

# ── Paths ──────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
META_PATH = os.path.join(DATA_DIR, "meta.json")
NODES_PATH = os.path.join(DATA_DIR, "layers", "work", "biblical_structure", "nodes.jsonl")
TEXTS_DIR = os.path.join(DATA_DIR, "texts")


def load_meta():
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_nodes():
    books, chapters, verses = [], [], []
    with open(NODES_PATH, encoding="utf-8") as f:
        for line in f:
            node = json.loads(line)
            if node["unit_name"] == "book":
                books.append(node)
            elif node["unit_name"] == "chapter":
                chapters.append(node)
            elif node["unit_name"] == "verse":
                verses.append(node)
    return books, chapters, verses


def load_text_content(text_id):
    path = os.path.join(TEXTS_DIR, text_id)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Step 1: Create Corpus ──────────────────────────────────
def ingest_corpus(meta):
    query = """
    MERGE (c:Corpus {id: $id})
    ON CREATE SET c.schema_version = $schema_version
    """
    with get_session() as session:
        session.run(query, id=meta["id"], schema_version=meta["schema_version"])
    print(f"[1/7] Corpus node created: {meta['id']}")


# ── Step 2: Create Text nodes ─────────────────────────────
def ingest_texts(meta):
    """
    Each Text represents one book in one language:
        (:Text {id: "48vd5.0", version: "af", work_id: "b.GEN"})
    """
    query = """
    UNWIND $texts AS t
    MERGE (text:Text {id: t.id})
    ON CREATE SET text.work_id = t.work_id,
                  text.version = t.version
    WITH text
    MATCH (c:Corpus {id: $corpus_id})
    MERGE (c)-[:HAS_TEXT]->(text)
    """
    with get_session() as session:
        session.run(query, texts=meta["texts"], corpus_id=meta["id"])
    print(f"[2/7] Text nodes created: {len(meta['texts'])}")


# ── Step 3: Create Book nodes ─────────────────────────────
def ingest_books(meta, books):
    query = """
    UNWIND $books AS b
    MERGE (book:Book {id: b.id})
    ON CREATE SET book.code = b.code,
                  book.unit_name = b.unit_name
    WITH book
    MATCH (c:Corpus {id: $corpus_id})
    MERGE (c)-[:HAS_BOOK]->(book)
    """
    book_params = [
        {"id": b["id"], "code": b["properties"]["code"], "unit_name": b["unit_name"]}
        for b in books
    ]
    with get_session() as session:
        session.run(query, books=book_params, corpus_id=meta["id"])
    print(f"[3/7] Book nodes created: {len(books)}")


# ── Step 4: Link Texts to Books via VERSION_OF ────────────
def ingest_version_of():
    """
    The query matches Text.work_id to Book.id:
        Text {work_id: "b.GEN"} -[:VERSION_OF]-> Book {id: "b.GEN"}
    """

    query = """
    MATCH (t:Text)
    MATCH (b:Book {id: t.work_id})
    MERGE (t)-[:VERSION_OF]->(b)
    """
    with get_session() as session:
        session.run(query)
    print(f"[4/7] VERSION_OF relationships created (Text -> Book)")


# ── Step 5: Create Chapter nodes ──────────────────────────
def ingest_chapters(chapters):
    query = """
    UNWIND $chapters AS ch
    MERGE (chapter:Chapter {id: ch.id})
    ON CREATE SET chapter.number = ch.number,
                  chapter.unit_name = ch.unit_name
    WITH chapter, ch
    MATCH (book:Book {id: ch.parent_id})
    MERGE (book)-[:HAS_CHAPTER]->(chapter)
    """
    chapter_params = [
        {
            "id": c["id"],
            "number": c["properties"]["number"],
            "unit_name": c["unit_name"],
            "parent_id": c["parent_id"],
        }
        for c in chapters
    ]
    with get_session() as session:
        session.run(query, chapters=chapter_params)
    print(f"[5/7] Chapter nodes created: {len(chapters)}")


# ── Step 6: Create Verse nodes ────────────────────────────
def ingest_verses(verses):
    query = """
    UNWIND $verses AS v
    MERGE (verse:Verse {id: v.id})
    ON CREATE SET verse.number = v.number,
                  verse.unit_name = v.unit_name
    WITH verse, v
    MATCH (chapter:Chapter {id: v.parent_id})
    MERGE (chapter)-[:HAS_VERSE]->(verse)
    """
    BATCH_SIZE = 5000
    with get_session() as session:
        for i in range(0, len(verses), BATCH_SIZE):
            batch = verses[i : i + BATCH_SIZE]
            verse_params = [
                {
                    "id": v["id"],
                    "number": v["properties"]["number"],
                    "unit_name": v["unit_name"],
                    "parent_id": v["parent_id"],
                }
                for v in batch
            ]
            session.run(query, verses=verse_params)
    print(f"[6/7] Verse nodes created: {len(verses)}")


# ── Step 7: Create Passage nodes ──────────────────────────
def ingest_passages(verses):
    """
    The biggest step: create ~1.3M Passage nodes with verse content.

    Instead of storing content on a relationship (APPEARS_IN),
    we create a :Passage NODE for each verse-in-a-language.

    Each Passage:
        - Has a unique id: "{verse_id}:{text_id}" (e.g., "b.GEN.001.001:48vd5.0")
        - Stores the content, start, and end positions
        - Connects to its Verse via [:HAS_PASSAGE]
        - Connects to its Text via [:IN_TEXT]

    So the path is:
        (:Verse)-[:HAS_PASSAGE]->(:Passage {content})-[:IN_TEXT]->(:Text)

    Strategy: process one text file at a time (load file once, extract all verses).

    text_verses = { 
        "48vd5.0": [(verse_id, start, end), ...], 
        "48vd5.1": [(verse_id, start, end), ...], 
        ...

        for example: 
        "48vd5.0": [
            ("b.GEN.001.001", 0, 4),
            ("b.GEN.001.002", 4, 7),
            ("b.GEN.001.003", 7, 11),
            ("b.GEN.001.004", 11, 16),
        ]

        Or 

        "48vd5.1": [
            ("b.GEN.001.001", 0, 4),
            ("b.GEN.001.002", 4, 7),
            ("b.GEN.001.003", 7, 11),
            ("b.GEN.001.004", 11, 16),
        ]
    }
    """
    print("[7/7] Building Passage nodes (~1.3M)...")

    # Build lookup: text_id -> list of (verse_id, start, end)
    text_verses = {}
    for v in verses:
        for text_id, span in v["spans"].items():
            if text_id not in text_verses:
                text_verses[text_id] = []
            text_verses[text_id].append((v["id"], span["start"], span["end"]))

    # Cypher: create Passage node, link to Verse and Text
    query = """
    UNWIND $passages AS p
    MERGE (passage:Passage {id: p.id, content: p.content, start: p.start, end: p.end})
    WITH passage, p 
    MATCH (v:Verse {id: p.verse_id})
    MATCH (t:Text {id: p.text_id})
    MERGE (v)-[:HAS_PASSAGE]->(passage)
    MERGE (passage)-[:IN_TEXT]->(t)
    """

    total_passages = 0
    total_texts = len(text_verses)
    start_time = time.time()
    BATCH_SIZE = 2000

    with get_session() as session:
        for idx, (text_id, verse_list) in enumerate(text_verses.items(), 1):
            # Load the full text file once
            content = load_text_content(text_id)

            # Build passage params
            passages = [] # free memory before inserting
            for verse_id, start, end in verse_list:
                verse_content = content[start:end].strip()
                passages.append({
                    "id": f"{verse_id}:{text_id}",  # unique ID for this passage
                    "verse_id": verse_id,
                    "text_id": text_id,
                    "start": start,
                    "end": end,
                    "content": verse_content,
                })
            
            # Insert in batches
            for i in range(0, len(passages), BATCH_SIZE):
                batch = passages[i : i + BATCH_SIZE]
                session.run(query, passages=batch)

            total_passages += len(passages)

            # Progress every 100 texts
            if idx % 100 == 0 or idx == total_texts:
                elapsed = time.time() - start_time
                rate = total_passages / elapsed if elapsed > 0 else 0
                print(f"       {idx}/{total_texts} texts | {total_passages:,} passages | {rate:.0f}/sec")

    elapsed = time.time() - start_time
    print(f"       Done: {total_passages:,} passages in {elapsed:.1f}s")


# ── Main ──────────────────────────────────────────────────
def run_ingestion():
    """Run the full ingestion pipeline."""
    print("=" * 50)
    print("TextLPG — Data Ingestion (v2)")
    print("=" * 50)
    total_start = time.time()

    # Load data from files
    print("\nLoading data files...")
    meta = load_meta()
    books, chapters, verses = load_nodes()
    print(f"  meta.json: {len(meta['texts'])} texts")
    print(f"  nodes.jsonl: {len(books)} books, {len(chapters)} chapters, {len(verses)} verses\n")

    # Run each step in order
    ingest_corpus(meta)
    ingest_texts(meta)
    ingest_books(meta, books)
    ingest_version_of()
    ingest_chapters(chapters)
    ingest_verses(verses)
    ingest_passages(verses)

    total_elapsed = time.time() - total_start
    print(f"\nIngestion complete in {total_elapsed:.1f}s")
    print("=" * 50)


if __name__ == "__main__":
    run_ingestion()
