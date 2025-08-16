[![Made with FastAPI](https://img.shields.io/badge/FastAPI-🚀-turquoise?style=for-the-badge)](#)
[![LLM-Ready](https://img.shields.io/badge/LLM-Ready-purple?style=for-the-badge)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

# 🔍 TruthLens — Summaries, Deep Dives & a 0–100 Truth Score

A founder-friendly toolkit to summarize YouTube videos and user-provided texts (e.g., book forewords), extract factual claims, gather sources, and compute a **0–100 Truth Score**—with a clean Markdown report you can share.

## 🔗 Table of Contents
- [Features](#features)
- [Quickstart](#quickstart)
- [API Endpoints](#api-endpoints)
- [How Truth Scoring Works](#how-truth-scoring-works)
- [Legal & Ethics](#legal--ethics)
- [Architecture](#architecture)
- [Examples](#examples)
- [Roadmap](#roadmap)
- [License](#license)

## Features
- TL;DR & TL;DW (for videos w/ timestamps)
- Executive Summary (300–600 words) and Deep Dive
- Claim Extraction → Web Corroboration → **Truth Score (0–100)**
- “Critical-style” 1–5 ⭐ rating (clarity, evidence, bias)
- JSON + Markdown reports
- Optional Streamlit UI

## Quickstart
```bash
git clone https://github.com/yourname/truthlens.git
cd truthlens
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # add your keys
make run  # FastAPI at http://localhost:8000
make ui   # Streamlit at http://localhost:8501
API Endpoints
POST /analyze/youtube → { "url": "https://youtu.be/..." }

POST /analyze/text → { "content": "your text" }

POST /analyze/web → { "url": "...", "extracted_text": "..." }

Note: Provide text you have the right to use. Do not scrape or republish copyrighted content.

How Truth Scoring Works
Extract top claims with LLM

Search web (Tavily/Serper/DDG) for independent sources

LLM assesses support vs contradiction using snippets

Aggregate to a final 0–100 with a transparent rubric

Legal & Ethics
Use official APIs where possible (YouTube Data API)

Avoid scraping paywalled or copyrighted text (e.g., Amazon “Look Inside”)

Whisper transcription is local and opt-in for personal research

Reports include links & short quotes/snippets under fair use (brief, attributed)

Architecture
mermaid
Copy
Edit
flowchart LR
A[Input (YouTube URL / Text)] --> B[Transcript/Content]
B --> C[Summarizer LLM]
B --> D[Claim Extractor LLM]
D --> E[Search Provider (Tavily/Serper/DDG)]
E --> F[Fact Checker LLM]
F --> G[Scoring (0–100)]
C --> H[Markdown + JSON]
G --> H
Examples
YouTube: Provide URL with public transcript → get TL;DW, Summary, Deep Dive, Claims, Truth Score

Books: Paste your own foreword/excerpt text → same pipeline

Roadmap
Multi-provider LLM router

PDF ingestion

Per-claim confidence intervals

License
MIT

yaml
Copy
Edit

---

### How to use it on your example book
For *The Founding Myth* by Andrew L. Seidel, paste a short, legally shareable excerpt (e.g., your notes or publicly posted quotations) into the `/analyze/text` endpoint. The app will produce the deep-dive, claim table, truth score, and a “critical-style” star rating. (You can also attach a bibliography of sources for stronger corroboration.)
---
