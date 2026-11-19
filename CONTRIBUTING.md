# Contributing to TextLPG

Thank you for your interest in contributing to TextLPG! This project is part of an MSc internship at Georg-August-Universitat Gottingen, but contributions and suggestions are welcome.

## How to Contribute

### Reporting Bugs

1. Check existing [Issues](../../issues) to avoid duplicates
2. Open a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Python version, OS, Neo4j version)

### Suggesting Features

Open an issue with the `enhancement` label. Describe:
- What problem it solves
- How you envision it working
- Any alternatives you considered

### Submitting Code

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** -- follow the existing code style
4. **Test** that everything works:
   ```bash
   python -m textlpg.config       # connection works
   python -m textlpg.queries      # queries run
   streamlit run ui/app.py         # UI loads
   ```
5. **Commit** with a clear message:
   ```bash
   git commit -m "Add: brief description of what you did"
   ```
6. **Push** and open a Pull Request

## Development Setup

```bash
git clone <your-fork-url>
cd Textlpg

python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

You will also need:
- **Neo4j** running locally with the TextLPG database loaded
- **MySQL** (via XAMPP) for research benchmarks
- **Ollama** with `gemma2:9b` for enrichment and NL query features

## Project Structure

| Module | Purpose |
|--------|---------|
| `textlpg/config.py` | Database connection |
| `textlpg/ingest.py` | Data ingestion pipeline |
| `textlpg/queries.py` | Cypher query library |
| `textlpg/enrich.py` | LLM enrichment |
| `textlpg/nl_query.py` | Natural language querying |
| `ui/app.py` | Streamlit interface |
| `notebooks/research.ipynb` | Research benchmarks |

## Code Style

- Python 3.12+
- Keep functions focused and well-commented (this is also a learning project)
- Use existing patterns -- look at how other modules are structured before adding new ones

## Questions?

Open an issue or contact the maintainer at **yulchiebahodir@gmail.com**.
