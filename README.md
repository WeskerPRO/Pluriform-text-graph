# 📖 Pluriform Text Graph

> **Modeling pluriform texts as a Labeled Property Graph**

A graph-based system for storing, querying, and enriching parallel Bible translations (64 languages) using Neo4j, Python, and local LLMs.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com)
[![Ollama](https://img.shields.io/badge/Ollama-gemma2:9b-black?logo=ollama&logoColor=white)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Version](https://img.shields.io/badge/version-1.0--beta-blue)]()

---

## 🧠 What Is This?

Pluriform Text Graph (PTG) explores how **pluriform texts** — texts that exist in many parallel versions — can be modeled using a **Labeled Property Graph (LPG)**.

The dataset is the **Bible in 64 languages**: ~33,000 verses × 64 translations = **~1.3 million passages**. Each passage is stored as a node in a Neo4j graph, connected to its verse, chapter, book, and language.

On top of the raw text, an **LLM (gemma2:9b via Ollama)** generates annotations — summaries, themes, keywords, sentiment — that are stored directly in the graph as new nodes.

---

## 🏗️ Graph Model (v2)

```
(:Corpus)
    │
    ├──[:HAS_BOOK]──▶ (:Book {id, code})  ◀──[:VERSION_OF]── (:Text {id, version})
    │                    │                                        ▲
    │              [:HAS_CHAPTER]                                 │
    │                    ▼                                   [:IN_TEXT]
    │              (:Chapter {id, number})                        │
    │                    │                               (:Passage {content})
    │              [:HAS_VERSE]                                   ▲
    │                    ▼                                        │
    │              (:Verse {id, number}) ───[:HAS_PASSAGE]────────┘
    │
    └──[:HAS_TEXT]──▶ (:Text)

                                          (:Annotation {type, content, author})
                                               │
                                         [:ANNOTATES]
                                               ▼
                                          (:Verse)
```

### 📊 Node Counts

| Node | Count | Description |
|------|------:|-------------|
| 🌐 Corpus | 1 | Root node |
| 📕 Book | 66 | Genesis to Revelation |
| 📄 Chapter | 1,249 | All chapters |
| 📜 Verse | 33,921 | All verses |
| 🌍 Text | 3,047 | One per book per language |
| 💬 Passage | ~1,326,545 | Verse content in each language |
| 🏷️ Annotation | *varies* | LLM-generated enrichments |

### 🔑 Key Query — "Get Genesis 2:1 in Afrikaans"

```cypher
MATCH (v:Verse {id: "b.GEN.002.001"})
      -[:HAS_PASSAGE]->(p:Passage)
      -[:IN_TEXT]->(t:Text {version: "af"})
RETURN p.content
```

No Corpus traversal needed. Direct path: **Verse → Passage → Text**.

---

## 📁 Project Structure

```
pluriform-text-graph/
├── 📄 config.env              ← Neo4j credentials (not in git)
├── 📄 requirements.txt        ← Python dependencies
│
├── 📂 textlpg/                ← Main Python package
│   ├── config.py              ← Neo4j connection manager
│   ├── ingest.py              ← Data ingestion pipeline (7 steps)
│   ├── queries.py             ← Cypher queries wrapped in Python
│   ├── enrich.py              ← LLM enrichment via Ollama
│   ├── nl_query.py            ← Natural language → Cypher querying
│   └── agent_query.py         ← Self-healing agentic queries
│
├── 📂 ui/                     ← Browser-based interface
│   └── app.py                 ← Streamlit app (6 tabs)
│
├── 📂 notebooks/              ← Research & analysis
│   └── research.ipynb         ← Neo4j vs MySQL benchmarks (5 RQs)
│
├── 📂 cypher/                 ← Raw Cypher files (for learning & Neo4j Browser)
│   ├── schema.cypher          ← Constraints & indexes
│   ├── queries.cypher         ← 23 example queries
│   └── ingest.cypher          ← Manual ingestion examples
│
└── 📂 data/                   ← Dataset (not in git)
    ├── meta.json              ← Corpus metadata + 3,047 text entries
    ├── 📂 layers/             ← Structural nodes (books, chapters, verses)
    └── 📂 texts/              ← 3,047 plain text files (one per book per language)
```

---

## 🚀 Setup

### Prerequisites

- **Python 3.12+**
- **Neo4j Desktop** (or Neo4j Community Server)
- **Ollama** (for LLM enrichment)

### 1. Clone & Install

```bash
git clone https://github.com/WeskerPRO/pluriform-text-graph.git
cd pluriform-text-graph

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Neo4j

Create `config.env` in the project root:

```env
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```

### 3. Test Connection

```bash
python -m textlpg.config
# Output: Connection successful
```

### 4. Create Schema & Ingest Data

Run the constraints in Neo4j Browser (paste from `cypher/schema.cypher`), then:

```bash
python -m textlpg.ingest
```

This loads **~1.3M nodes** and **~2.7M relationships** in 7 steps.

### 5. Install Ollama (for enrichment)

```bash
ollama pull gemma2:9b
```

---

## 💻 Usage

### 🔍 Query verses

```python
from textlpg.queries import get_verse_text, compare_verse, search_verses

# Get Genesis 1:1 in English
get_verse_text("b.GEN.001.001", language="en")
# [{"language": "en", "content": "In the beginning God created the heaven and the earth."}]

# Compare across languages
compare_verse("b.PSA.023.001", ["en", "de", "fr", "ar"])

# Search for a keyword
search_verses("love", language="en", limit=10)
```

### 🤖 Enrich with LLM

```bash
# Single verse, single annotation type
python -m textlpg.enrich --verse b.GEN.001.001 --type summary

# Single verse, all types (summary, themes, keywords, sentiment)
python -m textlpg.enrich --verse b.JHN.003.016

# Demo mode — 3 famous verses
python -m textlpg.enrich
```

### 💬 Natural Language Querying

```bash
# Single question
python -m textlpg.nl_query --question "What does John 3:16 say in German?"

# Interactive mode
python -m textlpg.nl_query
```

### 🖥️ Streamlit UI

```bash
streamlit run ui/app.py
```

6 tabs: Browse, Read, Compare, Search, Enrich, Ask

### 📊 Run query tests

```bash
python -m textlpg.queries
```

---

## 📌 Version History

| Version | Milestone | Description |
|---------|-----------|-------------|
| **v0.1** | 🔌 Connection | Project setup, Neo4j connection (`config.py`) |
| **v0.2** | 📐 Schema | Graph model design — v1 → v2 redesign (Passage nodes, VERSION_OF) |
| **v0.3** | 📥 Ingestion | Data pipeline loading ~1.3M nodes into Neo4j (`ingest.py`) |
| **v0.4** | 🔍 Queries | 23 Cypher queries + Python query module (`queries.py`) |
| **v0.5** | 🤖 Enrichment | LLM annotations via Ollama/gemma2:9b (`enrich.py`) |
| **v0.6** | 💬 NL Query | Natural language → Cypher via LLM (`nl_query.py`) |
| **v0.7** | 🖥️ UI | Streamlit browser interface — 6 tabs (`ui/app.py`) |
| **v0.8** | 📊 Research | Neo4j vs MySQL benchmarks, 5 research questions (`notebooks/research.ipynb`) |
| **v0.9** | 🤖 Agent | Self-healing agentic queries — auto-retries failed Cypher (`agent_query.py`) |
| **v1.0-beta** | 📦 Beta | All features complete — pending supervisor review |

---

## 🏛️ Internship

**Georg-August-Universität Göttingen**
MSc Applied Data Science — Internship Module

- 📅 Duration: April 1 – June 1, 2026
- 🎯 Topic: Modeling pluriform texts as Labeled Property Graphs
- 🛠️ Stack: Python, Neo4j, Cypher, MySQL, Ollama (LLM), Streamlit
