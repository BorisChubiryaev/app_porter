# Slotless: landing page

A static site with no dependencies: one page per language, in `dist/`.

```bash
python3 build.py
```

The build stops if a language lacks a text. To see the result:

```bash
python3 -m http.server -d dist 8000
```

## Going live

Everything is in `config.json`; run the build after changing it.

| Key | What it does |
|---|---|
| `base_url` | The site's address, for search engines (language links, sitemap). Empty until there is a domain. |
| `download_url` | The app's zip. While empty, the button says the download is coming. |
| `verify` | The codes from Google Search Console, Yandex Webmaster and Bing Webmaster Tools (`google`, `yandex`, `bing`): the code alone, not the whole tag. Each adds its tag to every page. |
| `indexnow_key` | Public by design: `build.py` puts it in a file on the site, which proves to IndexNow that the list of pages comes from the site's owner. |
| `donate` | A list of `{"label": "Ko-fi", "url": "https://..."}`, one button each. While empty, the section says they are coming. |

The site lives on Cloudflare Pages at https://slotless.pages.dev: a push to `main` builds and publishes it (build command `python3 build.py`, output directory `dist`). After a deploy that changes pages, `python3 indexnow.py` tells Bing and Yandex.

## Changing the text

Texts are in `src/i18n/<language>.json`, the page is `src/template.html`, its look `src/style.css`, its toys (the level in the hero, the practice screen, the coin) `src/site.js`, and all pixel art, also the favicon, `src/sprites.json`. `build.py` draws the picture for shared links, `og.png`. A new language takes a JSON file and an entry in `LANGS` in `build.py`.

## Rules for the text

No games, game art, characters or keys, no links to where to get them, and no logos of Nintendo or Apple. The legal line in the footer stays. Facts such as the number of tested games and the requirements come from the nxnative repository's README.

The mascot is this project's own. Keep the look original: nothing copied from Nintendo's characters, consoles or sounds.

Fonts load from Google Fonts. To avoid that request, host the files yourself and change `FONTS` in `build.py`.

The pictures in `src/shots/` are the app's real windows with stand-in files (no game, key or personal detail). English and Russian only, as the app speaks those two; every other language shows the English ones. Retake them when the app's look changes.
