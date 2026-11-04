#!/usr/bin/env python3
"""Builds the landing page into dist/: one real page per language, so search engines can find each.

Usage: python3 build.py     (exit 1 when a language lacks a text or has a text the template does not use)

Only config.json needs editing to go live:
  base_url      the site's address, for search engines; empty until there is one
  download_url  the zip of the app; while empty the button says the download is coming
  donate        a list of {"label": "Ko-fi", "url": "https://..."}; while empty the section says so
  verify        the codes that search engines' webmaster tools give (google, yandex, bing); an empty one adds nothing
"""
import html
import json
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC, DIST = ROOT / 'src', ROOT / 'dist'
# The first is the root page; a visitor's browser language moves them from there to their own.
LANGS = ['en', 'ru', 'es', 'de', 'fr', 'pt-BR', 'ja', 'zh-Hans']
FONTS = 'family=Handjet:wght@500;700&family=Golos+Text:wght@400;600'
LANG_FONTS = {'ja': '&family=DotGothic16&family=Noto+Sans+JP:wght@400;600', 'zh-Hans': '&family=ZCOOL+KuaiLe&family=Noto+Sans+SC:wght@400;600'}


OG_LOCALES = {'en': 'en_US', 'ru': 'ru_RU', 'es': 'es_ES', 'de': 'de_DE', 'fr': 'fr_FR', 'pt-BR': 'pt_BR', 'ja': 'ja_JP', 'zh-Hans': 'zh_CN'}
VERIFY_TAGS = {'google': 'google-site-verification', 'yandex': 'yandex-verification', 'bing': 'msvalidate.01'}
OG_SIZE = (1200, 630)
GLYPHS = {
    'S': ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'], 'L': ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
    'O': ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'], 'T': ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
    'E': ['#####', '#....', '#....', '####.', '#....', '#....', '#####'], 'F': ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
    'R': ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'], 'P': ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
    'A': ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'], 'Y': ['#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'],
}


def og_image(sprites):
    """The picture a shared link shows: the hero's level, in words every language's reader knows, so one image serves all pages."""
    w, h = OG_SIZE
    rgb = lambda c: bytes.fromhex(c.lstrip('#'))
    sky, deep, dot, ink, yolk, white = rgb('#3a2be8'), rgb('#2a1fc4'), rgb('#5c50ee'), rgb('#15104a'), rgb('#ffd23f'), rgb('#ffffff')
    px = bytearray(sky * (w * h))

    def rect(x, y, rw, rh, colour):
        for row in range(max(y, 0), min(y + rh, h)):
            left, right = max(x, 0), min(x + rw, w)
            if right > left:
                px[(row * w + left) * 3:(row * w + right) * 3] = colour * (right - left)

    def text(word, x, y, cell, colour):
        for ch in word:
            for gy, line in enumerate(GLYPHS.get(ch, [])):
                for gx, on in enumerate(line):
                    if on == '#':
                        rect(x + gx * cell, y + gy * cell, cell, cell, colour)
            x += 6 * cell

    ground = 500
    for y in range(20, ground, 40):
        for x in range(20, w, 40):
            rect(x, y, 3, 3, dot)
    for x, bw, bh in ((0, 90, 70), (120, 60, 120), (210, 130, 50), (370, 70, 95), (470, 50, 140), (550, 140, 70), (720, 70, 60), (820, 100, 120), (1040, 80, 70), (1140, 60, 130)):
        rect(x, ground - bh, bw, bh, deep)
    rect(0, ground, w, h - ground, ink)
    for x in range(10, w, 100):
        rect(x, ground + 34, 60, 14, yolk)
    text('SLOTLESS', 78, 108, 15, ink)
    text('SLOTLESS', 70, 100, 15, white)
    text('FREE PLAY', 74, 256, 9, ink)
    text('FREE PLAY', 70, 252, 9, yolk)
    rows, cell = sprites['sprites']['hero_a'], 20
    left, top = 880, ground - len(rows) * cell
    for ry, row in enumerate(rows):
        for rx, c in enumerate(row):
            if c != '.':
                rect(left + rx * cell, top + ry * cell, cell, cell, rgb(sprites['palette'][c]))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    raw = b''.join(b'\0' + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def seo_tags(lang, config, t, page_url, base):
    """The parts of the head that need the site's address, or the webmaster tools' codes."""
    e = lambda s: html.escape(s, quote=True)
    tags = [f'<meta name="{VERIFY_TAGS[k]}" content="{e(v)}">' for k, v in config.get('verify', {}).items() if v and k in VERIFY_TAGS]
    tags += [f'<meta property="og:site_name" content="{e(t["app_name"])}">', '<meta name="twitter:card" content="summary_large_image">', f'<meta name="twitter:title" content="{e(t["title"])}">', f'<meta name="twitter:description" content="{e(t["description"])}">']
    tags += [f'<meta property="og:locale:alternate" content="{OG_LOCALES[l]}">' for l in LANGS if l != lang]
    if not base:
        return '\n'.join(tags)
    image = f'{base}/og.png'
    tags += [f'<meta property="og:url" content="{e(page_url)}">', f'<meta property="og:image" content="{e(image)}">', f'<meta property="og:image:width" content="{OG_SIZE[0]}">', f'<meta property="og:image:height" content="{OG_SIZE[1]}">', f'<meta property="og:image:alt" content="{e(t["description"])}">', f'<meta name="twitter:image" content="{e(image)}">']
    app = {'@context': 'https://schema.org', '@type': 'SoftwareApplication', 'name': t['app_name'], 'description': t['description'], 'url': page_url, 'image': image, 'inLanguage': lang,
           'operatingSystem': 'macOS 26.6 or later', 'applicationCategory': 'UtilitiesApplication', 'isAccessibleForFree': True, 'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD'}}
    if config['download_url']:
        app['downloadUrl'] = config['download_url']
    tags.append('<script type="application/ld+json">' + json.dumps(app, ensure_ascii=False).replace('<', '\\u003c') + '</script>')
    return '\n'.join(tags)


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
    computed = {'lang', 'root', 'alternates', 'language_links', 'download_button', 'donate_buttons', 'source_url', 'upstream_url', 'games_url', 'font_link', 'sprites_json', 'shot_lang', 'seo', 'og_locale'}
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
                  seo=seo_tags(lang, config, t, f'{base}/{url(lang)}', base), og_locale=OG_LOCALES[lang],
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
    (DIST / 'og.png').write_bytes(og_image(sprites))
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
