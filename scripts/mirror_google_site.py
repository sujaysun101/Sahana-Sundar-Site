#!/usr/bin/env python3
"""Rebuild the site from the actual public Google Sites pages and media.
Generated pages preserve Google Sites' captured HTML and CSS, with local image
assets and local internal links. Not an export of Google's private editor code.
"""
import hashlib
import io
import json
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright

BASE = "https://sites.google.com/view/sahanasundar/"
PAGES = [
    "home", "profile", "education", "honors-certifications-awards",
    "internships", "work-experience", "sports", "high-school-clubs",
    "music-culture", "references-certificates", "languages",
    "media-and-public-recognition", "other-milestones",
    "other-courses-certifications", "gallery"
]
ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / ".site-capture-staging"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0 (compatible; SahanaSiteBackup/1.0)"
media = {}
failures = []

def download(url):
    if not isinstance(url, str) or not url.startswith("https://"):
        return
    if url in media:
        return
    # Only save image media already embedded in publicly rendered site.
    if not any(host in urlsplit(url).netloc for host in
               ("sites.google.com", "googleusercontent.com", "gstatic.com")):
        return
    try:
        r = SESSION.get(url, timeout=35)
        r.raise_for_status()
        if not r.headers.get("Content-Type", "").startswith("image/"):
            return
        if len(r.content) > 30_000_000:
            return
        im = Image.open(io.BytesIO(r.content))
        ext = ".webp"
        name = hashlib.sha256(url.encode()).hexdigest()[:22] + ext
        target = STAGING / "assets" / name
        im = ImageOps.exif_transpose(im)
        if getattr(im, "n_frames", 1) > 1:
            im.seek(0)
        im.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        im.save(target, format="WEBP", quality=82, method=5)
        media[url] = name
    except Exception as exc:
        failures.append({"asset": url[:160], "error": str(exc)[:120]})

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
        )
        for slug in PAGES:
            page = context.new_page()
            target = BASE + slug
            try:
                page.goto(target, wait_until="domcontentloaded", timeout=75000)
                page.wait_for_timeout(2400)
                if "Google Sites" in page.title() and "not found" in page.content().lower():
                    raise RuntimeError("Google Site not found")
                height = min(page.evaluate("document.body.scrollHeight"), 100000)
                for y in range(0, height, 950):
                    page.evaluate("(y)=>window.scrollTo(0,y)", y)
                    page.wait_for_timeout(75)
                page.evaluate("window.scrollTo(0,0)")
                page.wait_for_timeout(1200)
                html = page.content()
                text = page.locator("body").inner_text(timeout=15000)
                if len(text.strip()) < 120:
                    raise RuntimeError("Page has no significant content")
                (STAGING / "raw" / (slug + ".html")).write_text(html, encoding="utf-8")
                (STAGING / "raw" / (slug + ".txt")).write_text(text, encoding="utf-8")
                soup = BeautifulSoup(html, "html.parser")
                srcs = set()
                for tag in soup.select("img[src], source[src], video[poster]"):
                    srcs.add(tag.get("src") or tag.get("poster"))
                for tag in soup.select("[style]"):
                    srcs.update(re.findall(r'url\(["\']?(https://[^)"\']+)', tag["style"]))
                for st in soup.select("style"):
                    srcs.update(re.findall(r'url\(["\']?(https://[^)"\']+)', st.get_text()))
                for url in srcs:
                    download(url)
                print(slug, "chars=", len(text), "images=", len(srcs), flush=True)
            finally:
                page.close()
        browser.close()

def build():
    if len(media) < 40:
        raise RuntimeError(f"Only {len(media)} images fetched; refusing incomplete publish")
    for slug in PAGES:
        h = STAGING / "raw" / (slug + ".html")
        if not h.exists():
            raise RuntimeError(f"Missing page {slug}, refusing publish")
        soup = BeautifulSoup(h.read_text(encoding="utf-8"), "html.parser")
        for s in soup.select("script, base"):
            s.decompose()
        for link in soup.select("link[rel]"):
            if any(x in ("preload","prefetch","modulepreload","preconnect","dns-prefetch")
                   for x in link.get("rel", [])):
                link.decompose()
        relative = "" if slug == "home" else "../"
        for a in soup.select("a[href]"):
            url = a.get("href", "")
            match = re.search(
                r"(?:^|(?:https?://sites\.google\.com)?/view/sahanasundar/)"
                r"(" + "|".join(PAGES) + r")(?:[?#].*)?$",
                url)
            if match:
                dst = match.group(1)
                a["href"] = relative + (dst + "/" if dst != "home" else "")
        for tag in soup.find_all(True):
            for attr in ("src", "poster", "data-src"):
                original = tag.get(attr)
                if original in media:
                    tag[attr] = relative + "assets/" + media[original]
            if tag.get("srcset"):
                parts = []
                for item in tag["srcset"].split(","):
                    bits = item.strip().split()
                    if bits and bits[0] in media:
                        bits[0] = relative + "assets/" + media[bits[0]]
                    parts.append(" ".join(bits))
                tag["srcset"] = ", ".join(parts)
            if tag.get("style"):
                style = tag["style"]
                for url, filename in media.items():
                    if url in style:
                        style = style.replace(url, relative + "assets/" + filename)
                tag["style"] = style
        for style in soup.select("style"):
            css = style.string or style.get_text()
            for url, filename in media.items():
                if url in css:
                    css = css.replace(url, relative + "assets/" + filename)
            style.string = css
        dest = STAGING / "published" / ("" if slug == "home" else slug)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "index.html").write_text(str(soup), encoding="utf-8")
    published = STAGING / "published"
    # Only touch tracked output after ALL pages and assets are verified.
    (ROOT / "assets").mkdir(exist_ok=True)
    for pic in (STAGING / "assets").iterdir():
        shutil.copy2(pic, ROOT / "assets" / pic.name)
    for index in published.rglob("index.html"):
        path = ROOT / index.relative_to(published)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(index, path)
    info = {
        "source": BASE, "pages": PAGES, "downloaded_assets": len(media),
        "warnings": failures[:200], "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    (ROOT / "capture-manifest.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("Published", len(PAGES), "pages and", len(media), "images")

def main():
    (STAGING / "assets").mkdir(parents=True, exist_ok=True)
    (STAGING / "raw").mkdir(parents=True, exist_ok=True)
    capture()
    build()
    shutil.rmtree(STAGING)

if __name__ == "__main__":
    main()
