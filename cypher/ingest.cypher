// ============================================================
// TextLPG — Data Ingestion: Sample Data
// ============================================================
// This file shows how to create nodes and relationships
// for the sample_data.json dataset.
//
// KEY CYPHER CONCEPTS USED HERE:
//   MERGE   — "find or create": if the node exists, reuse it; otherwise create it.
//              Safer than CREATE because re-running won't create duplicates.
//   CREATE  — always creates a new node/relationship (duplicates if run twice).
//   SET     — updates properties on an existing node.
//   -[:REL]-> — creates a directed relationship between two nodes.
//   ON CREATE SET / ON MATCH SET — run only when MERGE creates vs finds.
//
// We use MERGE for nodes (idempotent) and CREATE for relationships
// after ensuring the nodes exist.
// ============================================================


// ----------------------------------------------------------
// 1. TEXT NODE (the root of everything)
// ----------------------------------------------------------
// MERGE finds or creates a node with label :Text and id "text_001".
// ON CREATE SET sets properties only if the node was just created.

MERGE (t:Text {id: "text_001"})
ON CREATE SET
  t.title       = "De Exemplo Textuum",
  t.language    = "latin",
  t.description = "A sample scholarly text with two witnesses";


// ----------------------------------------------------------
// 2. PHYSICAL HIERARCHY: Witness → Page → Line
// ----------------------------------------------------------
// Pattern: MERGE the child node, then MERGE the relationship.
// Using MERGE on relationships too, so this is fully idempotent.

// --- Witness A ---
MERGE (wA:Witness {id: "witness_A"})
ON CREATE SET
  wA.siglum   = "A",
  wA.source   = "Manuscript Alpha",
  wA.language = "latin";

// Connect Text → Witness A
MATCH (t:Text {id: "text_001"})
MATCH (wA:Witness {id: "witness_A"})
MERGE (t)-[:HAS_WITNESS]->(wA);

// Witness A, Page 1
MERGE (pA1:Page {id: "page_A1"})
ON CREATE SET pA1.number = 1;

MATCH (wA:Witness {id: "witness_A"})
MATCH (pA1:Page {id: "page_A1"})
MERGE (wA)-[:HAS_PAGE]->(pA1);

// Witness A, Page 1, Lines
MERGE (lA1_1:Line {id: "line_A1_1"})
ON CREATE SET lA1_1.number = 1, lA1_1.content = "In principio erat verbum";

MERGE (lA1_2:Line {id: "line_A1_2"})
ON CREATE SET lA1_2.number = 2, lA1_2.content = "et verbum erat apud deum";

MERGE (lA1_3:Line {id: "line_A1_3"})
ON CREATE SET lA1_3.number = 3, lA1_3.content = "et deus erat verbum";

MATCH (pA1:Page {id: "page_A1"})
MATCH (l1:Line {id: "line_A1_1"})
MATCH (l2:Line {id: "line_A1_2"})
MATCH (l3:Line {id: "line_A1_3"})
MERGE (pA1)-[:HAS_LINE]->(l1)
MERGE (pA1)-[:HAS_LINE]->(l2)
MERGE (pA1)-[:HAS_LINE]->(l3);

// Witness A, Page 2
MERGE (pA2:Page {id: "page_A2"})
ON CREATE SET pA2.number = 2;

MATCH (wA:Witness {id: "witness_A"})
MATCH (pA2:Page {id: "page_A2"})
MERGE (wA)-[:HAS_PAGE]->(pA2);

MERGE (lA2_1:Line {id: "line_A2_1"})
ON CREATE SET lA2_1.number = 1, lA2_1.content = "hoc erat in principio";

MERGE (lA2_2:Line {id: "line_A2_2"})
ON CREATE SET lA2_2.number = 2, lA2_2.content = "apud deum omnia per ipsum";

MATCH (pA2:Page {id: "page_A2"})
MATCH (l1:Line {id: "line_A2_1"})
MATCH (l2:Line {id: "line_A2_2"})
MERGE (pA2)-[:HAS_LINE]->(l1)
MERGE (pA2)-[:HAS_LINE]->(l2);


// --- Witness B ---
MERGE (wB:Witness {id: "witness_B"})
ON CREATE SET
  wB.siglum   = "B",
  wB.source   = "Manuscript Beta",
  wB.language = "latin";

MATCH (t:Text {id: "text_001"})
MATCH (wB:Witness {id: "witness_B"})
MERGE (t)-[:HAS_WITNESS]->(wB);

// Witness B, Page 1
MERGE (pB1:Page {id: "page_B1"})
ON CREATE SET pB1.number = 1;

MATCH (wB:Witness {id: "witness_B"})
MATCH (pB1:Page {id: "page_B1"})
MERGE (wB)-[:HAS_PAGE]->(pB1);

MERGE (lB1_1:Line {id: "line_B1_1"})
ON CREATE SET lB1_1.number = 1, lB1_1.content = "In principio verbum erat";

MERGE (lB1_2:Line {id: "line_B1_2"})
ON CREATE SET lB1_2.number = 2, lB1_2.content = "verbum erat apud deum";

MERGE (lB1_3:Line {id: "line_B1_3"})
ON CREATE SET lB1_3.number = 3, lB1_3.content = "et deus verbum erat";

MATCH (pB1:Page {id: "page_B1"})
MATCH (l1:Line {id: "line_B1_1"})
MATCH (l2:Line {id: "line_B1_2"})
MATCH (l3:Line {id: "line_B1_3"})
MERGE (pB1)-[:HAS_LINE]->(l1)
MERGE (pB1)-[:HAS_LINE]->(l2)
MERGE (pB1)-[:HAS_LINE]->(l3);

// Witness B, Page 2
MERGE (pB2:Page {id: "page_B2"})
ON CREATE SET pB2.number = 2;

MATCH (wB:Witness {id: "witness_B"})
MATCH (pB2:Page {id: "page_B2"})
MERGE (wB)-[:HAS_PAGE]->(pB2);

MERGE (lB2_1:Line {id: "line_B2_1"})
ON CREATE SET lB2_1.number = 1, lB2_1.content = "hoc in principio erat";

MERGE (lB2_2:Line {id: "line_B2_2"})
ON CREATE SET lB2_2.number = 2, lB2_2.content = "omnia per ipsum apud deum";

MATCH (pB2:Page {id: "page_B2"})
MATCH (l1:Line {id: "line_B2_1"})
MATCH (l2:Line {id: "line_B2_2"})
MERGE (pB2)-[:HAS_LINE]->(l1)
MERGE (pB2)-[:HAS_LINE]->(l2);


// ----------------------------------------------------------
// 3. LOGICAL HIERARCHY: Chapter → Paragraph → Sentence
// ----------------------------------------------------------

MERGE (ch1:Chapter {id: "chapter_1"})
ON CREATE SET ch1.number = 1, ch1.title = "De Verbo";

MATCH (t:Text {id: "text_001"})
MATCH (ch1:Chapter {id: "chapter_1"})
MERGE (t)-[:HAS_CHAPTER]->(ch1);

// Paragraph 1
MERGE (p1_1:Paragraph {id: "para_1_1"})
ON CREATE SET p1_1.number = 1;

MATCH (ch1:Chapter {id: "chapter_1"})
MATCH (p:Paragraph {id: "para_1_1"})
MERGE (ch1)-[:HAS_PARAGRAPH]->(p);

// Sentences in Paragraph 1
MERGE (s1:Sentence {id: "sent_1_1_1"})
ON CREATE SET s1.number = 1, s1.content = "In principio erat verbum et verbum erat apud deum";

MERGE (s2:Sentence {id: "sent_1_1_2"})
ON CREATE SET s2.number = 2, s2.content = "et deus erat verbum";

MATCH (p:Paragraph {id: "para_1_1"})
MATCH (s1:Sentence {id: "sent_1_1_1"})
MATCH (s2:Sentence {id: "sent_1_1_2"})
MERGE (p)-[:HAS_SENTENCE]->(s1)
MERGE (p)-[:HAS_SENTENCE]->(s2);

// Paragraph 2
MERGE (p1_2:Paragraph {id: "para_1_2"})
ON CREATE SET p1_2.number = 2;

MATCH (ch1:Chapter {id: "chapter_1"})
MATCH (p:Paragraph {id: "para_1_2"})
MERGE (ch1)-[:HAS_PARAGRAPH]->(p);

MERGE (s3:Sentence {id: "sent_1_2_1"})
ON CREATE SET s3.number = 1, s3.content = "hoc erat in principio apud deum";

MERGE (s4:Sentence {id: "sent_1_2_2"})
ON CREATE SET s4.number = 2, s4.content = "omnia per ipsum apud deum";

MATCH (p:Paragraph {id: "para_1_2"})
MATCH (s3:Sentence {id: "sent_1_2_1"})
MATCH (s4:Sentence {id: "sent_1_2_2"})
MERGE (p)-[:HAS_SENTENCE]->(s3)
MERGE (p)-[:HAS_SENTENCE]->(s4);


// ----------------------------------------------------------
// 4. ALIGNMENT: Sentence ←→ Line
// ----------------------------------------------------------
// This is the key relationship that bridges the logical and
// physical hierarchies. A sentence may align with lines from
// MULTIPLE witnesses (that's the whole point of collation).

// Sentence 1 aligns with lines from both witnesses
MATCH (s:Sentence {id: "sent_1_1_1"})
MATCH (l:Line)
WHERE l.id IN ["line_A1_1", "line_A1_2", "line_B1_1", "line_B1_2"]
MERGE (s)-[:ALIGNS_WITH]->(l);

// Sentence 2
MATCH (s:Sentence {id: "sent_1_1_2"})
MATCH (l:Line)
WHERE l.id IN ["line_A1_3", "line_B1_3"]
MERGE (s)-[:ALIGNS_WITH]->(l);

// Sentence 3
MATCH (s:Sentence {id: "sent_1_2_1"})
MATCH (l:Line)
WHERE l.id IN ["line_A2_1", "line_B2_1"]
MERGE (s)-[:ALIGNS_WITH]->(l);

// Sentence 4
MATCH (s:Sentence {id: "sent_1_2_2"})
MATCH (l:Line)
WHERE l.id IN ["line_A2_2", "line_B2_2"]
MERGE (s)-[:ALIGNS_WITH]->(l);


// ----------------------------------------------------------
// 5. ANNOTATIONS
// ----------------------------------------------------------
// Annotations can point to any node (Sentence, Line, etc.)
// We use separate MATCH + MERGE blocks per annotation.

MERGE (a1:Annotation {id: "anno_001"})
ON CREATE SET
  a1.type    = "note",
  a1.content = "Key theological statement, compare with John 1:1",
  a1.author  = "Scholar A";

MATCH (a1:Annotation {id: "anno_001"})
MATCH (target:Sentence {id: "sent_1_1_1"})
MERGE (a1)-[:ANNOTATES]->(target);

MERGE (a2:Annotation {id: "anno_002"})
ON CREATE SET
  a2.type    = "variant",
  a2.content = "Witness B inverts word order: verbum erat instead of erat verbum",
  a2.author  = "Scholar A";

MATCH (a2:Annotation {id: "anno_002"})
MATCH (target:Line {id: "line_A1_1"})
MERGE (a2)-[:ANNOTATES]->(target);
