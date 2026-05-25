# 🔍 Lens — AI-Powered News Verification & Conflict Detection Engine

> **Hackathon:** National Level Online Hackathon 2027 — Organized by Steps AI  
> **Problem Statement:** PS3 — Open Track: AI Agents for Real-World Problems  
> **Team:** Shivang Srivastava  

---

## 📌 Project Description

We live in an era of information overload where the same event gets reported with different facts, different framing, or sometimes gets completely ignored by certain outlets. A reader searching "Is the Indian government hiding unemployment data?" cannot easily tell whether this claim is supported, denied, or just absent from mainstream coverage.

**Lens** is an AI-powered agentic verification system that takes any claim, question, or allegation — as plain text, a PDF, or an image screenshot — and maps what the surrounding media landscape is saying about it.

> ⚠️ **Important:** Lens does not determine ground truth. It surfaces what sources are reporting, where they agree, where they conflict, and how they frame the story. The verdict reflects the state of available coverage — not independent fact verification.

It retrieves live news coverage from multiple source types (Google News, mainstream Indian and international media RSS feeds, semantically relevant Reddit communities), detects narrative conflicts using an LLM, runs targeted deep-dive re-retrieval when conflicts are found, and synthesizes a final verdict — all streamed to the frontend in real time via SSE.

---

## 🎬 Demo Video

📽️ [Watch Demo](#)

---

## ✨ Features

- **Live news aggregation** from Google News RSS (3 locales × 2 variants per query), The Hindu, Indian Express, ANI News, and BBC
- **Semantic Reddit retrieval** — dynamically discovers relevant subreddits at runtime using pgvector similarity search against 5,000+ indexed communities
- **Six-angle query generation** — each user input is expanded into 6 search queries covering factual, comparative, critical, causal, impact, and historical angles
- **LLM conflict detection** — catches three distinct failure modes: user's claim being ignored/denied by articles, direct inter-source factual contradictions, and framing divergence
- **Auto deep-dive loop** — triggered when conflict is detected, generates 2–3 targeted follow-up queries and re-fetches; loops up to 2 times
- **Structured verdict** with 6 labels: `CONSENSUS`, `PARTIAL_CONFLICT`, `FACTUAL_CONFLICT`, `ECHO_CLUSTER`, `FRAMING_DIVERGENCE`, `INSUFFICIENT_DATA`
- **Framing analysis** — every verdict includes a separate `framing_notes` field analyzing narrative differences across source types
- **Multi-modal input** — plain text, PDF upload (with OCR fallback for scanned PDFs), and image/screenshot (OpenCV + Tesseract)
- **Real-time SSE streaming** — frontend receives progress updates as each pipeline node completes
- **Redis caching** — 1-hour TTL on all RSS feed fetches; subreddit similarity results are also cached

---

## 🛠️ Tech Stack

<details>
    <summary>View full tech stack diagram</summary>


| Layer | Technology | Why |
|---|---|---|
| Backend framework | FastAPI | Async-native, SSE support, clean routing |
| Pipeline orchestration | LangGraph | State machine with conditional looping |
| LLM | Groq (LLaMA 3.3 70B + fallbacks) | Fast inference, free tier, structured output |
| Embeddings | FastEmbed (all-MiniLM-L6-v2) | Runs locally, no API cost, fast |
| Vector DB | PostgreSQL + pgvector | Avoids a separate vector store; already using Postgres |
| Cache | Redis | TTL-based caching for RSS feeds and subreddit lookups |
| Frontend | SvelteKit + Tailwind + shadcn-svelte | Lightweight, fast to build, SSE support built in |
| RSS parsing | feedparser + httpx | Reliable, handles malformed feeds gracefully |
| OCR | Tesseract + OpenCV | Open source, good accuracy with preprocessing |
| PDF extraction | PyMuPDF | Fast, handles OCR fallback for scanned PDFs |


</details>
---

## 🏗️ System Architecture

<details>
<summary>View architecture diagram & state design</summary>

```
User Input (text / PDF / image)
          │
          ▼
    [ Query Node ]
    LLM generates 6 queries across:
    factual · comparative · critical
    causal · impact · historical
          │
    ┌─────┼──────┐
    ▼     ▼      ▼
[Google [News  [Reddit
 News]  Orgs]   Node]
  RSS    RSS   pgvector
  (3    (The   subreddit
locales) Hindu  discovery
         IE/ANI
         BBC)
    └─────┼──────┘
          ▼
  [ Merge & Rerank ]
  dedupe → embed → 0.5×cosine + 0.5×recency → top 20
          │
          ▼
  [ Conflict Detector ]
  LLM checks: user vs articles · source vs source · framing
          │
     has_conflict AND deep_dive_count < 2?
     ┌────┴────┐
    YES        NO
     ▼          ▼
[ Deep Dive ]  [ Verdict ]
  LLM generates    │
  2–3 targeted     ▼
  queries        [ END ]
  re-fetch
  loop back ↑
  (max 2×)
```

**State** is a typed `TypedDict` (`LensState`) shared across all LangGraph nodes. Each node reads only what it needs and writes only its own keys — making every node independently testable.

</details>

---

## 🧠 Key Technical Decisions

<details>
<summary>View all 7 architectural decisions</summary>

**1. LangGraph over a simple chain**
I needed a pipeline where conflict detection could loop back and trigger more retrieval. A linear LangChain chain can't do this. LangGraph lets me model this as a proper state machine with conditional edges, so the deep-dive loop (re-fetch when conflict is found, max 2 iterations) is a first-class architectural feature, not a hack.

**2. Fan-out parallelism for article fetching**
Google News, news org RSS feeds, and Reddit are all fetched concurrently using `asyncio.gather`. This cuts total fetch time to the slowest source rather than the sum of all sources.

**3. Semantic subreddit discovery with pgvector**
Instead of hardcoding subreddit lists, I seeded 5,000+ popular subreddits into PostgreSQL with pgvector embeddings. At runtime, query embeddings are compared against this table to find the most topically relevant communities. Reddit retrieval is dynamic and generalizes to any topic.

**4. Hybrid ranking: cosine similarity + recency decay**
In `merge_rerank.py`, articles are scored as `0.5 × cosine_similarity + 0.5 × recency_score`. The recency score uses exponential decay with a 48-hour half-life (`e^(-age_hours/48)`), preventing old but semantically similar articles from outranking genuinely fresh coverage.

**5. Three-type conflict detection**
The conflict detector is explicitly designed to catch three distinct failure modes:
- **User-article conflict**: the user's claim is ignored or denied by articles (silence = conflict)
- **Inter-source factual conflict**: two sources contradict each other on facts
- **Framing divergence**: same facts, but different source types tell different stories

**6. SSE over WebSockets**
Server-Sent Events are simpler, stateless, and sufficient for a unidirectional server → client stream.

**7. Redis caching on RSS feeds**
RSS feeds don't change every second. A 1-hour TTL means repeated queries on similar topics don't re-hammer the same endpoints, and warm-cache response times drop significantly.

</details>

---

## 📡 API

### `POST /verify/stream`

Single endpoint. Accepts JSON or multipart form. Streams results via SSE.

<details>
<summary>View request formats, SSE events, and verdict labels</summary>

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

**Verdict labels:**

| Label | Meaning |
|---|---|
| `CONSENSUS` | 3+ independent sources report the same core facts |
| `PARTIAL_CONFLICT` | Facts agreed, but cause/significance disputed |
| `FACTUAL_CONFLICT` | Mutually exclusive factual claims across sources |
| `FRAMING_DIVERGENCE` | Same facts, meaningfully different narratives |
| `ECHO_CLUSTER` | Apparent consensus is amplification of a single originating source |
| `INSUFFICIENT_DATA` | Fewer than two independent substantive sources found |

> ⚠️ All labels reflect what the retrieved coverage says — not independently verified ground truth.

</details>

---

## 🚀 Running Locally

### Prerequisites
- Docker & Docker Compose
- [Groq API key](https://console.groq.com/) (free)

### 1. Clone
```bash
git clone https://github.com/shv-ng/lens.git
cd lens
```

### 2. Configure environment
```bash
cp example.env .env
```
Open `.env` and set your `GROQ_API_KEY`. Everything else works as-is with the defaults.

### 3. Start
```bash
docker compose up -d
```

Open [http://localhost](http://localhost).

### 4. Seed data (one-time only)

Run these in order before first use:

```bash
docker compose --profile scripts run --rm seed
docker compose --profile scripts run --rm embed
```

The `seed` script fetches 5,000+ popular subreddits from Reddit and bulk-inserts them into Postgres. The `embed` script backfills pgvector embeddings for each subreddit description in batches of 256 using the local FastEmbed model. Both are safe to re-run but only need to run once.

Python, Node, and all database setup are handled by Docker — no local installs required.

---

## 🔑 Environment Variables

Copy `example.env` to `.env` and fill in the values below.

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Your Groq API key — get one free at [console.groq.com](https://console.groq.com) |
| `POSTGRES_URL` | ✅ Yes | PostgreSQL connection string. Docker default: `postgresql://postgres:postgres@postgres:5432/postgres` |
| `REDIS_URL` | ✅ Yes | Redis connection string. Docker default: `redis://redis:6379` |

When running via `docker compose`, `POSTGRES_URL` and `REDIS_URL` are pre-configured. You only need to set `GROQ_API_KEY`.

---

## 📂 Project Structure

<details>
<summary>View full file tree with annotations</summary>

```
lens/
├── api/
│   └── sse.py              # SSE endpoint, request routing, file handling
├── config/
│   └── logging_config.py   # Rotating file + console logging setup
├── db/
│   ├── postgres.py         # asyncpg connection pool
│   ├── redis.py            # Redis async + sync clients
│   └── queries/
│       └── subreddits.py   # pgvector cosine similarity query
├── frontend/               # SvelteKit app
├── llm/
│   ├── client.py           # Groq LLM client with fallback chain
│   ├── prompts/            # System prompts: query, conflict, deep_dive, verdict
│   └── schemas/            # Pydantic structured output models
├── migrations/             # SQL schema (pgvector extension, subreddits table)
├── nodes/
│   ├── state.py            # LensState TypedDict + get_initial_state()
│   ├── graph.py            # LangGraph pipeline assembly + conflict router
│   ├── query_node.py       # 6-angle query generation
│   ├── google_news_node.py # Google News RSS (3 locales × 2 variants per query)
│   ├── news_orgs_node.py   # The Hindu / Indian Express / ANI / BBC RSS
│   ├── reddit_node.py      # Reddit RSS + pgvector subreddit discovery
│   ├── merge_rerank.py     # Deduplication + hybrid cosine/recency ranking
│   ├── conflict_detector.py# LLM conflict detection (3 types)
│   ├── deep_dive_node.py   # Targeted re-retrieval on conflict (max 2 loops)
│   └── verdict_node.py     # Final structured verdict synthesis
├── scripts/
│   ├── seed_reddit_subs.py # Bulk-insert 5,000+ subreddits into Postgres
│   └── embed_subreddits.py # Backfill pgvector embeddings in batches of 256
├── tools/
│   ├── rss_fetcher.py      # Async RSS fetch + Redis caching + retry decorator
│   ├── embedder.py         # FastEmbed wrapper with caching
│   ├── ocr.py              # OpenCV preprocessing + Tesseract extraction
│   └── pdf.py              # PyMuPDF text extraction with OCR fallback
├── core/decorators/
│   ├── cache.py            # @cached decorator (Redis, async + sync)
│   ├── logger.py           # @logit decorator (async gen / coroutine / sync)
│   └── retry.py            # @retry decorator with configurable backoff
├── example.env             # Environment variable template
├── docker-compose.yaml     # Full stack: backend, frontend, Postgres, Redis
└── main.py                 # FastAPI app + lifespan + CORS
```

</details>

---

## 🔮 What I'd Improve With More Time

- **Full article content fetching** — currently using RSS descriptions only; fetching and summarizing full article bodies would significantly improve conflict detection accuracy
- **Source credibility scoring** — weight verdicts by outlet reliability, not just recency and semantic similarity
- **Verdict-level caching** — hash the input and cache full pipeline outputs for identical or near-identical queries
- **User feedback loop** — let users flag incorrect verdicts to improve prompt behavior over time

---

## 📜 License

[MIT](LICENSE)
