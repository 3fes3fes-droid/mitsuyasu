from __future__ import annotations
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('collector', ROOT / 'tools' / 'refresh_official_images.py')
collector = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(collector)

sample_image = 'https://cdn-scissors.gigaviewer.com/image/scale/abc/enlarge=0;height=450/https%3A%2F%2Fcdn-ak-img.shonenjumpplus.com%2Fpublic%2Fepisode-thumbnail%2F123-x%3F1'
html = f'''<!doctype html><html><head><title>[第2話]呪術廻戦 - 芥見下々</title><meta property="og:title" content="[第2話]呪術廻戦 - 芥見下々"><meta name="twitter:image" content="{sample_image}"><meta property="og:url" content="https://shonenjumpplus.com/episode/222"></head><body><a href="/episode/333">次の話を読む</a></body></html>'''
parsed = collector.parse_episode_page('https://shonenjumpplus.com/episode/222', html)
assert parsed['title'].startswith('[第2話]呪術廻戦')
assert parsed['imageUrl'] == sample_image
assert parsed['episodeUrl'] == 'https://shonenjumpplus.com/episode/222'
assert parsed['nextUrl'] == 'https://shonenjumpplus.com/episode/333'
assert collector.chapter_number(parsed['title']) == 2
collector.ensure_expected_series(parsed['title'], 'main')
assert collector.valid_remote_url(parsed['imageUrl'])

rss = f'''<?xml version="1.0"?><rss><channel><item><title>[第2話]呪術廻戦 - 芥見下々</title><link>https://shonenjumpplus.com/episode/222</link><description><![CDATA[<img src="{sample_image}">]]></description></item></channel></rss>'''
item = ET.fromstring(rss).find('.//item')
urls = collector.extract_urls_from_item(item)
assert 'https://shonenjumpplus.com/episode/222' in urls
assert any('episode-thumbnail' in url for url in urls)
print('PASS: official image parser fixtures')
