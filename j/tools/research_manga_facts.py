from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
CHAPTER_DIR = SOURCE / "chapters"
OUTPUT = SOURCE / "chapter_line_evidence.json"
REPORT = ROOT / "reports" / "MANGA_SOURCE_RESEARCH.json"
CACHE = Path("/tmp/jujutsu-manga-source-cache")
CACHE_ONLY = os.environ.get("JUJUTSU_CACHE_ONLY") == "1"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)

SOURCE_REFS = {
    "eiga-manga": "src-shindo-chapter-recaps",
    "manga-games": "src-manga-games-manga-pages",
    "animenb": "src-animenb-manga-recaps",
    "idononaka": "src-idononaka-manga-recaps",
    "neet-life": "src-neet-life-manga-recaps",
    "manga5000": "src-manga5000-manga-recaps",
    "morn-life": "src-morn-life-manga-recaps",
}

CHAPTER_TITLE_RE = re.compile(
    r"(?:第\s*)?(\d{1,3})\s*話|呪術廻戦[^0-9]{0,12}(\d{1,3})\s*話"
)
QUOTE_RE = re.compile(r"[「『“\"]([^」』”\"]{2,48})[」』”\"]")
BOILERPLATE_RE = re.compile(
    r"アフィリエイト|広告を利用|メールアドレス|コメントをどうぞ|"
    r"サイト内検索|プロフィール|関連記事|購入はこちら|電子書籍|"
    r"無断転載|著作権|引用元|週刊少年ジャンプ.*発売|"
    r"この記事では|ネタバレを含|最新刊|次の記事|前の記事"
)
ANIME_RE = re.compile(
    r"TVアニメ|アニメ第|アニメ[0-9一二三四五六七八九十]*期|劇場版|映画版|"
    r"声優|放送|配信|Blu-ray|DVD"
)
OPINION_RE = re.compile(
    r"考察|予想|推測|かもしれ|と思います|と思う|でしょうか|だろうか|"
    r"個人的|気がします|気がする|楽しみ|期待|読者|筆者|"
    r"面白|カッコ|かっこ|ヤバ|すごい|凄い|好き|嫌い|"
    r"[ｗw]{2,}|（笑）|\(笑\)|\^/\^|管理人|芥見先生"
)
SPEECH_RE = re.compile(
    r"言(?:う|い|った|います|いました)|答え|返(?:す|し|答)|"
    r"告げ|叫|呟|つぶや|語|述べ|伝え|頼|命じ|宣言|"
    r"問い|尋ね|聞(?:く|き)|口に|発言|言葉|台詞|セリフ|遺言|胸中"
)
TECHNIQUE_RE = re.compile(
    r"術式|領域展開|呪法|呪具|呪物|呪霊|式神|奥義|極ノ番|"
    r"反転術式|簡易領域|落花の情|彌虚葛籠|黒閃"
)
NARRATIVE_ONLY_RE = re.compile(
    r"^(?:第?\d+話|呪術廻戦|渋谷事変|死滅回游|"
    r"まとめ|あらすじ|ネタバレ|感想|考察)"
)


@dataclass(frozen=True)
class Block:
    tag: str
    text: str


class PageParser(HTMLParser):
    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "p", "blockquote"}
    SKIP_TAGS = {"script", "style", "svg", "noscript", "form"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.links: list[tuple[str, str]] = []
        self._skip_depth = 0
        self._current_tag: str | None = None
        self._current_parts: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        attr_map = dict(attrs)
        if tag == "a":
            self._anchor_href = attr_map.get("href")
            self._anchor_parts = []
        if tag in self.BLOCK_TAGS and self._current_tag is None:
            self._current_tag = tag
            self._current_parts = []

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._current_tag is not None:
            self._current_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a" and self._anchor_href is not None:
            text = clean_text("".join(self._anchor_parts))
            self.links.append((self._anchor_href, text))
            self._anchor_href = None
            self._anchor_parts = []
        if tag == self._current_tag:
            text = clean_text("".join(self._current_parts))
            if text:
                self.blocks.append(Block(tag, text))
            self._current_tag = None
            self._current_parts = []


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = value.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_line(value):
    value = clean_text(value)
    return re.sub(
        r"[「」『』（）()【】\[\]、。！？!?・：:―—…〜～\s\"'“”]",
        "",
        value,
    ).lower()


def source_cache_path(url):
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE / f"{digest}.html"


def fetch(url, *, retries=2):
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = source_cache_path(url)
    if cache_path.exists() and cache_path.stat().st_size > 100:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    if CACHE_ONLY:
        raise RuntimeError(f"not cached: {url}")

    last_error = None
    for attempt in range(retries + 1):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml",
                    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
                },
            )
            with urlopen(request, timeout=45) as response:
                body = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
            text = body.decode(charset, errors="replace")
            cache_path.write_text(text, encoding="utf-8")
            return text
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last_error}")


def parse_page(text):
    parser = PageParser()
    parser.feed(text)
    return parser


def sitemap_urls(url):
    text = fetch(url)
    return [clean_text(item) for item in re.findall(r"<loc>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</loc>", text)]


def chapter_number_from_text(text):
    match = CHAPTER_TITLE_RE.search(clean_text(text))
    if not match:
        return None
    number = int(match.group(1) or match.group(2))
    return number if 1 <= number <= 271 else None


def chapter_id(number):
    return f"ch-{number:03d}"


def article_blocks(text):
    return parse_page(text).blocks


def split_volume_page(blocks):
    grouped = defaultdict(list)
    current = None
    for block in blocks:
        if block.tag in {"h2", "h3", "h4"}:
            match = re.search(r"第\s*(\d{1,3})\s*話", block.text)
            if match:
                number = int(match.group(1))
                current = number if 1 <= number <= 271 else None
                if current:
                    grouped[current].append(block)
                continue
            if re.search(r"おまけ|まとめ|感想|関連記事|購入", block.text):
                current = None
        if current:
            grouped[current].append(block)
    return grouped


def split_animenb_page(blocks):
    grouped = defaultdict(list)
    current = None
    started = False
    for block in blocks:
        if block.tag in {"h2", "h3", "h4"}:
            number = chapter_number_from_text(block.text)
            if number:
                current = number
                started = True
                grouped[current].append(block)
                continue
            if started and re.search(
                r"キャラクター|アニメ|映画|考察テーマ|伏線|関連記事", block.text
            ):
                current = None
        if current:
            grouped[current].append(block)
    return grouped


def source_urls():
    discovered = []

    for url in sitemap_urls("https://eiga-manga.com/post-sitemap.xml"):
        match = re.fullmatch(r"https://eiga-manga\.com/entry/jujutsu(\d+)", url.rstrip("/"))
        if match and 1 <= int(match.group(1)) <= 271:
            discovered.append(("eiga-manga", int(match.group(1)), url))

    manga_urls = []
    for sitemap in (
        "https://manga-games.com/post-sitemap.xml",
        "https://manga-games.com/post-sitemap2.xml",
    ):
        manga_urls.extend(sitemap_urls(sitemap))
    for url in sorted(set(manga_urls)):
        match = re.fullmatch(
            r"https://manga-games\.com/jujutsukaisen-jump-(\d+)(?:-\d+)?/",
            url,
        )
        if match and 1 <= int(match.group(1)) <= 271:
            discovered.append(("manga-games", int(match.group(1)), url))

    for url in sitemap_urls("https://idononaka.com/wp-sitemap-posts-post-1.xml"):
        match = re.fullmatch(
            r"https://idononaka\.com/jujutsukaisen-(?:netabare|netbare)(\d+)",
            url.rstrip("/"),
        )
        if match and 1 <= int(match.group(1)) <= 271:
            discovered.append(("idononaka", int(match.group(1)), url))

    neet_links = {}
    neet_base = (
        "https://neet-life-blog.com/category/"
        "%E6%BC%AB%E7%94%BB%E3%80%81%E3%82%A2%E3%83%8B%E3%83%A1/"
        "%E5%91%AA%E8%A1%93%E5%BB%BB%E6%88%A6/page/"
    )
    for page in range(1, 9):
        url = f"{neet_base}{page}"
        parser = parse_page(fetch(url))
        for href, text in parser.links:
            number = chapter_number_from_text(text)
            if not number or "呪術廻戦" not in text or ANIME_RE.search(text):
                continue
            absolute = urljoin(url, href).split("#", 1)[0]
            if absolute.startswith("https://neet-life-blog.com/"):
                neet_links[(number, absolute)] = text
    for number, url in sorted(neet_links):
        discovered.append(("neet-life", number, url))

    for number in range(1, 11):
        discovered.append(
            (
                "manga5000",
                number,
                "https://manga5000.com/"
                "%E5%91%AA%E8%A1%93%E5%BB%BB%E6%88%A6/"
                f"jujutukaisen-{number}/",
            )
        )
    discovered.extend(
        [
            ("morn-life", 1, "https://morn.life/2019/10/07/jujutsukaisen-1/"),
            ("morn-life", 2, "https://morn.life/2019/10/11/jujutsukaisen-2/"),
        ]
    )

    return sorted(set(discovered), key=lambda item: (item[1], item[0], item[2]))


def relevant_blocks(blocks, source):
    result = []
    stop = False
    factual_section = source != "eiga-manga"
    for block in blocks:
        text = block.text
        if block.tag in {"h2", "h3", "h4"}:
            if source == "eiga-manga":
                if re.search(r"あらすじ・ネタバレ|内容ネタバレ", text):
                    factual_section = True
                    stop = False
                elif factual_section and re.search(r"感想|考察|関連記事", text):
                    stop = True
            elif re.search(r"コメント|関連記事|購入はこちら", text):
                stop = True
        if stop or not factual_section:
            continue
        if BOILERPLATE_RE.search(text) or ANIME_RE.search(text):
            continue
        if len(text) < 2 or len(text) > 1800:
            continue
        result.append(block)
    return result


def character_aliases():
    characters = json.loads((SOURCE / "characters.json").read_text(encoding="utf-8"))
    aliases = {}
    for character in characters:
        name = clean_text(character.get("name"))
        for alias in [name, *character.get("aliases", [])]:
            alias = clean_text(alias)
            if len(alias) >= 2 and alias not in {"高専", "宿儺の器"}:
                aliases[alias] = name
    # Common short forms used by recap sites.
    aliases.update(
        {
            "虎杖": "虎杖悠仁",
            "悠仁": "虎杖悠仁",
            "伏黒": "伏黒恵",
            "釘崎": "釘崎野薔薇",
            "五条": "五条悟",
            "夏油": "夏油傑",
            "ニセ夏油": "羂索",
            "偽夏油": "羂索",
            "乙骨": "乙骨憂太",
            "真希": "禪院真希",
            "真依": "禪院真依",
            "直哉": "禪院直哉",
            "脹相": "脹相",
            "宿儺": "両面宿儺",
            "日車": "日車寛見",
            "秤": "秤金次",
            "高羽": "髙羽史彦",
        }
    )
    return dict(sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True))


ALIASES = character_aliases()
REPORTED_SPEECH_PATTERNS = {
    alias: re.compile(
        rf"{re.escape(alias)}(?:は|が|も)?[^。]{{0,18}}[、：]\s*"
        rf"([^、。]{{3,42}}?)[、]\s*と"
        rf"(?:言|答|返|告|叫|呟|語|述|伝|頼|命|宣言)"
    )
    for alias in ALIASES
}


def infer_speaker(context, phrase):
    index = context.find(phrase)
    before = context[max(0, index - 120) : index] if index >= 0 else context
    after = context[index + len(phrase) : index + len(phrase) + 80] if index >= 0 else ""
    scores = Counter()
    for alias, canonical in ALIASES.items():
        if alias not in before and alias not in after:
            continue
        escaped = re.escape(alias)
        if re.search(
            rf"{escaped}(?:は|が|も)?[^。]{{0,45}}(?:言|答|返|告|叫|呟|語|述|伝|頼|命|宣言|問い|聞)[^。]{{0,20}}$",
            before,
        ):
            scores[canonical] += 7
        if re.search(rf"{escaped}(?:は|が|も|に対して|へ)[^。]{{0,55}}$", before):
            scores[canonical] += 3
        if alias in before[-45:]:
            scores[canonical] += 1
        if re.search(
            rf"^(?:[^。]{{0,30}})(?:と|、と)(?:言|答|返|告|叫|呟|語|述|伝)[^。]{{0,25}}{escaped}",
            after,
        ):
            scores[canonical] += 7
    if not scores:
        return None
    speaker, score = scores.most_common(1)[0]
    return speaker if score >= 3 else None


def dialogue_like(phrase, context):
    if SPEECH_RE.search(context):
        return True
    return bool(
        re.search(
            r"(?:だ|だよ|だろ|だな|です|ます|ない|ねぇ|しろ|せよ|"
            r"やれ|来い|行け|任せろ|ありがとう|ごめん|僕|俺|私|"
            r"オマエ|お前|君|アンタ|テメェ|誰|何|どう|なぜ|何故)$",
            phrase,
        )
    )


def candidate_is_safe(phrase, context):
    phrase = clean_text(phrase).strip(" 　、。！？!?…―—")
    normalized = normalize_line(phrase)
    if not (3 <= len(normalized) <= 38):
        return False
    if NARRATIVE_ONLY_RE.search(phrase) or BOILERPLATE_RE.search(phrase):
        return False
    if ANIME_RE.search(context):
        return False
    local_index = context.find(phrase)
    local = (
        context[max(0, local_index - 100) : local_index + len(phrase) + 100]
        if local_index >= 0
        else context
    )
    if OPINION_RE.search(local) and not SPEECH_RE.search(local):
        return False
    if TECHNIQUE_RE.fullmatch(phrase):
        return False
    return dialogue_like(phrase, local)


def extract_candidates(blocks, source, chapter_number, url):
    candidates = []
    for block in relevant_blocks(blocks, source):
        context = block.text
        if OPINION_RE.search(context) and not SPEECH_RE.search(context):
            continue
        for match in QUOTE_RE.finditer(context):
            phrase = clean_text(match.group(1))
            if not candidate_is_safe(phrase, context):
                continue
            candidates.append(
                {
                    "chapter": chapter_number,
                    "phrase": phrase,
                    "normalized": normalize_line(phrase),
                    "speaker": infer_speaker(context, phrase),
                    "source": source,
                    "sourceRef": SOURCE_REFS[source],
                    "url": url,
                    "capture": "quoted",
                }
            )

        # Some recaps omit quotation marks but preserve "Xは、…、と言う".
        for alias, canonical in ALIASES.items():
            if alias not in context:
                continue
            for match in REPORTED_SPEECH_PATTERNS[alias].finditer(context):
                phrase = clean_text(match.group(1))
                if not candidate_is_safe(phrase, context):
                    continue
                candidates.append(
                    {
                        "chapter": chapter_number,
                        "phrase": phrase,
                        "normalized": normalize_line(phrase),
                        "speaker": canonical,
                        "source": source,
                        "sourceRef": SOURCE_REFS[source],
                        "url": url,
                        "capture": "reported-speech",
                    }
                )
    return candidates


def line_similarity(left, right):
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 5 and shorter in longer:
        return len(shorter) / len(longer)
    return SequenceMatcher(None, left, right).ratio()


def cluster_candidates(candidates):
    clusters = []
    for item in sorted(candidates, key=lambda row: (-len(row["normalized"]), row["phrase"])):
        best = None
        best_score = 0.0
        for cluster in clusters:
            score = line_similarity(item["normalized"], cluster["key"])
            if score > best_score:
                best = cluster
                best_score = score
        if best is not None and best_score >= 0.86:
            best["items"].append(item)
            if len(item["normalized"]) < len(best["key"]):
                best["key"] = item["normalized"]
        else:
            clusters.append({"key": item["normalized"], "items": [item]})
    return clusters


def choose_phrase(items):
    counts = Counter(item["phrase"] for item in items)
    return sorted(
        counts,
        key=lambda phrase: (-counts[phrase], len(normalize_line(phrase)), phrase),
    )[0]


def choose_speaker(items):
    source_support = defaultdict(set)
    for item in items:
        if item.get("speaker"):
            source_support[item["speaker"]].add(item["source"])
    if not source_support:
        return None
    speaker, sources = max(
        source_support.items(), key=lambda pair: (len(pair[1]), pair[0])
    )
    return speaker if len(sources) >= 2 else None


def build_verified_lines(candidates):
    grouped = defaultdict(list)
    for item in candidates:
        grouped[item["chapter"]].append(item)

    result = {}
    for number in range(1, 272):
        verified = []
        for cluster in cluster_candidates(grouped.get(number, [])):
            normalized_support = defaultdict(set)
            for item in cluster["items"]:
                normalized_support[item["normalized"]].add(item["source"])
            exact_normalized = [
                value
                for value, sources_for_value in normalized_support.items()
                if len(sources_for_value) >= 2
            ]
            if not exact_normalized:
                continue
            selected_normalized = max(
                exact_normalized,
                key=lambda value: (
                    len(normalized_support[value]),
                    sum(item["normalized"] == value for item in cluster["items"]),
                    len(value),
                    value,
                ),
            )
            items = [
                item
                for item in cluster["items"]
                if item["normalized"] == selected_normalized
            ]
            sources = sorted({item["source"] for item in items})
            phrase = choose_phrase(items)
            refs = sorted({item["sourceRef"] for item in items})
            urls = []
            for source in sources:
                source_urls_for_line = sorted(
                    {item["url"] for item in items if item["source"] == source}
                )
                if source_urls_for_line:
                    urls.append(source_urls_for_line[0])
            verified.append(
                {
                    # Surrounding recap prose can place several names beside one
                    # line. Even two sites can repeat the same recap structure,
                    # so secondary articles alone are not strong enough to
                    # publish a speaker as fact. Keep attribution deliberately
                    # blank until the primary manga page is checked directly.
                    "speaker": None,
                    "text": phrase,
                    "kind": "短い作中語句・発言",
                    "verification": "crosschecked-manga-secondary",
                    "sourceCount": len(sources),
                    "sourceRefs": refs,
                    "sourceUrls": urls,
                }
            )
        unique = []
        for item in sorted(
            verified,
            key=lambda row: (-row["sourceCount"], row["speaker"] or "", row["text"]),
        ):
            if any(
                line_similarity(normalize_line(item["text"]), normalize_line(old["text"]))
                >= 0.88
                for old in unique
            ):
                continue
            unique.append(item)
        result[chapter_id(number)] = unique
    return result


def add_text_confirmations(candidates, evidence_texts):
    enriched = list(candidates)
    seen = {
        (
            item["chapter"],
            item["normalized"],
            item["source"],
            item["url"],
        )
        for item in candidates
    }
    for item in candidates:
        normalized = item["normalized"]
        if len(normalized) < 5:
            continue
        for source, pages in evidence_texts.get(item["chapter"], {}).items():
            if source == item["source"]:
                continue
            for url, normalized_page_text in pages:
                if normalized not in normalized_page_text:
                    continue
                key = (item["chapter"], normalized, source, url)
                if key in seen:
                    break
                confirmed = dict(item)
                confirmed.update(
                    {
                        "speaker": None,
                        "source": source,
                        "sourceRef": SOURCE_REFS[source],
                        "url": url,
                        "capture": "plain-text-confirmation",
                    }
                )
                enriched.append(confirmed)
                seen.add(key)
                break
    return enriched


def add_evidence_text(evidence_texts, number, source, url, blocks):
    text = normalize_line(" ".join(block.text for block in relevant_blocks(blocks, source)))
    if text:
        evidence_texts[number][source].append((url, text))


def fetch_articles(entries):
    results = {}
    errors = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(fetch, url): (source, number, url)
            for source, number, url in entries
        }
        completed = 0
        for future in as_completed(future_map):
            source, number, url = future_map[future]
            try:
                results[(source, number, url)] = future.result()
            except Exception as error:
                errors.append({"source": source, "chapter": number, "url": url, "error": str(error)})
            completed += 1
            if completed % 50 == 0:
                print(f"fetched {completed}/{len(entries)}", flush=True)
    return results, errors


def main():
    entries = source_urls()
    print(f"discovered chapter articles: {len(entries)}", flush=True)
    pages, errors = fetch_articles(entries)

    all_candidates = []
    coverage = defaultdict(set)
    evidence_texts = defaultdict(lambda: defaultdict(list))
    page_counts = Counter()

    for (source, number, url), text in pages.items():
        blocks = article_blocks(text)
        all_candidates.extend(extract_candidates(blocks, source, number, url))
        add_evidence_text(evidence_texts, number, source, url, blocks)
        coverage[number].add(source)
        page_counts[source] += 1

    volume_entries = [
        ("manga-games", volume, f"https://manga-games.com/jujutsukaisen-vol-{volume}/")
        for volume in range(1, 31)
    ]
    volume_pages, volume_errors = fetch_articles(volume_entries)
    errors.extend(volume_errors)
    for (source, _volume, url), text in volume_pages.items():
        grouped = split_volume_page(article_blocks(text))
        for number, blocks in grouped.items():
            all_candidates.extend(extract_candidates(blocks, source, number, url))
            add_evidence_text(evidence_texts, number, source, url, blocks)
            coverage[number].add(source)
        page_counts["manga-games-volumes"] += 1

    animenb_url = "https://animenb.com/jujutukaisen-latest-story/"
    try:
        grouped = split_animenb_page(article_blocks(fetch(animenb_url)))
        for number, blocks in grouped.items():
            all_candidates.extend(
                extract_candidates(blocks, "animenb", number, animenb_url)
            )
            add_evidence_text(evidence_texts, number, "animenb", animenb_url, blocks)
            coverage[number].add("animenb")
        page_counts["animenb-index"] = 1
    except Exception as error:
        errors.append(
            {
                "source": "animenb",
                "chapter": None,
                "url": animenb_url,
                "error": str(error),
            }
        )

    all_candidates = add_text_confirmations(all_candidates, evidence_texts)
    verified = build_verified_lines(all_candidates)
    counts = {
        "chapters": 271,
        "chaptersWithTwoOrMoreSourceFamilies": sum(
            1 for number in range(1, 272) if len(coverage[number]) >= 2
        ),
        "rawLineCandidates": len(all_candidates),
        "crosscheckedLines": sum(len(items) for items in verified.values()),
        "chaptersWithCrosscheckedLines": sum(bool(items) for items in verified.values()),
    }
    output = {
        "schemaVersion": 1,
        "scope": "manga-only",
        "policy": {
            "officialPriority": "公式の話数・巻・題名を基準にする。",
            "secondaryUse": "個人サイトは漫画の出来事・短い発言候補の照合だけに使う。",
            "excluded": ["アニメ", "劇場版", "ゲーム", "小説", "感想", "評価", "予想", "考察"],
            "adoption": "異なる二つ以上のサイト系統で一致した短い発言だけを表示候補にする。",
            "speakerAttribution": "二次記事だけでは誤帰属を排除できないため、話者は原作ページ直接監査まで表示しない。",
        },
        "sourceRefs": sorted(set(SOURCE_REFS.values())),
        "counts": counts,
        "chapters": verified,
    }
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "counts": counts,
        "pageCounts": dict(sorted(page_counts.items())),
        "sourceCoverageByChapter": {
            chapter_id(number): sorted(coverage[number]) for number in range(1, 272)
        },
        "errors": errors,
    }
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"counts": counts, "pages": page_counts, "errors": len(errors)}, ensure_ascii=False))
    if errors:
        print("warning: some pages failed; see report", file=sys.stderr)


if __name__ == "__main__":
    main()
