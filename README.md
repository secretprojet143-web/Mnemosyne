<div align="center">
  <img src="assets/header.jpg" alt="Mnemosyne" width="400" />
  <h1>Mnemosyne</h1>
  <p><em>The AI That Never Forgets</em></p>

  ![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
  ![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
  ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
  ![Tests](https://img.shields.io/badge/Tests-50%2B-passing-brightgreen)
  ![License](https://img.shields.io/badge/License-Source--Available-red)

  > **This project is source-available, NOT open-source.**
  > Viewing is permitted. Copying, redistribution, and commercial use are **prohibited**.
  > See [LICENSE](LICENSE) for full terms.
</div>

---

## What Is Mnemosyne?

In Greek mythology, **Mnemosyne** (Μνημοσύνη) is the Titan goddess of **memory** - the mother of all knowledge. Every conversation you have, every fact you share, every document you upload becomes part of a living, evolving memory that grows with you.

This project is the technical realization of that idea: **an AI operating system that remembers, reasons, plans, and acts autonomously** - built from scratch, not a wrapper around existing chatbots.

---

## Why This Exists

<div align="center">
  <img src="assets/logo.jpg" alt="Mnemosyne Leaf" width="220" />
</div>

Most AI assistants are stateless. You ask a question, get an answer, and the next conversation starts from zero. That's not intelligence - that's a search engine with a personality.

Mnemosyne is different. It was built on a single conviction: **intelligence requires memory**.

Every interaction is stored, classified, and made retrievable. Facts evolve. Contradictions are detected. Knowledge is consolidated over time. The system doesn't just respond to you - it *learns* you.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│   React + TypeScript + Vite   │   Glassmorphic Dashboard UI      │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                     BACKEND (FastAPI)                             │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Auth Layer  │  │ Memory Core  │  │    AI Engine           │  │
│  │ (JWT +      │  │ (Facts,      │  │    (Reasoning,         │  │
│  │  Sessions)  │  │  Semantics,  │  │     Planning,          │  │
│  │             │  │  RAG,        │  │     Execution,         │  │
│  │             │  │  Temporal,   │  │     Autonomy)          │  │
│  │             │  │  Continuity) │  │                        │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Security & Trust Layer                         │ │
│  │  Prompt Injection Defense · Tool Policies · Access Control  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ SQLite  │   │ ChromaDB │   │ LLM APIs │
   │  (Data) │   │(Vectors) │   │(Xiaomi /  │
   │         │   │          │   │ OpenRouter│
   │         │   │          │   │ / Ollama) │
   └─────────┘   └──────────┘   └──────────┘
```

---

## Core Capabilities

### Persistent Memory
- **Fact Extraction**: Automatically extracts and stores facts from every conversation
- **Fact Lifecycle**: Facts are versioned - superseded, outdated, or corrected facts are tracked, not deleted
- **Conflict Detection**: Identifies contradictions between facts and flags them
- **Fact Provenance**: Every fact knows where it came from (explicit, inferred, imported, corrected)
- **Pinning & Visibility**: Pin critical facts. Control visibility (general, personal, sensitive, restricted)

### Semantic Memory & RAG
- **Vector Search**: ChromaDB-powered semantic similarity search across all stored memories
- **Document Intelligence**: Upload PDFs, text files - searchable with contextual answers
- **Multiple Retrieval Modes**: balanced, deep_memory, focused, document_first, privacy_safe
- **Smart Context Budgeting**: Automatically allocates context window between memories, documents, and recent chat

### Reasoning & Planning
- **Reasoning States**: Multi-step reasoning with constraints, assumptions, candidate actions, and confidence scoring
- **Execution Plans**: Convert reasoning into actionable plans with ordered steps
- **Dependency Tracking**: Steps can depend on other steps - blocked steps prevent downstream execution
- **Self-Verification**: Each reasoning state includes self-check validation

### Autonomous Execution
- **Initiative Modes**: quiet, balanced, active, coach - controls how proactive the AI is
- **Execution Orchestration**: Plans are executed step-by-step with status tracking
- **Tool Registry**: Register tools with policies, permissions, and security scanning
- **Tool Execution**: Multi-layer confirmation (user consent, policy check, security scan)

### Temporal Intelligence
- **Change Detection**: Monitors facts over time and detects when things change (name, location, role)
- **Stale Fact Detection**: Flags facts that haven't been confirmed recently
- **Aging Items**: Detects aging open loops and goals that need attention
- **Recurring Patterns**: Identifies repeating open loop patterns

### Continuity System
- **Projects**: Organize work into projects with status and priority tracking
- **Goals**: Set goals with target dates, link to projects
- **Open Loops**: Track unfinished threads across conversations
- **Conversation Linking**: Automatically links conversations to relevant projects

### Evolution & Learning
- **Episodic Memories**: Capture significant conversation episodes
- **Reflections**: Generate insights from conversation patterns
- **Daily/Weekly Learnings**: Consolidated knowledge summaries over time
- **Memory Consolidation**: Automatic background consolidation of facts and learnings

### Security & Trust
- **Prompt Injection Defense**: Multi-layer scanning for injection attempts
- **Permission System**: Granular permissions per tool and operation
- **Trust Scoring**: Annotates and scores the trustworthiness of inputs
- **Security Scanning**: Scans both text and structured data for threats
- **Autonomy Guardrails**: Hard limits on steps and tool calls per autonomous run

### Proactive Intelligence
- **Daily Briefings**: Generates proactive summaries of your memory state
- **Smart Suggestions**: Context-aware suggestions based on current conversation
- **Recommendation Engine**: Promotes memory candidates, insights, and project ideas
- **Observability**: Full logging of retrieval decisions, memory extractions, and system events

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.9+, FastAPI, Pydantic |
| **Frontend** | React 18, TypeScript, Vite, Framer Motion |
| **Database** | SQLite (operational data) |
| **Vectors** | ChromaDB (semantic search) |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
| **LLM** | Xiaomi MiMo, OpenRouter, Ollama (local) |
| **Auth** | JWT-based authentication |
| **Tests** | pytest (50+ test files, 600+ test cases) |

---

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- An LLM API key (Xiaomi MiMo, OpenRouter, or local Ollama)

### 1. Clone & Configure

```bash
git clone https://github.com/secretprojet143-web/Mnemosyne.git
cd Mnemosyne
cp .env.example .env
```

Edit `.env` and add your API key:

```env
LLM_PROVIDER=xiaomi
XIAOMI_API_KEY=your_key_here
```

### 2. Run the Backend

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`.

### 3. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### 4. Use It

1. Open `http://localhost:5173`
2. Register an account
3. Start chatting - your memories build automatically

---

## Test Suite

```bash
pytest tests/ -v
```

The project includes **50+ test files** covering:
- Memory services (fact extraction, consolidation, retrieval)
- Autonomy (decision policies, handoff, runtime, readiness)
- Execution (state machines, recovery, step sync)
- Planning (generation, dependencies, health)
- Security (prompt injection, tool policies, permissions)
- Temporal (change detection, aging, reconfirmation)
- Reasoning (generation, validation, quality)
- Trust (propagation, scoring)

---

## License

This project is **source-available** under a custom restrictive license.

| Allowed | Prohibited |
|---------|-----------|
| View source code | Copy or redistribute |
| Run locally for evaluation | Commercial use |
| Study the architecture | Derivative works |
| | Remove copyright/attribution |

For commercial licensing inquiries, contact through GitHub.

**This software is protected by copyright law. Unauthorized use may result in civil and criminal penalties.**

---

<div align="center">
  <sub>Built by <strong>Youness AIT BAKROM</strong> &mdash; 2026</sub>
  <br />
  <sub>Mnemosyne - Because intelligence without memory is just autocomplete.</sub>
</div>
