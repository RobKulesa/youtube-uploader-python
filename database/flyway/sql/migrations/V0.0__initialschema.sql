CREATE SCHEMA IF NOT EXISTS volleyball_uploader;

ALTER DATABASE postgres SET timezone TO 'America/New_York';


CREATE TABLE IF NOT EXISTS volleyball_uploader.uploads (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    privacy TEXT NOT NULL,
    path TEXT NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
