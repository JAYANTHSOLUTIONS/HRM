-- Track failed OTP attempts so a reset code cannot be guessed indefinitely.
ALTER TABLE password_reset_tokens
    ADD COLUMN attempts SMALLINT UNSIGNED NOT NULL DEFAULT 0 AFTER used_at;