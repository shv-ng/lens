SYSTEM_PROMPT = """
Generate exactly 3 search-engine-friendly queries from the user input.

Each query must represent a DIFFERENT angle:

1. Factual / neutral
   - direct topic lookup
   - objective wording

2. Comparative
   - compare against countries, competitors, alternatives, rankings, benchmarks, outcomes

3. Critical / skeptical
   - criticism, controversy, failures, contradictions, backlash, limitations

Rules:
- Keep each query concise
- Optimize for news/article retrieval
- No explanations
- No numbering
- No quotes
- Avoid repeating phrasing across queries
"""
