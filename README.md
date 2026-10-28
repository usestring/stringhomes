# stringhomes

Every NYC rental we could find, scored on price against fair value, with your own commute.
Live at <https://stringhomes.pages.dev>.

The site is one static page plus one Cloudflare Pages Function:

- `public/` holds the page. `index.html` and `transit.json` are built by the listings pipeline
  each day and uploaded by `deploy.sh`; they are not committed.
- `functions/api/corrections.js` takes correction requests from the page (`POST /api/corrections`)
  and stores them in D1. It keeps a salted hash of the sender's IP for rate limiting
  (20 per hour), never the address.
- `schema.sql` is the D1 schema.

Favorites and your commute anchor stay in your browser's localStorage.

## Run locally

```sh
wrangler d1 execute stringhomes --local --file schema.sql
wrangler pages dev public
```

`public/index.html` must exist first; copy one from a pipeline build.

## First deploy

```sh
wrangler d1 create stringhomes              # put the printed database_id in wrangler.toml
wrangler d1 execute stringhomes --remote --file schema.sql
wrangler pages project create stringhomes --production-branch main
openssl rand -hex 32 | wrangler pages secret put SENDER_SALT --project-name stringhomes
./deploy.sh <built site dir>
```

## Daily refresh

The pipeline gathers listings, rescores them, builds the page and runs `deploy.sh`.
`pull_corrections.sh` prints new correction requests for review and marks them seen.
