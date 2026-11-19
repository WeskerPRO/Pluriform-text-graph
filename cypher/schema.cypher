// ============================================================
// TextLPG — Graph Schema: Constraints & Indexes (v2)
// ============================================================
//
// WHAT CHANGED FROM v1?
//   - Added :Passage node (holds verse content — was on APPEARS_IN before)
//   - Added [:VERSION_OF] relationship (Text -> Book, explicit link)
//   - Removed APPEARS_IN (replaced by HAS_PASSAGE + IN_TEXT)
//
// WHY?
//   Supervisor feedback: "Do NOT store content in relationships."
//   Content belongs on NODES, not relationships.
//   Relationships should describe HOW things connect, not carry heavy data.
//
// ============================================================
//
// THE NEW GRAPH MODEL (v2):
//
//   (:Corpus)
//       |
//       |--[:HAS_BOOK]--> (:Book {id, code})  <--[:VERSION_OF]-- (:Text {id, version})
//       |                    |                                        ^
//       |              [:HAS_CHAPTER]                                 |
//       |                    |                                   [:IN_TEXT]
//       |                    v                                        |
//       |              (:Chapter {id, number})                   (:Passage {content, start, end})
//       |                    |                                        ^
//       |              [:HAS_VERSE]                                   |
//       |                    |                                  [:HAS_PASSAGE]
//       |                    v                                        |
//       |              (:Verse {id, number})  -------------------------+
//       |
//       |--[:HAS_TEXT]--> (:Text)
//
//   Node counts:
//     :Corpus   — 1
//     :Book     — 66
//     :Chapter  — 1,249
//     :Verse    — 33,921
//     :Text     — 3,047
//     :Passage  — ~1,326,545 (one per verse per language — holds the content!)
//
//   KEY QUERY — "Get Genesis 2:1 in Afrikaans":
//     MATCH (v:Verse {id: "b.GEN.002.001"})
//           -[:HAS_PASSAGE]->(p:Passage)
//           -[:IN_TEXT]->(t:Text {version: "af"})
//     RETURN p.content
//
//     No Corpus traversal needed! Direct path: Verse -> Passage -> Text.
//
// ============================================================


// ----------------------------------------------------------
// 1. UNIQUENESS CONSTRAINTS
// ----------------------------------------------------------
// Each node type has a unique identifier.
// CREATE CONSTRAINT also creates an index automatically.
//
// SQL equivalent: ALTER TABLE books ADD UNIQUE (id);

CREATE CONSTRAINT corpus_id_unique IF NOT EXISTS
FOR (c:Corpus)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT book_id_unique IF NOT EXISTS
FOR (b:Book)
REQUIRE b.id IS UNIQUE;

CREATE CONSTRAINT chapter_id_unique IF NOT EXISTS
FOR (ch:Chapter)
REQUIRE ch.id IS UNIQUE;

CREATE CONSTRAINT verse_id_unique IF NOT EXISTS
FOR (v:Verse)
REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT text_id_unique IF NOT EXISTS
FOR (t:Text)
REQUIRE t.id IS UNIQUE;

// Passage id = verse_id + ":" + text_id (e.g., "b.GEN.001.001:48vd5.0")
// This guarantees one passage per verse-language combination
CREATE CONSTRAINT passage_id_unique IF NOT EXISTS
FOR (p:Passage)
REQUIRE p.id IS UNIQUE;


// ----------------------------------------------------------
// 2. ADDITIONAL INDEXES
// ----------------------------------------------------------
// Speed up common lookups. No uniqueness enforced.

CREATE INDEX book_code IF NOT EXISTS
FOR (b:Book)
ON (b.code);

CREATE INDEX text_version IF NOT EXISTS
FOR (t:Text)
ON (t.version);

CREATE INDEX chapter_number IF NOT EXISTS
FOR (ch:Chapter)
ON (ch.number);

CREATE INDEX verse_number IF NOT EXISTS
FOR (v:Verse)
ON (v.number);
