-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS subreddits (
    subreddit text,
    description text
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS subreddits;
-- +goose StatementEnd
