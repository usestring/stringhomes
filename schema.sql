CREATE TABLE IF NOT EXISTS corrections (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  listing_id TEXT NOT NULL,
  url TEXT,
  field TEXT NOT NULL,
  value TEXT,
  note TEXT,
  client_at TEXT,
  received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  sender TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new'
);
CREATE INDEX IF NOT EXISTS corrections_sender_time ON corrections (sender, received_at);
CREATE INDEX IF NOT EXISTS corrections_status ON corrections (status);
