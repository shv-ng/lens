# 🔍 Lens — Real-Time AI News Verification & Conflict Detection Engine

> **Hackathon:** National Level Online Hackathon 2026 — Organized by Steps AI
> **Problem Statement:** PS3 — Open Track: AI Agents for Real-World Problems
> **Team:** Shivang Srivastava
> **Submission Date:** Sunday, May 25, 2026

---

## 📌 Problem I Chose to Solve

We live in an era of information overload where the same event gets reported with different facts, different framing, or sometimes gets completely ignored by certain outlets. A reader searching "Is the Indian government hiding unemployment data?" cannot easily tell whether this claim is supported, denied, or just absent from mainstream coverage.

**Lens** addresses this by acting as an AI-powered verification agent: it takes any claim or question, retrieves live news coverage from multiple source types (mainstream Indian media, international media, Reddit communities), detects narrative conflicts using an LLM, and synthesizes a structured, explainable verdict — all streamed in real time.

---

## 🎬 Demo Video

📽️ [Watch Demo](#) ← _Replace with your YouTube / Google Drive link_

---

## 🧠 My Approach & Key Technical Decisions

These are the decisions I made intentionally, and why:

**1. LangGraph over a simple chain**
I needed a pipeline where conflict detection could loop back and trigger more retrieval. A linear LangChain chain can't do this. LangGraph lets me model this as a proper state machine with conditional edges, so the deep-dive loop (re-fetch when conflict is found, max 2×) is a first-class architectural feature, not a hack.

**2. Fan-out parallelism for article fetching**
Google News, news org RSS feeds, and Reddit are all fetched concurrently using `asyncio.gather`. This cuts total fetch time to the slowest source rather than the sum of all sources. Given that the pipeline already has enough sequential steps (query → merge → conflict → verdict), minimizing IO wait was important.

**3. Semantic subreddit discovery with pgvector**
Instead of hardcoding subreddit lists, I seeded 5,000+ popular subreddits into PostgreSQL with pgvector embeddings. At runtime, query embeddings are compared against this table to find the most topically relevant communities. This makes Reddit retrieval dynamic and generalized to any topic, not just pre-configured ones.

**4. Hybrid ranking: cosine similarity + recency decay**
In `merge_rerank.py`, articles are scored as `0.7 × cosine_similarity + 0.3 × recency_score`. The recency score uses exponential decay with a 48-hour half-life (`e^(-age_hours/48)`). This prevents old but semantically similar articles from outranking genuinely fresh coverage.

**5. Three-type conflict detection in the LLM prompt**
The conflict detector is explicitly designed to catch three distinct failure modes:
- **User-article conflict**: the user's claim is ignored or denied by articles (silence = conflict)
- **Inter-source factual conflict**: two sources contradict each other on facts
- **Framing divergence**: same facts, but Indian vs Western sources tell different stories

Most fact-checking tools only catch type 2. Types 1 and 3 are often more important for Indian news contexts.

**6. SSE over WebSockets**
Server-Sent Events are simpler, stateless, and sufficient for a unidirectional stream (server → client). WebSockets would add unnecessary complexity for this use case.

**7. Redis caching on RSS feeds**
RSS feeds don't change every second. Caching with a 24-hour TTL means repeated queries on similar topics (common in a demo/hackathon context) don't hammer the same endpoints repeatedly, and response times drop significantly on warm cache.

---

## 🏗️ System Architecture

```
User Input (text / PDF / image)
          │
          ▼
    [ Query Node ]
    LLM generates 3 queries:
    factual · comparative · critical
          │
    ┌─────┼──────┐
    ▼     ▼      ▼
[Google [News  [Reddit
 News]  Orgs]   Node]
  RSS    RSS   pgvector
    └─────┼──────┘
          ▼
  [ Merge & Rerank ]
  dedupe → embed → cosine + recency → top 10
          │
          ▼
  [ Conflict Detector ]
  LLM: user vs articles · source vs source · framing
          │
     has_conflict?
     ┌────┴────┐
    YES        NO
     ▼          ▼
[ Deep Dive ] [ Verdict ]
  new queries      │
  re-fetch         ▼
  loop ≤2×       [ END ]
  back to conflict ↑
```

**State is a typed `TypedDict` (`LensState`)** shared across all nodes. Each node reads what it needs and writes only its own keys. This makes the pipeline easy to test node-by-node.

---

## ✨ Features

- **Live news aggregation** from Google News RSS, The Hindu, Indian Express, ANI News, BBC
- **Semantic Reddit retrieval** — dynamically finds relevant subreddits using vector similarity
- **LLM conflict detection** — catches ignored claims, contradictions, and framing bias
- **Auto deep-dive loop** — triggered on conflict, runs targeted follow-up queries (max 2 iterations)
- **Structured verdict** with 6 labels: `CONSENSUS`, `PARTIAL_CONFLICT`, `FACTUAL_CONFLICT`, `ECHO_CLUSTER`, `FRAMING_DIVERGENCE`, `INSUFFICIENT_DATA`
- **Western vs Indian framing analysis** in every verdict
- **Multi-modal input** — plain text, PDF upload, image/screenshot (OCR)
- **Real-time SSE streaming** — frontend gets progress updates as each node completes
- **Redis caching** — 24-hour TTL on all RSS feeds

---

## 🛠️ Tech Stack

| Layer | Technology | Why I chose it |
|---|---|---|
| Backend framework | FastAPI | Async-native, SSE support, clean routing |
| Pipeline orchestration | LangGraph | State machine with conditional looping |
| LLM | Groq (LLaMA 3.3 70B) | Fast inference, free tier, structured output |
| Embeddings | FastEmbed (all-MiniLM-L6-v2) | Runs locally, no API cost, fast |
| Vector DB | PostgreSQL + pgvector | Already using Postgres, avoids adding a separate vector store |
| Cache | Redis | Simple TTL caching for RSS feeds |
| Frontend | SvelteKit + Tailwind + shadcn-svelte | Lightweight, fast to build, SSE support built in |
| RSS parsing | feedparser + httpx | Reliable, handles malformed feeds gracefully |
| OCR | Tesseract + OpenCV | Open source, good accuracy with preprocessing |
| PDF extraction | PyMuPDF | Fast, handles OCR fallback for scanned PDFs |

---

## 📡 API

### `POST /verify/stream`

Single endpoint, streams results via SSE.

**JSON input:**
```json
{
  "raw_input": "Did the government suppress election results?",
  "input_type": "text"
}
```

**Multipart input (PDF or image):**
```
file: <uploaded file>
input_type: "pdf" | "image"
```

**SSE events emitted:**

| Event | Payload |
|---|---|
| `progress` | `{ "node": "google_news", "message": "Fetched 42 articles" }` |
| `final` | `{ verdict_label, verdict_explanation, framing_notes, top_articles }` |
| `done` | `{ "ok": true }` |
| `error` | `{ "error": "..." }` |

---

## 🚀 Running Locally

### Prerequisites

- Python 3.11+ with [`uv`](https://github.com/astral-sh/uv)
- Node.js 18+
- Docker & Docker Compose
- [Groq API key](https://console.groq.com/) (free)

### 1. Clone

```bash
git clone https://github.com/your-username/lens.git
cd lens
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in your values
```

**.env.example:**
```env
GROQ_API_KEY=your_groq_api_key_here
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/lens_db
REDIS_URL=redis://localhost:6379
```

### 3. Start infrastructure

```bash
docker-compose up -d
```

### 4. Run migrations

```bash
psql $POSTGRES_URL -f migrations/00001_add_reddit_subs.sql
psql $POSTGRES_URL -f migrations/00002_make_subname_unique.sql
psql $POSTGRES_URL -f migrations/00003_add_pgvector_ext.sql
psql $POSTGRES_URL -f migrations/00004_add_embedding_to_subreddits.sql
```

### 5. Install backend & seed data

```bash
uv sync

# One-time: seed subreddits and generate embeddings
python scripts/seed_reddit_subs.py
python scripts/embed_subreddits.py
```

### 6. Start backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 📂 Project Structure

```
lens/
├── api/
│   └── sse.py              # SSE endpoint, request routing, file handling
├── config/
│   └── logging_config.py   # Uvicorn-style colourized logging
├── db/
│   ├── postgres.py         # asyncpg connection pool
│   ├── redis.py            # Redis client
│   └── queries/
│       └── subreddits.py   # pgvector similarity query
├── frontend/               # SvelteKit app
├── llm/
│   ├── client.py           # Groq LLM client factory
│   ├── prompts/            # System prompts for each LLM node
│   └── schemas/            # Pydantic structured output models
├── migrations/             # SQL schema migrations
├── nodes/
│   ├── state.py            # LensState TypedDict + initial state
│   ├── graph.py            # LangGraph pipeline assembly
│   ├── query_node.py       # Query generation
│   ├── google_news_node.py # Google News RSS fetch
│   ├── news_orgs_node.py   # The Hindu / IE / ANI / BBC fetch
│   ├── reddit_node.py      # Reddit RSS + subreddit discovery
│   ├── merge_rerank.py     # Deduplication + hybrid ranking
│   ├── conflict_detector.py# LLM conflict detection
│   ├── deep_dive_node.py   # Targeted re-retrieval on conflict
│   └── verdict_node.py     # Final verdict synthesis
├── scripts/
│   ├── seed_reddit_subs.py # Bulk-insert popular subreddits
│   └── embed_subreddits.py # Backfill pgvector embeddings
├── tools/
│   ├── rss_fetcher.py      # Async RSS fetch + caching
│   ├── embedder.py         # FastEmbed wrapper
│   ├── cache.py            # Redis get/set helpers
│   ├── ocr.py              # OpenCV + Tesseract OCR
│   └── pdf.py              # PyMuPDF extraction
└── main.py                 # FastAPI app + lifespan + CORS
```

---

## 🔮 What I'd Improve With More Time

- **Full article content fetching** — currently using RSS descriptions only; fetching and summarizing full article bodies would significantly improve conflict detection accuracy
- **Source credibility scoring** — weight verdicts by outlet reliability, not just recency and semantic similarity
- **Caching at the verdict level** — hash the input and cache full pipeline outputs for identical or near-identical queries
- **User feedback loop** — let users flag incorrect verdicts to fine-tune prompt behavior over time

---

## 📜 License

MIT
