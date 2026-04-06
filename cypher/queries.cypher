// ============================================================
// TextLPG — Example Queries
// ============================================================
// Run these in Neo4j Browser (localhost:7474) after ingesting data.
// Each query demonstrates a different Cypher concept.
// ============================================================


// ----------------------------------------------------------
// BASIC READS (MATCH + RETURN)
// ----------------------------------------------------------

// Q1: Get all texts
// MATCH finds nodes by label, RETURN selects what to show.
MATCH (t:Text)
RETURN t.id, t.title, t.language;

// Q2: Get all witnesses for a text
// The arrow (-[:HAS_WITNESS]->) follows the relationship direction.
MATCH (t:Text {id: "text_001"})-[:HAS_WITNESS]->(w:Witness)
RETURN w.siglum, w.source;

// Q3: Get all lines from Witness A, ordered by page and line number
// Variable-length patterns chain multiple hops.
MATCH (w:Witness {siglum: "A"})-[:HAS_PAGE]->(p:Page)-[:HAS_LINE]->(l:Line)
RETURN p.number AS page, l.number AS line, l.content
ORDER BY p.number, l.number;


// ----------------------------------------------------------
// TRAVERSALS (following paths)
// ----------------------------------------------------------

// Q4: Full physical hierarchy — from Text down to Lines
MATCH (t:Text)-[:HAS_WITNESS]->(w)-[:HAS_PAGE]->(p)-[:HAS_LINE]->(l)
RETURN t.title, w.siglum, p.number AS page, l.number AS line, l.content
ORDER BY w.siglum, p.number, l.number;

// Q5: Full logical hierarchy — from Text down to Sentences
MATCH (t:Text)-[:HAS_CHAPTER]->(ch)-[:HAS_PARAGRAPH]->(para)-[:HAS_SENTENCE]->(s)
RETURN ch.title, para.number AS paragraph, s.number AS sentence, s.content
ORDER BY para.number, s.number;


// ----------------------------------------------------------
// ALIGNMENT QUERIES (bridging physical ↔ logical)
// ----------------------------------------------------------

// Q6: Which lines does a sentence align with?
// Shows which manuscript lines correspond to a logical sentence.
MATCH (s:Sentence {id: "sent_1_1_1"})-[:ALIGNS_WITH]->(l:Line)
RETURN s.content AS sentence, l.id AS line_id, l.content AS line_text;

// Q7: Compare how witnesses render the same sentence
// Joins alignment with the physical hierarchy to show witness info.
MATCH (s:Sentence {id: "sent_1_1_1"})-[:ALIGNS_WITH]->(l:Line)<-[:HAS_LINE]-(p:Page)<-[:HAS_PAGE]-(w:Witness)
RETURN s.content AS sentence, w.siglum AS witness, l.content AS witness_text
ORDER BY w.siglum;

// Q8: Find all sentences that have lines in BOTH witnesses
// COLLECT gathers values into a list. WITH passes intermediate results.
MATCH (s:Sentence)-[:ALIGNS_WITH]->(l:Line)<-[:HAS_LINE]-(:Page)<-[:HAS_PAGE]-(w:Witness)
WITH s, COLLECT(DISTINCT w.siglum) AS witnesses
WHERE SIZE(witnesses) > 1
RETURN s.id, s.content, witnesses;


// ----------------------------------------------------------
// ANNOTATION QUERIES
// ----------------------------------------------------------

// Q9: All annotations with their targets
MATCH (a:Annotation)-[:ANNOTATES]->(target)
RETURN a.id, a.type, a.author, a.content, labels(target)[0] AS target_type, target.id AS target_id;

// Q10: Find variant annotations (textual differences between witnesses)
MATCH (a:Annotation {type: "variant"})-[:ANNOTATES]->(target)
RETURN a.content, target.id, target.content;


// ----------------------------------------------------------
// AGGREGATION & STATISTICS
// ----------------------------------------------------------

// Q11: Count nodes by label
// labels(n) returns a list of labels on a node.
MATCH (n)
RETURN labels(n)[0] AS label, COUNT(n) AS count
ORDER BY count DESC;

// Q12: Lines per witness
MATCH (w:Witness)-[:HAS_PAGE]->(p)-[:HAS_LINE]->(l)
RETURN w.siglum, COUNT(l) AS line_count;


// ----------------------------------------------------------
// SEARCH (WHERE + CONTAINS)
// ----------------------------------------------------------

// Q13: Find lines containing a specific word
MATCH (l:Line)
WHERE l.content CONTAINS "verbum"
RETURN l.id, l.content;

// Q14: Find lines containing "verbum" and show which witness they belong to
MATCH (w:Witness)-[:HAS_PAGE]->(:Page)-[:HAS_LINE]->(l:Line)
WHERE l.content CONTAINS "verbum"
RETURN w.siglum, l.id, l.content;


// ----------------------------------------------------------
// UPDATES (SET, REMOVE)
// ----------------------------------------------------------

// Q15: Add a property to a node
// SET adds or updates properties.
// MATCH (t:Text {id: "text_001"})
// SET t.editor = "Scholar B"
// RETURN t;

// Q16: Remove a property
// REMOVE deletes a property from a node.
// MATCH (t:Text {id: "text_001"})
// REMOVE t.editor
// RETURN t;


// ----------------------------------------------------------
// DELETE (with care!)
// ----------------------------------------------------------

// Q17: Delete a specific annotation
// DETACH DELETE removes the node AND all its relationships.
// MATCH (a:Annotation {id: "anno_001"})
// DETACH DELETE a;

// Q18: Clear entire database (use with caution!)
// MATCH (n) DETACH DELETE n;
