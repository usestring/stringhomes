// POST /api/corrections: one correction request per call, stored in D1 for the next daily refresh.
const FIELDS = new Set(["price", "beds", "where", "dates", "type", "gone", "scam", "other"]);
const PER_HOUR = 20;
const MAX = { id: 200, url: 1000, value: 200, note: 2000, at: 40 };

const reply = (status, body) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

async function senderKey(request, salt) {
  // Store a salted hash, never the address itself.
  const ip = request.headers.get("cf-connecting-ip") || "unknown";
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(salt + ip));
  return [...new Uint8Array(digest).slice(0, 12)].map(b => b.toString(16).padStart(2, "0")).join("");
}

const str = (v, n) => (v == null || v === "" ? null : typeof v === "string" && v.length <= n ? v.trim() : undefined);

export async function onRequestPost({ request, env }) {
  if (request.headers.get("content-length") > 8192) return reply(413, { error: "request too large" });
  let req;
  try { req = await request.json(); } catch { return reply(400, { error: "body must be JSON" }); }
  const row = {
    id: str(req.id, MAX.id), url: str(req.url, MAX.url), field: req.field,
    value: str(req.value, MAX.value), note: str(req.note, MAX.note), at: str(req.at, MAX.at),
  };
  if (!row.id || Object.values(row).includes(undefined)) return reply(400, { error: "invalid or oversized field" });
  if (!FIELDS.has(row.field)) return reply(400, { error: "unknown correction type" });
  if (!row.value && !row.note && row.field !== "gone" && row.field !== "scam") return reply(400, { error: "add the correct value or a note" });
  if (row.url && !/^https?:\/\//.test(row.url)) return reply(400, { error: "invalid url" });

  const sender = await senderKey(request, env.SENDER_SALT || "");
  const { n } = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM corrections WHERE sender = ? AND received_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 hour')"
  ).bind(sender).first();
  if (n >= PER_HOUR) return reply(429, { error: "too many corrections from this connection; try again in an hour" });

  await env.DB.prepare("INSERT INTO corrections (listing_id, url, field, value, note, client_at, sender) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .bind(row.id, row.url, row.field, row.value, row.note, row.at, sender).run();
  return reply(201, { ok: true });
}

export const onRequest = () => reply(405, { error: "POST only" });
