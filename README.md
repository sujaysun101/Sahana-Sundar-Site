# Sahana Sundar Site

A self-hostable static capture of the 15-page Google Sites portfolio at https://sites.google.com/view/sahanasundar/home .

## Full capture and rebuild

This repository contains a reproducible migration pipeline:

- `scripts/mirror_google_site.py` visits all 15 published pages, scrolls to load media, preserves the rendered Google Sites markup, downloads images, and rewrites internal links to local routes.
- `.github/workflows/mirror-google-site.yml` runs the capture in GitHub Actions, verifies page content and image availability, then commits the pages and local images to this repository.
- Each generated page is at `<slug>/index.html`; the homepage is `index.html`. Images are stored in `assets/`.

To run locally after the capture succeeds:

```sh
python -m http.server 8000
```

Navigate to http://localhost:8000/ and use the menu to move between real local pages.

## Limitations

This is a **static reconstruction of the published Google Site**, not an export of Google's private editor implementation. It faithfully preserves the scraped public page content, sections and media. Some embedded Google Drive document viewers, site search, carousels or JavaScript-driven components may need manual reimplementation; Google-hosted CSS and fonts may require internet access.

The site is distinct from `sujaysun101/Sahana-Sundar-Website`, which is not changed.

The destination GitHub repo is currently public, so review any documents, images and personal details before public deployment.
