CREATE TABLE IF NOT EXISTS volleyball_uploader.playlists (
    id SERIAL PRIMARY KEY,
    playlist_id TEXT NOT NULL,
    title TEXT UNIQUE NOT NULL,
    description TEXT,
    privacy TEXT NOT NULL,
    create_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);