# TextLPG

A graph-based tool for modelling pluriform texts with aligned versions,
structural information and annotations using a Labeled Property Graph (LPG).

Built with Neo4j / Memgraph + Python + LLM-based querying.

## Project Structure
```
Textlpg/
├── data/sample/        ← sample dataset
├── textlpg/            ← main Python package
├── cypher/             ← raw Cypher query files
├── notebooks/          ← Jupyter demo
├── ui/                 ← Streamlit browser UI
├── requirements.txt
└── README.md
```

## Setup

1. Clone the repository
2. Create and activate virtual environment:
   python -m venv .venv
   .venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Create config.env in the project root:
   NEO4J_URI=neo4j://127.0.0.1:7553
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here

5. Start Neo4j Desktop and run:
   python textlpg/config.py

## Usage

(To be completed as project develops)

## Internship

Georg-August-Universität Göttingen
Duration: 01.04.2026 – 30.06.2026
```

---

## `requirements.txt`

Open it and paste what you have installed so far:
```
neo4j
python-dotenv