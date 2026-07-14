#!/usr/bin/env python3
"""Crawl every product from any Shopify store.

Primary strategy: the public /products.json endpoint that almost every Shopify
store exposes (no auth, no API key). Falls back to the XML sitemap when a store
has disabled products.json. Outputs JSON always, and CSV (one row per variant)
on request.

Stdlib only — runs with the system `python3`, nothing to install.

Examples:
    python3 crawl.py https://allbirds.com
    python3 crawl.py allbirds.com --csv
    python3 crawl.py allbirds.com --collection mens --out mens.json --csv
    python3 crawl.py somestore.com --max 500 --delay 1.0
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
PAGE_SIZE = 250  # Shopify's hard cap for products.json


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def normalize_base(raw: str) -> str:
    """Turn 'allbirds.com/' or 'http://allbirds.com' into 'https://allbirds.com'."""
    raw = raw.strip().rstrip("/")
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    # Drop any path — we only want the origin.
    scheme, _, rest = raw.partition("://")
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}"


def fetch(url: str, retries: int = 3, backoff: float = 2.0) -> bytes:
    """GET a URL with a browser UA, retrying on transient errors."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return data
        except urllib.error.HTTPError as e:
            # 404/403 on the very first products.json page usually means the
            # endpoint is disabled — no point retrying those.
            if e.code in (403, 404):
                raise
            last_err = e
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
        if attempt < retries:
            wait = backoff * attempt
            log(f"  retry {attempt}/{retries} in {wait:.0f}s ({last_err})")
            time.sleep(wait)
    raise last_err or RuntimeError(f"failed to fetch {url}")


def products_json_url(base: str, collection: str | None, page: int) -> str:
    if collection:
        path = f"/collections/{collection}/products.json"
    else:
        path = "/products.json"
    return f"{base}{path}?limit={PAGE_SIZE}&page={page}"


def crawl_products_json(
    base: str, collection: str | None, delay: float, cap: int | None
) -> list[dict[str, Any]]:
    """Page through /products.json until an empty page or the cap is hit."""
    products: list[dict[str, Any]] = []
    page = 1
    while True:
        url = products_json_url(base, collection, page)
        raw = fetch(url)
        batch = json.loads(raw).get("products", [])
        if not batch:
            break
        products.extend(batch)
        log(f"  page {page}: +{len(batch)} (total {len(products)})")
        if cap and len(products) >= cap:
            products = products[:cap]
            log(f"  reached cap of {cap}, stopping")
            break
        page += 1
        time.sleep(delay)
    return products


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _locs(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    return [
        el.text.strip()
        for el in root.iter()
        if _strip_ns(el.tag) == "loc" and el.text
    ]


def crawl_sitemap(
    base: str, delay: float, cap: int | None
) -> list[dict[str, Any]]:
    """Fallback: read the sitemap, then fetch each product's own .json."""
    log("  products.json unavailable — falling back to sitemap")
    index = fetch(f"{base}/sitemap.xml")
    child_maps = [u for u in _locs(index) if "sitemap_products" in u]
    if not child_maps:
        # Some stores put product URLs directly in sitemap.xml.
        child_maps = [f"{base}/sitemap.xml"]

    product_urls: list[str] = []
    for sm in child_maps:
        try:
            product_urls.extend(
                u for u in _locs(fetch(sm)) if "/products/" in u
            )
        except Exception as e:  # noqa: BLE001
            log(f"  skip sitemap {sm}: {e}")
        time.sleep(delay)

    # De-dupe while preserving order.
    seen: set[str] = set()
    product_urls = [u for u in product_urls if not (u in seen or seen.add(u))]
    log(f"  sitemap lists {len(product_urls)} products")

    products: list[dict[str, Any]] = []
    for i, purl in enumerate(product_urls, 1):
        if cap and len(products) >= cap:
            break
        try:
            data = json.loads(fetch(purl + ".json"))
            if "product" in data:
                products.append(data["product"])
        except Exception as e:  # noqa: BLE001
            log(f"  skip {purl}: {e}")
        if i % 25 == 0:
            log(f"  fetched {i}/{len(product_urls)} (kept {len(products)})")
        time.sleep(delay)
    return products


def write_csv(products: list[dict[str, Any]], path: str) -> int:
    """One row per variant — the shape most useful for spreadsheets."""
    cols = [
        "product_id", "title", "handle", "vendor", "product_type", "tags",
        "published_at", "product_url_path", "variant_id", "variant_title",
        "sku", "price", "compare_at_price", "available", "image",
    ]
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in products:
            tags = p.get("tags")
            tags = ", ".join(tags) if isinstance(tags, list) else (tags or "")
            image = ""
            if p.get("images"):
                image = p["images"][0].get("src", "")
            variants = p.get("variants") or [{}]
            for v in variants:
                w.writerow({
                    "product_id": p.get("id", ""),
                    "title": p.get("title", ""),
                    "handle": p.get("handle", ""),
                    "vendor": p.get("vendor", ""),
                    "product_type": p.get("product_type", ""),
                    "tags": tags,
                    "published_at": p.get("published_at", ""),
                    "product_url_path": f"/products/{p.get('handle', '')}",
                    "variant_id": v.get("id", ""),
                    "variant_title": v.get("title", ""),
                    "sku": v.get("sku", ""),
                    "price": v.get("price", ""),
                    "compare_at_price": v.get("compare_at_price", ""),
                    "available": v.get("available", ""),
                    "image": image,
                })
                rows += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Crawl all products from a Shopify store."
    )
    ap.add_argument("store", help="Store domain or URL, e.g. allbirds.com")
    ap.add_argument("--collection", help="Only crawl this collection handle")
    ap.add_argument("--out", help="JSON output path (default: <host>.json)")
    ap.add_argument("--csv", action="store_true",
                    help="Also write a CSV (one row per variant)")
    ap.add_argument("--max", type=int, help="Stop after N products")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="Seconds between requests (default 0.5)")
    ap.add_argument("--no-fallback", action="store_true",
                    help="Do not fall back to the sitemap if products.json fails")
    args = ap.parse_args()

    base = normalize_base(args.store)
    host = base.split("://", 1)[1]
    out = args.out or f"{host.replace(':', '_')}.json"

    log(f"Crawling {base}"
        + (f" / collection '{args.collection}'" if args.collection else ""))

    try:
        products = crawl_products_json(base, args.collection, args.delay, args.max)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404) and not args.collection and not args.no_fallback:
            products = crawl_sitemap(base, args.delay, args.max)
        else:
            log(f"ERROR: {e} on {base}")
            return 1

    if not products:
        log("No products found. The store may be empty, protected, or not Shopify.")
        return 1

    with open(out, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    log(f"\n✓ {len(products)} products → {out}")

    if args.csv:
        csv_path = out.rsplit(".", 1)[0] + ".csv"
        n = write_csv(products, csv_path)
        log(f"✓ {n} variant rows → {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
