# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0-beta | Yes |
| < 1.0 | No |

## Reporting a Vulnerability

If you discover a security vulnerability in TextLPG, please report it responsibly.

**Do NOT open a public issue.** Instead, email the maintainer directly:

- **Email:** yulchiebahodir@gmail.com
- **Subject:** `[SECURITY] TextLPG - <brief description>`

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response time

- **Acknowledgment:** within 48 hours
- **Assessment:** within 1 week
- **Fix/patch:** as soon as possible, depending on severity

## Scope

This project connects to:
- **Neo4j** (local database)
- **MySQL** (local database via XAMPP)
- **Ollama** (local LLM inference)

All connections are local by default. The `config.env` file contains database credentials and should **never** be committed to version control.

## Best Practices for Users

- Keep `config.env` out of git (it is in `.gitignore`)
- Use strong passwords for Neo4j and MySQL
- Run Ollama locally -- do not expose it to the internet
- Keep dependencies up to date (`pip install --upgrade -r requirements.txt`)
