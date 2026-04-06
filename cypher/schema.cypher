// ============================================================
// TextLPG — Graph Schema: Constraints & Indexes
// ============================================================
// This file defines the structure of our Labeled Property Graph.
// Run these ONCE when setting up a fresh database.
//
// KEY CYPHER CONCEPTS USED HERE:
//   CREATE CONSTRAINT  — enforces uniqueness, also creates an index
//   CREATE INDEX       — speeds up lookups on frequently queried properties
//   Node labels        — like "types" for nodes: (:Text), (:Witness), etc.
//   Properties         — key-value pairs on nodes: {id: "text_001", title: "..."}
//
// OUR GRAPH MODEL (based on sample_data.json):
//
//   (:Text)  —[:HAS_WITNESS]→  (:Witness)
//                                   |
//                             [:HAS_PAGE]
//                                   ↓
//                                (:Page)
//                                   |
//                             [:HAS_LINE]
//                                   ↓
//                                (:Line)
//
//   (:Text)  —[:HAS_CHAPTER]→  (:Chapter)
//                                   |
//                            [:HAS_PARAGRAPH]
//                                   ↓
//                              (:Paragraph)
//                                   |
//                            [:HAS_SENTENCE]
//                                   ↓
//                              (:Sentence)
//
//   (:Sentence) —[:ALIGNS_WITH]→ (:Line)    ← links logical structure to physical witnesses
//   (:Annotation) —[:ANNOTATES]→ (:Sentence) or (:Line)
//
// Two parallel hierarchies:
//   PHYSICAL:  Text → Witness → Page → Line        (what the manuscripts look like)
//   LOGICAL:   Text → Chapter → Paragraph → Sentence (the abstract text structure)
//   The ALIGNS_WITH relationship bridges them.
// ============================================================


// ----------------------------------------------------------
// 1. UNIQUENESS CONSTRAINTS
// ----------------------------------------------------------
// Syntax:  CREATE CONSTRAINT <name> IF NOT EXISTS
//          FOR (variable:Label)
//          REQUIRE variable.property IS UNIQUE
//
// This ensures no two nodes of the same label share the same id.
// It also automatically creates an index on that property.
// "IF NOT EXISTS" makes it safe to re-run this file.

CREATE CONSTRAINT text_id_unique IF NOT EXISTS
FOR (t:Text)
REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT witness_id_unique IF NOT EXISTS
FOR (w:Witness)
REQUIRE w.id IS UNIQUE;

CREATE CONSTRAINT page_id_unique IF NOT EXISTS
FOR (p:Page)
REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT line_id_unique IF NOT EXISTS
FOR (l:Line)
REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT chapter_id_unique IF NOT EXISTS
FOR (c:Chapter)
REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT paragraph_id_unique IF NOT EXISTS
FOR (p:Paragraph)
REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT sentence_id_unique IF NOT EXISTS
FOR (s:Sentence)
REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT annotation_id_unique IF NOT EXISTS
FOR (a:Annotation)
REQUIRE a.id IS UNIQUE;


// ----------------------------------------------------------
// 2. ADDITIONAL INDEXES (for common queries)
// ----------------------------------------------------------
// Syntax:  CREATE INDEX <name> IF NOT EXISTS
//          FOR (variable:Label)
//          ON (variable.property)
//
// Unlike constraints, indexes don't enforce uniqueness —
// they just make lookups faster.

// Find witnesses by their siglum (short label like "A", "B")
CREATE INDEX witness_siglum IF NOT EXISTS
FOR (w:Witness)
ON (w.siglum);

// Find lines by their text content
CREATE INDEX line_content IF NOT EXISTS
FOR (l:Line)
ON (l.content);

// Find annotations by type ("note", "variant", etc.)
CREATE INDEX annotation_type IF NOT EXISTS
FOR (a:Annotation)
ON (a.type);

// Find annotations by author
CREATE INDEX annotation_author IF NOT EXISTS
FOR (a:Annotation)
ON (a.author);
