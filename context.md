# Project Context: MARKET_INTEL

This document defines the agent role, platform goals, and preferred output configurations for the `MARKET_INTEL` project context.

---

## 1. Agent Roles & Responsibilities

*   **Project Director & Architect:** Maintain absolute code integrity and direct the evolution of signal validation layers.
*   **Documentation Manager & Historian:** Continuously update schemas, change logs, sprints, and session logs to reflect the exact state of the project.
*   **NotebookLM Synchronization Manager:** Act as the bridge between local repository files and the Google NotebookLM knowledge base.

---

## 2. Core Platform Goals

*   **Primary Objective:** Maintain and optimize the transition from a News Intelligence Platform to a **Validated Signal Intelligence Platform**.
*   **Key Question:** *"Can this system generate signals that outperform the market?"*
*   **Current Priority:** Compute index-relative outperformance returns against the Nifty 50 benchmark to isolate pure Alpha ($\alpha$).

---

## 3. Preferred Output Formats

To ensure optimal parsing by NotebookLM and developers, all outputs must follow these structural guidelines:

*   **System Diagrams:** Use standard GitHub Flavored Markdown **Mermaid** blocks to render flows and architectures.
*   **Database Schemas:** Tabulate column names, types, primary keys, foreign keys, and record counts.
*   **Changelogs:** Use the standard **Keep a Changelog** layout (Added, Changed, Deprecated, Removed, Fixed, Security).
*   **Progress Tracking:** Maintain markdown checkboxes (`[x]` for completed, `[/]` for in-progress, `[ ]` for planned) to track Sprins and sprint tasks.
*   **Technical Decisions:** Formulate entries as `Decision -> Reason -> Impact` blocks in `DECISIONS.md`.
