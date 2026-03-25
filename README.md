<div align="center">
  <img src="assets/header.jpg" alt="Mnemosyne" width="380" />
</div>

<h1 align="center">Mnemosyne</h1>
<p align="center"><strong>An AI that actually remembers you.</strong></p>
<p align="center">Not a chatbot. Not a wrapper. A living memory system that learns, evolves, and acts.</p>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Tests](https://img.shields.io/badge/50%2B_Tests-Passing-brightgreen)

</div>

---

## The Problem

Every AI you've used forgets you.

You explain your project. You share your preferences. You upload documents. And the next session? Gone. Start over. Explain again. And again. And again.

That's not intelligence. That's a search engine wearing a mask.

## The Solution

<div align="center">
  <img src="assets/logo.jpg" alt="Mnemosyne" width="180" />
</div>

**Mnemosyne** (Μνημοσύνη) is the Greek goddess of memory - the mother of all knowledge.

This project is built on one idea: **an AI without memory is not intelligent.**

Mnemosyne doesn't just answer questions. It builds a persistent, evolving model of *you*. Your facts, your projects, your goals, your documents, your patterns - all stored, connected, and made available across every conversation.

The more you use it, the smarter it gets. Not because the model changes. Because **the memory grows.**

---

## What It Does

**Remembers everything.**
Facts are automatically extracted, classified, and stored. When you say "I work at Google," it remembers. When you later say "I switched to OpenAI," it tracks the change. Old facts aren't deleted - they're versioned. Nothing is lost.

**Thinks before it answers.**
Every response goes through a reasoning pipeline: it classifies your query, selects the right retrieval strategy, builds context from your memories, documents, and conversation history, then generates a response grounded in what it actually knows about you.

**Plans and executes.**
Need to do something complex? Mnemosyne breaks it into steps, tracks dependencies, monitors progress, and can run autonomously with configurable guardrails. Not hallucinated plans - real execution tracking.

**Reads your documents.**
Upload PDFs, text files, anything. They're chunked, embedded, and made searchable. Ask a question and Mnemosyne pulls from both your conversations AND your documents.

**Detects change over time.**
Moved cities? Changed jobs? Mnemosyne notices. It tracks temporal patterns, flags stale information, and surfaces things that need attention.

**Stays secure.**
Multi-layer prompt injection defense. Granular permissions. Trust scoring. Tool policies. Autonomy limits. Your data stays yours.

---

## How It Works

```
  You speak
     │
     ▼
┌─────────────────────────────────────┐
│           FastAPI Backend           │
│                                     │
│  Fact Extraction ──► SQLite (facts) │
│  Semantic Search  ──► ChromaDB      │
│  RAG Pipeline     ──► Documents     │
│  Reasoning Engine ──► Planning      │
│  Execution Engine ──► Tools         │
│  Temporal Monitor ──► Change Det.   │
│  Security Layer   ──► Trust/Policy  │
│                                     │
│          LLM (MiMo / Ollama)        │
└────────────────────┬────────────────┘
                     │
              React Dashboard
          (Glassmorphic UI, realtime)
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/secretprojet143-web/Mnemosyne.git
cd Mnemosyne

# Configure
cp .env.example .env
# Add your API key to .env

# Backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, register, and start talking. Your memory builds itself.

---

## Built With

| | |
|---|---|
| **Backend** | Python, FastAPI, Pydantic |
| **Frontend** | React 18, TypeScript, Vite, Framer Motion |
| **Storage** | SQLite + ChromaDB |
| **Embeddings** | sentence-transformers/all-MiniLM-L6-v2 |
| **LLM** | Xiaomi MiMo, OpenRouter, or local Ollama |
| **Tests** | pytest (50+ files, 600+ cases) |

---

## Why Not Just Use ChatGPT?

| | ChatGPT | Mnemosyne |
|---|---|---|
| Remembers across sessions | Limited, often wrong | Everything, versioned |
| Document understanding | Basic upload | Full RAG pipeline |
| Reasoning transparency | Black box | Visible reasoning states |
| Execution tracking | None | Plans, steps, dependencies |
| Security | Trust OpenAI | Self-hosted, full control |
| Your data | On their servers | On your machine |

---

## License

Source-available. See [LICENSE](LICENSE).

**You can:** view the code, run it locally, study the architecture.
**You cannot:** copy it, redistribute it, use it commercially, or remove attribution.

For licensing inquiries, contact through GitHub.

---

<div align="center">
  <sub>Built by <strong>Youness AIT BAKROM</strong></sub>
  <br /><br />
  <sub><em>Intelligence without memory is just autocomplete.</em></sub>
</div>
