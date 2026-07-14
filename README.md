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

Copy this folder into your skills directory (or a plugin marketplace), e.g.:

```bash
cp -r Shopify-Crawler ~/.claude/skills/shopify-crawler
```

Then Claude will invoke it automatically when you ask it to crawl, scrape, or
export products from a Shopify shop.

## When a store returns nothing

The site is likely **not Shopify**, is password-protected, or blocks bots at the
CDN. Fall back to a real browser session or the official Storefront API.

## Etiquette

Product listings are public data; crawling for research or price comparison is
generally fine. Keep a sane `--delay` so you don't overload a store, and don't
use this to disrupt a site or republish content in bad faith.

## License

MIT
