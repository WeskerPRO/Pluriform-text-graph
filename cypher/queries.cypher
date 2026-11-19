// ============================================================
// TextLPG — Cypher Query Library (v2)
// ============================================================
//
// WHAT CHANGED FROM v1?
//   Content is now on :Passage nodes, not on relationships.
//
//   v1: MATCH (v:Verse)-[a:APPEARS_IN]->(t:Text)       RETURN a.content
//   v2: MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text)  RETURN p.content
//
// Also new: (:Text)-[:VERSION_OF]->(:Book) — explicit link
//
// HOW TO USE: Copy ONE query at a time into Neo4j Browser (http://localhost:7474)
// ============================================================


// ===========================================================
// SECTION 1: BASIC READS
// ===========================================================

// Q1: Get all books
MATCH (b:Book)
RETURN b.id, b.code
ORDER BY b.code;

// Q2: Count everything in the database
MATCH (n)
RETURN labels(n)[0] AS label, COUNT(n) AS count
ORDER BY count DESC;

// Q3: Count all relationships by type
MATCH ()-[r]->()
RETURN type(r) AS relationship, COUNT(r) AS count
ORDER BY count DESC;

// Q4: Get all available languages
MATCH (t:Text)
RETURN DISTINCT t.version AS language
ORDER BY language;


// ===========================================================
// SECTION 2: NAVIGATION — Book > Chapter > Verse
// ===========================================================

// Q5: Get all chapters in Genesis
MATCH (b:Book {code: "GEN"})-[:HAS_CHAPTER]->(ch:Chapter)
RETURN ch.id, ch.number
ORDER BY ch.number;

// Q6: Get all verses in Genesis chapter 1
MATCH (ch:Chapter {id: "b.GEN.001"})-[:HAS_VERSE]->(v:Verse)
RETURN v.id, v.number
ORDER BY v.number;

// Q7: Chain: Book -> Chapter -> Verse (first 10 verses of Genesis ch.1)
MATCH (b:Book {code: "GEN"})-[:HAS_CHAPTER]->(ch:Chapter)-[:HAS_VERSE]->(v:Verse)
WHERE ch.number = "001"
RETURN b.code AS book, ch.number AS chapter, v.number AS verse
ORDER BY v.number
LIMIT 10;


// ===========================================================
// SECTION 3: VERSE CONTENT — the core query (v2 pattern)
// ===========================================================
//
// The path: Verse -> Passage (content) -> Text (language)
//
// Old: (Verse)-[a:APPEARS_IN {content}]->(Text)
// New: (Verse)-[:HAS_PASSAGE]->(Passage {content})-[:IN_TEXT]->(Text)
//
// WHY? Content belongs on nodes, not relationships.
// ===========================================================

// Q8: Get Genesis 1:1 in ALL languages
// This is the KEY query — the one the supervisor asked about.
MATCH (v:Verse {id: "b.GEN.001.001"})
      -[:HAS_PASSAGE]->(p:Passage)
      -[:IN_TEXT]->(t:Text)
RETURN t.version AS language, p.content AS text
ORDER BY t.version;

// Q9: Get a verse in ONE specific language
MATCH (v:Verse {id: "b.GEN.001.001"})
      -[:HAS_PASSAGE]->(p:Passage)
      -[:IN_TEXT]->(t:Text {version: "en"})
RETURN p.content AS text;

// Q10: Compare a verse across selected languages
MATCH (v:Verse {id: "b.PSA.023.001"})
      -[:HAS_PASSAGE]->(p:Passage)
      -[:IN_TEXT]->(t:Text)
WHERE t.version IN ["en", "de", "fr", "es", "ar"]
RETURN t.version AS language, p.content AS text
ORDER BY t.version;


// ===========================================================
// SECTION 4: FULL PATH — Book to content
// ===========================================================

// Q11: Full English text of Genesis chapter 1
MATCH (b:Book {code: "GEN"})
      -[:HAS_CHAPTER]->(ch:Chapter {number: "001"})
      -[:HAS_VERSE]->(v:Verse)
      -[:HAS_PASSAGE]->(p:Passage)
      -[:IN_TEXT]->(t:Text {version: "en"})
RETURN v.number AS verse, p.content AS text
ORDER BY v.number;

// Q12: How many verses per book?
MATCH (b:Book)-[:HAS_CHAPTER]->(ch:Chapter)-[:HAS_VERSE]->(v:Verse)
RETURN b.code AS book, COUNT(v) AS verse_count
ORDER BY verse_count DESC;

// Q13: How many languages per book? (using VERSION_OF — new in v2)
MATCH (t:Text)-[:VERSION_OF]->(b:Book)
RETURN b.code AS book, COUNT(t) AS language_count
ORDER BY book;


// ===========================================================
// SECTION 5: SEARCH
// ===========================================================

// Q14: Find English verses containing "love"
MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: "en"})
WHERE p.content CONTAINS "love"
RETURN v.id AS verse, p.content AS text
LIMIT 20;

// Q15: Case-insensitive search
MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: "en"})
WHERE toLower(p.content) CONTAINS toLower("Love")
RETURN v.id AS verse, p.content AS text
LIMIT 10;

// Q16: Find verses starting with "And God"
MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: "en"})
WHERE p.content STARTS WITH "And God"
RETURN v.id AS verse, p.content AS text
LIMIT 10;


// ===========================================================
// SECTION 6: AGGREGATION (WITH, COLLECT, COUNT)
// ===========================================================

// Q17: Books with more than 30 chapters
MATCH (b:Book)-[:HAS_CHAPTER]->(ch:Chapter)
WITH b, COUNT(ch) AS chapter_count
WHERE chapter_count > 30
RETURN b.code AS book, chapter_count
ORDER BY chapter_count DESC;

// Q18: 5 longest verses in English
MATCH (v:Verse)-[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: "en"})
WITH v, p, size(p.content) AS length
ORDER BY length DESC
LIMIT 5
RETURN v.id AS verse, length, p.content AS text;

// Q19: First verse of every book in English
MATCH (b:Book)-[:HAS_CHAPTER]->(ch:Chapter)-[:HAS_VERSE]->(v:Verse)
      -[:HAS_PASSAGE]->(p:Passage)-[:IN_TEXT]->(t:Text {version: "en"})
WHERE ch.number = "001" AND v.number = "001"
RETURN b.code AS book, p.content AS opening_verse
ORDER BY b.code;

// Q20: All languages available for Genesis 1:1
MATCH (v:Verse {id: "b.GEN.001.001"})-[:HAS_PASSAGE]->(:Passage)-[:IN_TEXT]->(t:Text)
RETURN v.id, COLLECT(t.version) AS languages, COUNT(t) AS language_count;

// Q21: John 3:16 in all languages
MATCH (v:Verse {id: "b.JHN.003.016"})
      -[:HAS_PASSAGE]->(p:Passage)
      -[:IN_TEXT]->(t:Text)
RETURN t.version AS lang, p.content AS text
ORDER BY t.version;


// ===========================================================
// SECTION 7: VERSION_OF — new in v2
// ===========================================================
// (:Text)-[:VERSION_OF]->(:Book) links text files to their book.

// Q22: Which language versions exist for Genesis?
MATCH (t:Text)-[:VERSION_OF]->(b:Book {code: "GEN"})
RETURN t.id AS text_file, t.version AS language
ORDER BY t.version;

// Q23: Find all texts for a specific language
MATCH (t:Text {version: "de"})-[:VERSION_OF]->(b:Book)
RETURN b.code AS book, t.id AS text_file
ORDER BY b.code;
