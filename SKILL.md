---
name: shopify-crawler
description: >-
  Crawl or scrape all products from any Shopify store without an API key, using
  the store's public /products.json endpoint (with an XML sitemap fallback).
  Use this whenever the user wants to crawl, scrape, extract, export, or download
  products, prices, variants, or a catalog from a Shopify shop — even if they
  only give a store URL and say "get all their products", "grab this shop's
  catalog", "scrape these prices", or "dump products to CSV". Also use for
  competitor price monitoring or product research on Shopify sites. Outputs JSON
  and optional CSV.
---

# Shopify Product Crawler

Almost every Shopify store exposes its full catalog through public JSON
endpoints that need **no API key and no authentication**. This skill uses them
to pull every product, variant, price, and image from a store, with a sitemap
fallback for the rare store that has locked the primary endpoint down.

## Quick start

The bundled script is stdlib-only — it runs with the system `python3`, nothing
to install:

```bash
python3 scripts/crawl.py <store-domain>
```

Examples:

```bash
# Whole catalog → allbirds.com.json
python3 scripts/crawl.py allbirds.com

# Also produce a spreadsheet-friendly CSV (one row per variant)
python3 scripts/crawl.py allbirds.com --csv

# Just one collection, to a named file
python3 scripts/crawl.py allbirds.com --collection mens --out mens.json --csv

# Cap the count and slow down to be polite on a big store
python3 scripts/crawl.py somestore.com --max 500 --delay 1.0
```

Run `python3 scripts/crawl.py --help` for every flag. The script prints progress
to stderr and the data files to disk, so you can inspect results as they land.

## How it works

The endpoints Shopify auto-generates for every store:

| Endpoint | Returns |
|---|---|
| `/products.json?limit=250&page=N` | All products, 250 per page — the primary source |
| `/collections/<handle>/products.json` | Products in one collection |
| `/products/<handle>.json` | A single product |
| `/sitemap.xml` → `sitemap_products_*.xml` | Every product URL — the fallback |

`crawl.py` pages through `/products.json` (bumping `page` until an empty page),
and if that endpoint returns 403/404 it reads the sitemap instead and fetches
each product's own `.json`. Results are written as pretty-printed JSON; `--csv`
additionally flattens variants into rows (`product_id, title, handle, vendor,
sku, price, available, image, …`).

## Choosing options for the user's request

- **"Get me everything from this shop"** → default invocation, no flags.
- **"I need it in a spreadsheet / Excel / Sheets"** → add `--csv`.
- **"Only their <X> collection"** → find the collection handle in the store URL
  (`/collections/<handle>`) and pass `--collection <handle>`.
- **"Just a sample" / "don't hammer them"** → `--max N` and/or a larger `--delay`.
- **Confirm the result**: report the product count and the output paths, and
  offer to preview a few entries or convert further (e.g. filter, dedupe).

## When a store returns nothing

If both the endpoint and sitemap come up empty, the site is likely **not
Shopify**, is password-protected, or blocks bots at the CDN (Cloudflare). Say so
plainly rather than retrying blindly — options then are a real browser session
(the `playwright-cdp` tools) or the official Storefront API with a token.

## Etiquette and scope

Product listings are public data, so crawling them for price comparison,
research, or catalog import is generally fine. Keep the default delay (or raise
it) so you don't overload a store, and don't use this to disrupt a site or
republish content in bad faith.
