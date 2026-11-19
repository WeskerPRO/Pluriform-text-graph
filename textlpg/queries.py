try:
    from textlpg.config import get_session
except ImportError:
    from config import get_session


# ══════════════════════════════════════════════════════════════
# SECTION 1: READ QUERIES — browsing the graph
# ══════════════════════════════════════════════════════════════


def get_all_books():
    """
    Get all 66 books with their codes.

    Returns: [{"id": "b.GEN", "code": "GEN"}, ...]
    """
    query = """
    MATCH (b:Book)
    RETURN b.id AS id, b.code AS code
    ORDER BY b.code
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query)]


def get_chapters(book_code):
    """
    Get all chapters for a given book.

    Args:
        book_code: e.g., "GEN", "PSA", "JHN"

    Returns: [{"id": "b.GEN.001", "number": "001"}, ...]
    """
    query = """
    MATCH (b:Book {code: $book_code})-[:HAS_CHAPTER]->(ch:Chapter)
    RETURN ch.id AS id, ch.number AS number
    ORDER BY ch.number
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, book_code=book_code)]


def get_verses(chapter_id):
    """
    Get all verses in a chapter.

    Args:
        chapter_id: e.g., "b.GEN.001"

    Returns: [{"id": "b.GEN.001.001", "number": "001"}, ...]
    """
    query = """
    MATCH (ch:Chapter {id: $chapter_id})-[:HAS_VERSE]->(v:Verse)
    RETURN v.id AS id, v.number AS number
    ORDER BY v.number
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, chapter_id=chapter_id)]


def get_languages():
    """
    Get all available language codes.

    Returns: ["af", "am", "ar", "bg", ...]
    """
    query = """
    MATCH (t:Text)
    RETURN DISTINCT t.version AS language
    ORDER BY language
    """
    with get_session() as session:
        return [r["language"] for r in session.run(query)]


# ══════════════════════════════════════════════════════════════
# SECTION 2: VERSE CONTENT — the core queries (v2 pattern)
# ══════════════════════════════════════════════════════════════
#
# v1 pattern: (Verse)-[a:APPEARS_IN]->(Text)     → a.content
# v2 pattern: (Verse)-[:HAS_PASSAGE]->(Passage)-[:IN_TEXT]->(Text)  → p.content
#
# The Passage node holds: {id, content, start, end}
# ══════════════════════════════════════════════════════════════


def get_verse_text(verse_id, language=None):
    """
    Get the text content of a verse, optionally filtered by language.

    This is the KEY query of the whole project.
    Path: Verse -> Passage (content lives here) -> Text (language info)

    Args:
        verse_id: e.g., "b.GEN.001.001"
        language: optional, e.g., "en", "de". None = all languages.

    Returns: [{"language": "en", "content": "In the beginning..."}, ...]
    """
    if language:
        query = """
        MATCH (v:Verse {id: $verse_id})
              -[:HAS_PASSAGE]->(p:Passage)
              -[:IN_TEXT]->(t:Text {version: $language})
        RETURN t.version AS language, p.content AS content
        """
        params = {"verse_id": verse_id, "language": language}
    else:
        query = """
        MATCH (v:Verse {id: $verse_id})
              -[:HAS_PASSAGE]->(p:Passage)
              -[:IN_TEXT]->(t:Text)
        RETURN t.version AS language, p.content AS content
        ORDER BY t.version
        """
        params = {"verse_id": verse_id}

    with get_session() as session:
        return [dict(r) for r in session.run(query, **params)]


def get_chapter_text(book_code, chapter_number, language):
    """
    Get all verses in a chapter for a specific language.

    Path: Book -> Chapter -> Verse -> Passage -> Text

    Args:
        book_code: e.g., "GEN"
        chapter_number: e.g., "001"
        language: e.g., "en"

    Returns: [{"verse": "001", "content": "In the beginning..."}, ...]
    """
    query = """
    MATCH (b:Book {code: $book_code})
          -[:HAS_CHAPTER]->(ch:Chapter {number: $chapter_number})
          -[:HAS_VERSE]->(v:Verse)
          -[:HAS_PASSAGE]->(p:Passage)
          -[:IN_TEXT]->(t:Text {version: $language})
    RETURN v.number AS verse, p.content AS content
    ORDER BY v.number
    """
    with get_session() as session:
        return [dict(r) for r in session.run(
            query,
            book_code=book_code,
            chapter_number=chapter_number,
            language=language,
        )]


def compare_verse(verse_id, languages):
    """
    Compare a verse across multiple languages side by side.

    Args:
        verse_id: e.g., "b.GEN.001.001"
        languages: list, e.g., ["en", "de", "fr", "ar"]

    Returns: [{"language": "en", "content": "In the beginning..."}, ...]
    """
    query = """
    MATCH (v:Verse {id: $verse_id})
          -[:HAS_PASSAGE]->(p:Passage)
          -[:IN_TEXT]->(t:Text)
    WHERE t.version IN $languages
    RETURN t.version AS language, p.content AS content
    ORDER BY t.version
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, verse_id=verse_id, languages=languages)]


# ══════════════════════════════════════════════════════════════
# SECTION 3: SEARCH QUERIES
# ══════════════════════════════════════════════════════════════


def search_verses(keyword, language="en", limit=20):
    """
    Search for verses containing a keyword (case-sensitive).

    Now searches on Passage.content (node property) instead of
    relationship property — this is what the supervisor wanted.

    Args:
        keyword: e.g., "love", "light"
        language: which language to search (default: "en")
        limit: max results

    Returns: [{"verse_id": "b.GEN.001.001", "content": "..."}, ...]
    """
    query = """
    MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: $language})
    WHERE p.content CONTAINS $keyword
    RETURN v.id AS verse_id, p.content AS content
    LIMIT $limit
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, keyword=keyword, language=language, limit=limit)]


def search_verses_case_insensitive(keyword, language="en", limit=20):
    """
    Search for verses containing a keyword (case-insensitive).

    Uses toLower() on both sides for case-insensitive matching.
    Slower but more user-friendly.
    """
    query = """
    MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: $language})
    WHERE toLower(p.content) CONTAINS toLower($keyword)
    RETURN v.id AS verse_id, p.content AS content
    LIMIT $limit
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, keyword=keyword, language=language, limit=limit)]


# ══════════════════════════════════════════════════════════════
# SECTION 4: STATISTICS & AGGREGATION
# ══════════════════════════════════════════════════════════════


def get_database_stats():
    """
    Get an overview of everything in the database.

    Returns: {"nodes": {"Verse": 33921, ...}, "relationships": {"HAS_PASSAGE": ..., ...}}
    """
    with get_session() as session:
        nodes = {}
        for r in session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, COUNT(n) AS count
            ORDER BY count DESC
        """):
            nodes[r["label"]] = r["count"]

        rels = {}
        for r in session.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, COUNT(r) AS count
            ORDER BY count DESC
        """):
            rels[r["rel_type"]] = r["count"]

        return {"nodes": nodes, "relationships": rels}


def get_book_stats(book_code):
    """
    Get statistics for a specific book.

            MATCH (b:Book {code: $book_code})-[:HAS_CHAPTER]->(ch:Chapter)
            WITH b, COUNT(ch) AS chapters
            MATCH (b)-[:HAS_CHAPTER]->(:Chapter)-[:HAS_VERSE]->(v:Verse)
            WITH b, chapters, COUNT(v) AS verses
            MATCH (t:Text)-[:VERSION_OF]->(b)
            RETURN chapters, verses, COUNT(t) AS languages

    Returns: {"chapters": 50, "verses": 1536, "languages": 38}
    """
    with get_session() as session:
        result = session.run("""
            MATCH (b:Book {code: $book_code})-[:HAS_CHAPTER]->(ch:Chapter)-[:HAS_VERSE]->(v:Verse)
            WITH b, COUNT(DISTINCT ch) AS chapters, COUNT(v) AS verses
            MATCH (t:Text)-[:VERSION_OF]->(b)
            RETURN chapters, verses, COUNT(t) AS languages
        """, book_code=book_code)
        record = result.single()
        if record:
            return dict(record)
        return None


# ══════════════════════════════════════════════════════════════
# SECTION 5: WRITE QUERIES — annotations
# ══════════════════════════════════════════════════════════════


def add_annotation(annotation_id, annotation_type, content, author, target_verse_id):
    """
    Add an annotation to a verse.

    Creates :Annotation node and connects to Verse via [:ANNOTATES].
    Used by enrich.py for LLM-generated annotations.

    Args:
        annotation_id: unique ID, e.g., "anno_001"
        annotation_type: e.g., "summary", "theme", "translation_note"
        content: the annotation text
        author: e.g., "Claude", "GPT-4"
        target_verse_id: e.g., "b.GEN.001.001"
    """
    query = """
    MERGE (a:Annotation {id: $id})
    ON CREATE SET a.type = $type,
                  a.content = $content,
                  a.author = $author
    ON MATCH SET a.content = $content
    WITH a
    MATCH (v:Verse {id: $verse_id})
    MERGE (a)-[:ANNOTATES]->(v)
    """
    with get_session() as session:
        session.run(
            query,
            id=annotation_id,
            type=annotation_type,
            content=content,
            author=author,
            verse_id=target_verse_id,
        )


def get_annotations(verse_id):
    """
    Get all annotations for a verse.

    Returns: [{"id": "anno_001", "type": "summary", "content": "...", "author": "Claude"}, ...]
    """
    query = """
    MATCH (a:Annotation)-[:ANNOTATES]->(v:Verse {id: $verse_id})
    RETURN a.id AS id, a.type AS type, a.content AS content, a.author AS author
    ORDER BY a.type, a.id
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, verse_id=verse_id)]


def delete_annotation(annotation_id):
    """Delete a specific annotation and its relationships."""
    query = """
    MATCH (a:Annotation {id: $id})
    DETACH DELETE a
    """
    with get_session() as session:
        session.run(query, id=annotation_id)


def run_raw_cypher(query, **params):
    """
    Run any Cypher query directly — used by nl_query.py for LLM-generated queries.

    Args:
        query: any Cypher query string
        **params: query parameters

    Returns: list of dicts (one per result row)
    """
    with get_session() as session:
        return [dict(r) for r in session.run(query, **params)]


# ══════════════════════════════════════════════════════════════
# MAIN — test the queries
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 50)
    print("TextLPG — Query Module Test (v2)")
    print("=" * 50)

    # Test 1: Database overview
    print("\n--- Database Stats ---")
    stats = get_database_stats()
    for label, count in stats["nodes"].items():
        print(f"  :{label:12} {count:>10,}")
    for rel, count in stats["relationships"].items():
        print(f"  -[:{rel}]->  {count:>10,}")

    # Test 2: List books
    books = get_all_books()
    print(f"\n--- Books ({len(books)}) ---")
    print(f"  First 5: {[b['code'] for b in books[:5]]}")

    # Test 3: Verse in all languages (first 5)
    print("\n--- Genesis 1:1 (first 5 languages) ---")
    for r in get_verse_text("b.GEN.001.001")[:5]:
        print(f"  [{r['language']}] {r['content'][:60]}")

    # Test 4: Verse in specific language
    print("\n--- Genesis 1:1 in English ---")
    for r in get_verse_text("b.GEN.001.001", language="en"):
        print(f"  {r['content']}")

    # Test 5: Compare across languages
    print("\n--- Psalm 23:1 compared ---")
    for r in compare_verse("b.PSA.023.001", ["en", "de", "fr", "la"]):
        print(f"  [{r['language']}] {r['content']}")

    # Test 6: Search
    print("\n--- Search 'light' in English ---")
    for r in search_verses("light", language="en", limit=5):
        print(f"  {r['verse_id']}: {r['content'][:70]}...")

    # Test 7: Book stats
    print("\n--- Genesis stats ---")
    print(f"  {get_book_stats('GEN')}")

    print("\n" + "=" * 50)
    print("All tests passed!")
