# Contributing to Market-Intel

Welcome! We are excited that you are interested in contributing to Market-Intel. This project aims to bring rigor, transparency, and statistical validation to event-driven market intelligence.

---

## 💬 Community & Communication

We use **GitHub Discussions** as our central hub for community discussions. Please direct your conversations to the appropriate category:
*   **🙏 Q&A / Support**: Need help running the scrapers or configuring your local Ollama server? Ask here.
*   **💡 Ideas & Features**: Have a suggestion for an alpha-generating feature (e.g., sector neutral beta adjustments)? Pitch it here.
*   **🎉 Show and Tell**: Built a custom UI theme or a cool dashboard component? Show off your work!
*   **💬 General**: Any other discussions that do not fit into the other categories.

---

## 🛠️ Development Flow

We follow a structured Git branch and development workflow:

### 1. Find or Create an Issue
*   Before writing code, please search the open issues or create a new one (using our Bug Report or Feature Request templates) to discuss your proposed changes.

### 2. Branch Naming Convention
Create a local development branch using the following format:
*   `feature/issue-number-short-description` (e.g., `feature/42-relative-returns`)
*   `bugfix/issue-number-short-description` (e.g., `bugfix/17-playwright-timeout`)
*   `docs/short-description` (e.g., `docs/add-api-reference`)

### 3. Coding Guidelines
*   **Python Casing & Formatting**: Follow PEP 8 guidelines. Write clear variable and function names. Use standard camelCase or snake_case consistently.
*   **Path Safety**: Never use hardcoded path separators (use `Path` from python's `pathlib`). Always resolve paths relative to `BASE_DIR = Path(__file__).resolve().parent.parent.parent` (for scripts two levels deep) or the appropriate parent level.
*   **Secrets Security**: Never commit raw tokens, cookies, or password files. Ensure they are covered by `.gitignore`.

### 4. Submitting a Pull Request (PR)
*   Ensure that all local tests pass:
    ```bash
    python scripts/news_engine/test_engines.py
    ```
*   Verify that your local SQLite databases are uncorrupted.
*   Submit a Pull Request using our standard **Pull Request Template**. Make sure to link the PR to the relevant issue using `Closes #IssueNumber`.
