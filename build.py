#!/usr/bin/env python3
"""Builds the landing page into dist/: one real page per language, so search engines can find each.

Usage: python3 build.py     (exit 1 when a language lacks a text or has a text the template does not use)

Only config.json needs editing to go live:
  base_url      the site's address, for search engines; empty until there is one
  download_url  the zip of the app; while empty the button says the download is coming
  donate        a list of {"label": "Ko-fi", "url": "https://..."}; while empty the section says so
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC, DIST = ROOT / 'src', ROOT / 'dist'
# The first is the root page; a visitor's browser language moves them from there to their own.
LANGS = ['en', 'ru', 'es', 'de', 'fr', 'pt-BR', 'ja', 'zh-Hans']
FONTS = 'family=Handjet:wght@500;700&family=Golos+Text:wght@400;600'
LANG_FONTS = {'ja': '&family=DotGothic16&family=Noto+Sans+JP:wght@400;600', 'zh-Hans': '&family=ZCOOL+KuaiLe&family=Noto+Sans+SC:wght@400;600'}


def sprite_svg(rows, palette, standalone=False):
    """Pixel art as an SVG of rectangles, so that it stays sharp at any size and needs no image file."""
    if len({len(r) for r in rows}) != 1:
        raise ValueError(f'a sprite has rows of different widths: {rows}')
    w, h = len(rows[0]), len(rows)
    rects = ''.join(f'<path fill="{palette[m.group(1)]}" d="M{m.start()} {y}h{len(m.group(0))}v1H{m.start()}z"/>'
                    for y, row in enumerate(rows) for m in re.finditer(r'([^.])\1*', row))
    size = f' width="{w}" height="{h}"' if standalone else ' class="spr" aria-hidden="true"'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"{size} shape-rendering="crispEdges">{rects}</svg>'


def load():
    config = json.loads((ROOT / 'config.json').read_text('utf-8'))
    return config, {l: json.loads((SRC / 'i18n' / f'{l}.json').read_text('utf-8')) for l in LANGS}


def check(texts, template):
    keys = set(re.findall(r'\{\{(\w+)\}\}', template))
    computed = {'lang', 'root', 'alternates', 'language_links', 'download_button', 'donate_buttons', 'source_url', 'upstream_url', 'games_url', 'font_link', 'sprites_json', 'shot_lang'}
    computed |= {k for k in keys if k.startswith('spr_')}
    errors = []
    for lang, t in texts.items():
        errors += [f'{lang}: no text for {k}' for k in sorted(keys - computed - set(t))]
        errors += [f'{lang}: {k} is not used' for k in sorted(set(t) - keys - {'cta_download', 'cta_soon', 'donate_soon'})]   # those three go into the buttons, below
    return errors


def page(lang, config, texts, template, sprites):
    t = texts[lang]
    root = '' if lang == LANGS[0] else '../'
    url = lambda l: '' if l == LANGS[0] else f'{l}/'
    base = config['base_url'].rstrip('/')
    alternates = ''
    if base:
        alternates = '\n'.join(f'<link rel="alternate" hreflang="{l}" href="{base}/{url(l)}">' for l in LANGS)
        alternates += f'\n<link rel="alternate" hreflang="x-default" href="{base}/">\n<link rel="canonical" href="{base}/{url(lang)}">'
    links = ''.join(
        f'<li><a href="{root}{url(l)}" hreflang="{l}" lang="{l}"' + (' aria-current="true"' if l == lang else '') + f'>{html.escape(texts[l]["lang_name"])}</a></li>'
        for l in LANGS)
    e = lambda s: html.escape(s, quote=True)
    download = (f'<a class="button" href="{e(config["download_url"])}">{e(t["cta_download"])}</a>' if config['download_url']
                else f'<span class="button soon" aria-disabled="true">{e(t["cta_soon"])}</span>')
    donate = (''.join(f'<a class="button" href="{e(d["url"])}" rel="noopener">{e(d["label"])}</a>' for d in config['donate'])
              or f'<span class="button soon">{e(t["donate_soon"])}</span>')
    values = {k: e(v) for k, v in t.items()}
    values.update(lang=lang, root=root, alternates=alternates, language_links=links, download_button=download, donate_buttons=donate,
                  source_url=e(config['source_url']), upstream_url=e(config['upstream_url']), games_url=e(config['games_url']),
                  font_link=e(f"https://fonts.googleapis.com/css2?{FONTS}{LANG_FONTS.get(lang, '')}&display=swap"),
                  sprites_json=json.dumps(sprites, separators=(',', ':')),
                  shot_lang='ru' if lang == 'ru' else 'en')   # the app itself speaks these two
    values.update({f'spr_{n}': sprite_svg(rows, sprites['palette']) for n, rows in sprites['sprites'].items()})
    return re.sub(r'\{\{(\w+)\}\}', lambda m: values[m.group(1)], template)


# The root page only: the first visit goes to the visitor's language, a choice made on the site stays
REDIRECT = '''<script>(function () {
  var langs = %s, saved = null;
  try { saved = localStorage.getItem('lang'); } catch (e) {}
  if (saved) return;
  var want = (navigator.languages || [navigator.language || 'en']);
  for (var i = 0; i < want.length; i++) {
    var w = want[i].toLowerCase(), pick = null;
    if (w.indexOf('en') === 0) return;
    if (w.indexOf('zh') === 0) pick = 'zh-Hans';
    else if (w.indexOf('pt') === 0) pick = 'pt-BR';
    else for (var j = 0; j < langs.length; j++) if (w.split('-')[0] === langs[j].toLowerCase()) pick = langs[j];
    if (pick) { location.replace(pick + '/'); return; }
  }
})();</script>
'''


def main():
    config, texts = load()
    template = (SRC / 'template.html').read_text('utf-8')
    errors = check(texts, template)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()
    for f in ('style.css', 'site.js'):
        shutil.copy2(SRC / f, DIST / f)
    shutil.copytree(SRC / 'shots', DIST / 'shots')
    sprites = json.loads((SRC / 'sprites.json').read_text('utf-8'))
    (DIST / 'icon.svg').write_text(sprite_svg(sprites['sprites']['hero_a'], sprites['palette'], standalone=True), 'utf-8')
    for lang in LANGS:
        out = DIST if lang == LANGS[0] else DIST / lang
        out.mkdir(exist_ok=True)
        text = page(lang, config, texts, template, sprites)
        if lang == LANGS[0]:
            text = text.replace('</head>', REDIRECT % json.dumps(LANGS) + '</head>', 1)
        (out / 'index.html').write_text(text, 'utf-8')
    if config['base_url']:
        base = config['base_url'].rstrip('/')
        urls = ''.join(f'<url><loc>{base}/{"" if l == LANGS[0] else l + "/"}</loc></url>' for l in LANGS)
        (DIST / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', 'utf-8')
        (DIST / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n', 'utf-8')
    (DIST / '.nojekyll').write_text('')
    print(f'{len(LANGS)} languages in {DIST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
