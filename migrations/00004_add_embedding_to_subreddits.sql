-- +goose Up
-- +goose StatementBegin
ALTER TABLE subreddits 
ADD COLUMN IF NOT EXISTS embedding vector(384);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
ALTER TABLE subreddits 
DROP COLUMN IF EXISTS embedding;
-- +goose StatementEnd
