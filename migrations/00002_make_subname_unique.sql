-- +goose Up
-- +goose StatementBegin
ALTER TABLE subreddits
ADD CONSTRAINT subreddits_pkey
PRIMARY KEY (subreddit);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

ALTER TABLE subreddits
DROP CONSTRAINT subreddits_pkey;
-- +goose StatementEnd
