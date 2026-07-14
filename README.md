# Shopify-Crawler

Crawl **every product from any Shopify store** — no API key, no auth. Packaged as
a [Claude Code / Claude skill](SKILL.md) with a standalone, stdlib-only Python
crawler you can also run by hand.

## Why it works

Nearly every Shopify store auto-exposes its catalog through public endpoints:

| Endpoint | Returns |
|---|---|
| `/products.json?limit=250&page=N` | All products, 250/page (primary) |
| `/collections/<handle>/products.json` | Products in one collection |
| `/products/<handle>.json` | A single product |
| `/sitemap.xml` → `sitemap_products_*.xml` | Every product URL (fallback) |

## Usage

Runs on the system `python3` — nothing to install:

```bash
# Whole catalog → allbirds.com.json
python3 scripts/crawl.py allbirds.com

# Add a spreadsheet-friendly CSV (one row per variant)
python3 scripts/crawl.py allbirds.com --csv

# One collection, to a named file
python3 scripts/crawl.py allbirds.com --collection mens --out mens.json --csv

# Cap count and slow down on a large store
python3 scripts/crawl.py somestore.com --max 500 --delay 1.0
```

| Flag | Meaning |
|---|---|
| `--collection <handle>` | Only crawl one collection |
| `--out <path>` | JSON output path (default `<host>.json`) |
| `--csv` | Also write `<name>.csv`, one row per variant |
| `--max <N>` | Stop after N products |
| `--delay <sec>` | Seconds between requests (default `0.5`) |
| `--no-fallback` | Don't fall back to the sitemap if `products.json` fails |

## Install as a skill

Once you install it, you no longer need to remember the CLI — just ask Claude in
plain language and it runs the crawler for you.

**1. Copy the folder into your skills directory (one time):**

```bash
cp -r /Users/ethanmiller/Documents/Companies/Lab3/Shopify-Crawler \
  ~/.claude/skills/shopify-crawler
```

(If you cloned this repo elsewhere, point `cp -r` at your local copy instead.)

**2. Talk to Claude — it invokes the skill automatically:**

> "Crawl all products from gymshark.com and give me a CSV"
>
> "Grab the men's collection from allbirds.com as JSON"
>
> "Export this Shopify shop's catalog: somestore.com"

Claude recognizes the intent, runs `scripts/crawl.py` with the right flags, and
hands you the resulting JSON/CSV files. Verify it's loaded by checking that
`shopify-crawler` appears in your skills list.

## When a store returns nothing

The site is likely **not Shopify**, is password-protected, or blocks bots at the
CDN. Fall back to a real browser session or the official Storefront API.

## Etiquette

Product listings are public data; crawling for research or price comparison is
generally fine. Keep a sane `--delay` so you don't overload a store, and don't
use this to disrupt a site or republish content in bad faith.

## License

MIT
