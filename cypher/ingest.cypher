// ============================================================
// TextLPG — Manual Ingestion Example (for learning)
// ============================================================
//
// THIS FILE IS FOR LEARNING ONLY — it shows how to manually create
// nodes and relationships in Cypher, one by one.
//
// In the real project, ingestion is done by textlpg/ingest.py which
// reads the data files and runs Cypher queries programmatically.
// But understanding how to write these by hand is essential!
//
// ============================================================
// CYPHER WRITE OPERATIONS — CHEAT SHEET
// ============================================================
//
// CREATE vs MERGE — the two ways to make things:
//
//   CREATE (n:Label {prop: "value"})
//   ^^^^^^
//   Always creates a NEW node, even if an identical one exists.
//   Fast, but will create duplicates if you run it twice!
//   SQL: INSERT INTO label (prop) VALUES ('value')
//
//   MERGE (n:Label {id: "unique_id"})
//   ^^^^^
//   "Find or create" — checks if a node with this id exists first.
//   If yes: reuse it. If no: create it. Safe to re-run!
//   SQL: INSERT INTO label (id) VALUES ('unique_id') ON CONFLICT DO NOTHING
//
//   WHEN TO USE WHICH?
//   - MERGE for nodes (so re-running doesn't create duplicates)
//   - CREATE for relationships in bulk (faster, use on clean database)
//   - MERGE for relationships when you might re-run
//
//
// ON CREATE SET vs SET:
//
//   MERGE (n:Book {id: "b.GEN"})
//   ON CREATE SET n.code = "GEN"     <-- only runs when MERGE creates a new node
//   ON MATCH SET n.code = "GEN"      <-- only runs when MERGE finds an existing node
//   SET n.code = "GEN"               <-- always runs (whether created or found)
//
//   Useful for: "set these properties only the first time, don't overwrite later"
//
//
// Creating relationships:
//
//   // Method 1: inline with node creation
//   CREATE (a:Book {id: "b.GEN"})-[:HAS_CHAPTER]->(ch:Chapter {id: "b.GEN.001"})
//
//   // Method 2: find existing nodes, then connect (more common)
//   MATCH (a:Book {id: "b.GEN"})
//   MATCH (ch:Chapter {id: "b.GEN.001"})
//   MERGE (a)-[:HAS_CHAPTER]->(ch)
//
//   Method 2 is better because the nodes might already exist.
//
// ============================================================


// ----------------------------------------------------------
// EXAMPLE 1: Create a Book node
// ----------------------------------------------------------
// Try running this in Neo4j Browser (Ctrl+Enter):

MERGE (b:Book {id: "b.GEN"})
ON CREATE SET b.code = "GEN",
              b.unit_name = "book";

// Now check it exists:
// MATCH (b:Book {id: "b.GEN"}) RETURN b;
//
// Run the MERGE again — nothing changes! That's the safety of MERGE.
// If you used CREATE instead, you'd get a second b.GEN node (bad!).


// ----------------------------------------------------------
// EXAMPLE 2: Create a Chapter and connect it to the Book
// ----------------------------------------------------------

MERGE (ch:Chapter {id: "b.GEN.001"})
ON CREATE SET ch.number = "001",
              ch.unit_name = "chapter";

// Now connect them — find both, then create the relationship:
MATCH (b:Book {id: "b.GEN"})
MATCH (ch:Chapter {id: "b.GEN.001"})
MERGE (b)-[:HAS_CHAPTER]->(ch);

// Verify the connection:
// MATCH (b:Book {id: "b.GEN"})-[:HAS_CHAPTER]->(ch:Chapter)
// RETURN b.code, ch.number;


// ----------------------------------------------------------
// EXAMPLE 3: Create a Verse and connect it to the Chapter
// ----------------------------------------------------------

MERGE (v:Verse {id: "b.GEN.001.001"})
ON CREATE SET v.number = "001",
              v.unit_name = "verse";

MATCH (ch:Chapter {id: "b.GEN.001"})
MATCH (v:Verse {id: "b.GEN.001.001"})
MERGE (ch)-[:HAS_VERSE]->(v);


// ----------------------------------------------------------
// EXAMPLE 4: Create a Text node and an APPEARS_IN relationship
// ----------------------------------------------------------
// This is the most important relationship in our model!
// APPEARS_IN carries properties: {start, end, content}

MERGE (t:Text {id: "48vd5.0"})
ON CREATE SET t.work_id = "b.GEN",
              t.version = "af";

// Now query it — this is what the whole project is about:
// MATCH (v:Verse {id: "b.GEN.001.001"})-[a:APPEARS_IN]->(t:Text)
// RETURN t.version AS language, a.content AS text;


// ----------------------------------------------------------
// EXAMPLE 5: Bulk insert with UNWIND
// ----------------------------------------------------------
// UNWIND is how you do batch inserts in Cypher.
// Instead of running one query per item, you pass a list.
//
// This is what ingest.py uses for all 33,921 verses.

// UNWIND [{id: "b.GEN.001.001", number: "001", parent: "b.GEN.001"},
//         {id: "b.GEN.001.002", number: "002", parent: "b.GEN.001"},
//         {id: "b.GEN.001.003", number: "003", parent: "b.GEN.001"}] AS v
// MERGE (verse:Verse {id: v.id})
// ON CREATE SET verse.number = v.number
// WITH verse, v
// MATCH (ch:Chapter {id: v.parent})
// MERGE (ch)-[:HAS_VERSE]->(verse);


// ----------------------------------------------------------
// NOTE: The real ingestion
// ----------------------------------------------------------
// All the examples above are for learning. In the real project,
// the Python script textlpg/ingest.py handles all of this
// automatically — it reads the data files and runs these same
// Cypher patterns programmatically for all 38,000+ nodes and
// 1.3 million relationships.
//
// To run the real ingestion:
//   python -m textlpg.ingest
// ----------------------------------------------------------
// Connect Verse to Text with content:
MATCH (v:Verse {id: "b.GEN.001.001"})
MATCH (t:Text {id: "48vd5.0"})
MERGE (v)-[:APPEARS_IN {
    start: 0,
    end: 66,
    content: "In die begin het God die hemel en die aarde geskape."
}]->(t);
