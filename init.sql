CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS subreddits (
    subreddit text PRIMARY KEY,
    description text,
    embedding vector(384)
);
