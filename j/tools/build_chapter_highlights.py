from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
CHAPTER_DIR = SOURCE / "chapters"
OUTPUT = SOURCE / "chapter_highlights.json"
LINE_EVIDENCE = SOURCE / "chapter_line_evidence.json"
POPULAR_SOURCE_REF = "src-ciatr-quotes-2026"


# Publicly discussed lines are stored as short search labels plus original prose
# summaries.  The database deliberately does not reproduce long dialogue.
POPULAR_LINE_GISTS = [
    ("zero-04", 1, "乙骨憂太", "純愛", "里香への思いを、侮辱されるようなものではなく純愛だと言い切る。"),
    ("ch-002", 2, "伏黒恵", "死なせたくない", "規定より自分の気持ちを優先し、虎杖を救ってほしいと五条へ頼む。"),
    ("ch-005", 3, "釘崎野薔薇", "私であるため", "自分らしく生きるためなら、危険な呪術師の道にも命を懸けられると示す。"),
    ("ch-002", 4, "五条悟", "僕 最強", "宿儺を前にしても心配はいらないと断言し、自身の強さを端的に示す。"),
    ("ch-003", 5, "虎杖悠仁", "生き様に後悔しない", "死に方は選べなくても、生き方だけは後悔したくないと覚悟を決める。"),
    ("ch-009", 6, "伏黒恵", "不平等に助ける", "善人を優先する自分の基準を受け入れ、不平等に人を救うと宣言する。"),
    ("ch-041", 7, "釘崎野薔薇", "釘崎野薔薇である", "周囲の物差しではなく、自分自身として生きることを強く言い切る。"),
    ("ch-058", 8, "五条悟", "死ぬ時は独り", "仲間を計算に入れて限界を決めず、単独でも勝てる強さを求めろと伏黒を促す。"),
    ("ch-019", 9, "七海建人", "小さな絶望", "日常に積み重なる小さな失望こそが人を大人にすると虎杖へ説く。"),
    ("ch-072", 10, "夏油傑", "二人は最強", "五条と自分なら理子の望みを守れると伝え、彼女自身の選択を後押しする。"),
    ("zero-01", 11, "五条悟", "愛と呪い", "深い愛情は、ときに最も歪んだ呪いになり得るという見方を乙骨へ示す。"),
    ("ch-009", 12, "伏黒津美紀", "大切な人を思う", "他人を呪うことに時間を使わず、大切な人を思いたいという価値観を示す。"),
    ("ch-093", 13, "羂索", "後悔の味", "後悔をほとんど覚えていないかのように振る舞い、長い生と底知れなさをにおわせる。"),
    ("ch-041", 14, "釘崎野薔薇", "不幸は免罪符ではない", "不幸な境遇を理由に他人を傷つけることは許されないと西宮へ突きつける。"),
    ("ch-126", 15, "真人", "正しさの衝突", "戦いを善悪の決着ではなく、互いの正しさを押しつける争いだと虎杖へ語る。"),
    ("ch-159", 16, "日車寛見", "目を開けていたい", "皆が不都合な現実から目をそらしても、自分だけは見続けると決意する。"),
    ("ch-128", 17, "与幸吉", "幸せを願う", "自分がもう隣にいられなくても、三輪には幸せに生きてほしいと願う。"),
    ("ch-021", 18, "真人", "言い訳と言葉遊び", "人間は自分を正当化する言葉がなければ生きられないという冷めた見方を語る。"),
    ("ch-176", 19, "乙骨憂太", "自分のために必死", "他者を顧みない烏鷺へ、人が自分のために尽くす意味を問い返す。"),
    ("ch-127", 20, "東堂葵", "託されたもの", "死者へ安易な意味を与えず、仲間から託されたものを考え続けろと虎杖を立たせる。"),
    ("ch-009", 21, "伏黒恵", "英雄ではなく呪術師", "万人を平等に救う英雄ではなく、自分の基準で救う呪術師だと宿儺へ示す。"),
    ("ch-125", 22, "釘崎野薔薇", "悪くない人生", "最期を覚悟した瞬間にも、自分の人生は悪いものではなかったと仲間へ託す。"),
    ("ch-040", 23, "西宮桃", "女術師に求められる完璧", "女性の術師には実力だけでなく外見や振る舞いまで求められる現実を訴える。"),
    ("ch-021", 24, "吉野順平", "無関心という言葉", "悪意ある関与を無関心より上に置く通念へ、当事者の立場から疑問を投げる。"),
    ("ch-024", 25, "虎杖悠仁", "殺すという選択肢", "一度人を殺せば、殺人が日常の選択肢になることを恐れていると順平へ話す。"),
    ("ch-187", 26, "鹿紫雲一", "生前葬", "秤の無敵時間をしのぐのではなく、その最中に倒すと戦意を高める。"),
    ("ch-220", 27, "家入硝子", "独りではなかった", "独りで走ってきたと思う五条へ、自分もずっと仲間だったと心の中で返す。"),
    ("ch-116", 28, "両面宿儺", "強さを認める", "敗れた漏瑚の強さを認め、胸を張るに値すると告げる。"),
    ("ch-223", 29, "五条悟", "挑戦者は宿儺", "最強同士の決戦でも宿儺の側が挑む立場だと余裕を崩さない。"),
    ("ch-177", 30, "石流龍", "満たされない食欲", "十分な人生を送ってもなお残る飢えこそ、自分の不満の正体だと捉える。"),
    ("ch-079", 31, "五条悟", "置いていかれない強さ", "幼い伏黒へ、自分に置いていかれないほど強くなれと期待を託す。"),
    ("ch-078", 32, "夏油傑", "選んだ本音", "非術師を守る建前を捨て、術師だけの世界を選ぶ本音を明らかにする。"),
    ("ch-221", 33, "五条悟", "今際の際", "封印から戻るなり羂索へ死を意識させ、主導権を握る。"),
    ("ch-018", 34, "禪院真希", "禪院家への意趣返し", "見下した一族を実力で見返すことを、自分が術師を続ける動機として語る。"),
    ("ch-134", 35, "脹相", "兄として割り込む", "虎杖を弟と確信し、危険を押しのけて兄として守ろうとする。"),
    ("ch-018", 36, "五条悟", "災難にも数えない", "特級呪霊との遭遇すら取るに足らない出来事として扱い、実力差を示す。"),
    ("ch-046", 37, "狗巻棘", "吹き飛ばす呪言", "喉が限界でも強い呪言を放ち、花御から仲間を守る。"),
    ("ch-157", 38, "虎杖悠仁", "自分は部品", "個人の感情より呪いを祓う役割を優先し、自分を機能の一部として定義する。"),
    ("ch-001", 39, "虎杖倭助", "人を助ける遺言", "力のある悠仁には人を助け、多くの人に囲まれて最期を迎えてほしいと遺す。"),
    ("ch-120", 40, "七海建人", "後を託す", "最期の瞬間、重荷になることを恐れながらも虎杖へ先を託す。"),
    ("ch-223", 41, "伊地知潔高", "信頼に応える結界", "五条から寄せられた信頼に命懸けで応える覚悟を固める。"),
    ("ch-042", 42, "禪院真依", "一緒に落ちぶれてほしかった", "姉に置いていかれた寂しさと、望まない修行へ巻き込まれた苦しさを吐露する。"),
    ("ch-019", 43, "七海建人", "呪術師という仕事", "呪術師も会社員も楽ではないと割り切り、適性のある仕事として術師を選ぶ。"),
    ("ch-019", 44, "東堂葵", "好みを問う", "女性の好みには人間性が表れるとして、初対面の相手へ型破りな質問をする。"),
    ("ch-221", 45, "五条悟", "勝利を断言", "宿儺との決戦を前に、以前と変わらない確信で自分が勝つと答える。"),
    ("ch-113", 46, "伏黒甚爾", "禪院ではない安堵", "息子が禪院家へ渡らず伏黒として生きたと知り、安堵して暴走を止める。"),
    ("ch-028", 47, "両面宿儺", "二度目は許さない", "自分の魂へ触れた真人へ、次は許さないと圧倒的な上下関係を示す。"),
    ("zero-04", 48, "夏油傑", "最後の言葉", "五条からかけられた言葉を受け、親友らしい皮肉を返して最期を迎える。"),
    ("ch-010", 49, "五条悟", "上層部への怒り", "生徒を死地へ送った上層部へ、力ずくの排除すら選べる怒りを見せる。"),
    ("ch-058", 50, "伏黒恵", "自由に戦う", "自己犠牲の癖を捨て、勝つために欲張って未完成の領域を展開する。"),
    ("ch-084", 51, "五条悟", "勝算への嘲笑", "漏瑚が自分に勝てると考えたこと自体を、冷たくあざ笑う。"),
    ("ch-027", 52, "真人", "順平を嘲る", "自分を信じた順平を愚かだと切り捨て、直後に無為転変の対象にする。"),
    ("ch-074", 53, "五条悟", "覚醒の高揚", "死の淵で反転術式を会得し、極度の高揚状態で甚爾との再戦へ入る。"),
    ("ch-090", 54, "羂索", "正体を見抜かれた反応", "夏油ではないと五条に見抜かれ、軽い調子で驚きながら脳を露出する。"),
    ("ch-072", 55, "夏油傑", "甚爾への怒り", "五条と理子を失った怒りを抑えず、甚爾を倒す意思を示す。"),
    ("ch-076", 56, "五条悟", "唯我独尊", "術式の核心へ到達し、自他の境界を越えた最強として甚爾を圧倒する。"),
    ("ch-150", 57, "禪院直哉", "人の心を問う皮肉", "一族を壊滅させる真希へ人の心を問うが、それまでの自分の行いが皮肉を際立たせる。"),
    ("ch-064", 58, "虎杖悠仁", "小沢をすぐ見抜く", "外見が大きく変わっていても、中学時代の小沢だとすぐに気づく。"),
    ("ch-181", 59, "秤金次", "漫画家への挑発", "理屈を並べるシャルルを挑発し、戦いの熱へ引きずり込む。"),
    ("ch-039", 60, "パンダ", "外見を気にしない", "自分はパンダなのだから、他人の外見を理由に態度を変えないと与幸吉へ示す。"),
    ("ch-033", 61, "東堂葵", "リアルタイムも録画も", "高田ちゃんの番組は生放送と録画の両方を見るのが当然だと会議を抜ける。"),
    ("ch-152", 62, "禪院直哉", "呪力を練れない最期", "呪力で傷を防げないまま母に刺され、真希を罵りながら死亡する。"),
]


SPEECH_MARKERS = re.compile(
    r"告げ|伝え|言い|話し|語り|問い|問う|答え|訴え|頼み|頼む|命じ|説き|"
    r"宣言|要求|求め|説明|明かし|示し|促し|拒み|挑発|呼びかけ|忠告"
)
DECISION_MARKERS = re.compile(
    r"決め|選び|選ぶ|判断|決意|覚悟|狙い|狙う|企て|決断|誓い|誓う|"
    r"受け入れ|認め|定め|切り替え"
)
MIND_MARKERS = re.compile(r"思い|思う|考え|悟り|悟る|理解|確信|疑い|恐れ|願い|願う|回想|振り返")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chapter_order(chapter_id: str):
    if chapter_id.startswith("zero-"):
        return int(chapter_id.split("-")[1]) - 10
    return int(chapter_id.split("-")[-1])


def latest_list(chapter, prefix, fallback=None):
    candidates = []
    for key, value in chapter.items():
        match = re.fullmatch(re.escape(prefix) + r"_phase(\d+)", key)
        if match and isinstance(value, list):
            candidates.append((int(match.group(1)), value))
    if not candidates:
        return list(fallback or [])
    return list(max(candidates)[1])


def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def comparison_key(text):
    text = clean_text(text)
    return re.sub(r"[「」『』（）()【】\[\]、。！？!?\s・：:―—…]", "", text)


def is_near_duplicate(left, right):
    left_key, right_key = comparison_key(left), comparison_key(right)
    if not left_key or not right_key:
        return True
    if left_key == right_key:
        return True
    shorter, longer = sorted((left_key, right_key), key=len)
    if len(shorter) >= 18 and shorter in longer and len(shorter) / len(longer) >= 0.72:
        return True
    return SequenceMatcher(None, left_key, right_key).ratio() >= 0.88


def unique_texts(items, limit=None):
    result = []
    for item in items:
        text = clean_text(item)
        if not text or any(is_near_duplicate(text, current) for current in result):
            continue
        result.append(text)
        if limit and len(result) >= limit:
            break
    return result


def split_sentences(text):
    normalized = clean_text(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？])", normalized)
    return [clean_text(part) for part in parts if clean_text(part)]


def classify_dialogue_summary(sentence):
    if SPEECH_MARKERS.search(sentence):
        return "セリフ要旨"
    if DECISION_MARKERS.search(sentence):
        return "判断・決意"
    if MIND_MARKERS.search(sentence):
        return "心情・認識"
    return "印象的な言動"


def latest_related_ids(chapter, prefix, fallback_key):
    values = latest_list(chapter, prefix, chapter.get(fallback_key, []))
    return [item for item in values if isinstance(item, str)]


def derive_keywords(chapter, popular_gists, technique_names, term_names):
    candidates = list(chapter.get("highlight_keywords", []))
    candidates.extend(item["label"] for item in popular_gists)

    summary = clean_text(chapter.get("summary_full", ""))
    for quoted in re.findall(r"「([^」]{2,24})」", summary):
        if not re.search(r"[。！？]", quoted):
            candidates.append(quoted)

    for pattern in (
        r"0\.2秒(?:だけ)?(?:の)?(?:領域展開)?",
        r"299秒(?:で)?(?:約)?千体",
        r"\d+分\d+秒",
        r"\d+(?:\.\d+)?秒",
        r"\d+点",
        r"\d+人",
        r"\d+体",
    ):
        candidates.extend(re.findall(pattern, summary))

    technique_ids = latest_related_ids(
        chapter, "technique_ids_verified", "technique_ids_candidate"
    )
    term_ids = latest_related_ids(chapter, "term_ids_verified", "term_ids_candidate")
    candidates.extend(technique_names[item] for item in technique_ids if item in technique_names)
    candidates.extend(term_names[item] for item in term_ids if item in term_names)
    candidates.extend(
        clean_text(item.get("text") if isinstance(item, dict) else item)
        for item in latest_list(chapter, "key_events_verified")
    )

    result = []
    for candidate in candidates:
        candidate = clean_text(candidate).strip(".,、。 ")
        if not candidate or len(candidate) > 30 or candidate in result:
            continue
        result.append(candidate)
        if len(result) >= 16:
            break
    return result


def build_chapter_record(
    chapter,
    popular_gists,
    crosschecked_lines,
    technique_names,
    term_names,
):
    verified_events = [
        clean_text(item.get("text") if isinstance(item, dict) else item)
        for item in latest_list(chapter, "key_events_verified")
    ]
    verified_events = unique_texts(verified_events)
    summary_sentences = split_sentences(chapter.get("summary_full", ""))

    detailed_events = []
    for event in verified_events:
        detailed_events.append(
            {"text": event, "level": "重要出来事", "basis": "verified-key-event"}
        )
    for sentence in summary_sentences:
        if any(is_near_duplicate(sentence, item["text"]) for item in detailed_events):
            continue
        detailed_events.append(
            {"text": sentence, "level": "場面経過", "basis": "summary-full-scene"}
        )

    dialogue_candidates = [
        sentence
        for sentence in summary_sentences
        if SPEECH_MARKERS.search(sentence)
        or DECISION_MARKERS.search(sentence)
        or MIND_MARKERS.search(sentence)
    ]
    # The first version exposed only three or four items per chapter, which made
    # dialogue-heavy chapters look almost empty. Keep every speech/decision/
    # recognition sentence, then fill with other notable scene sentences.
    for sentence in summary_sentences:
        if sentence not in dialogue_candidates:
            dialogue_candidates.append(sentence)
    dialogue_candidates = unique_texts(dialogue_candidates, limit=10)
    dialogue_summaries = [
        {
            "text": sentence,
            "kind": classify_dialogue_summary(sentence),
            "basis": "summary-full-paraphrase",
        }
        for sentence in dialogue_candidates
    ]

    popular_line_gists = [
        {
            "speaker": speaker,
            "label": label,
            "text": gist,
            "rank": rank,
            "kind": "名言要旨",
            "sourceRef": POPULAR_SOURCE_REF,
            "verification": "secondary-source-chapter-mapped",
        }
        for _, rank, speaker, label, gist in popular_gists
    ]

    return {
        "detailedEvents": detailed_events,
        "crosscheckedLines": crosschecked_lines,
        "dialogueSummaries": dialogue_summaries,
        "popularLineGists": popular_line_gists,
        "highlightKeywords": derive_keywords(
            chapter, popular_line_gists, technique_names, term_names
        ),
    }


def main():
    chapters = [read_json(path) for path in CHAPTER_DIR.glob("*.json")]
    chapters.sort(key=lambda item: chapter_order(item["id"]))
    techniques = read_json(SOURCE / "techniques.json")
    terms = read_json(SOURCE / "terms.json")
    technique_names = {item["id"]: item["name"] for item in techniques}
    term_names = {item["id"]: item["name"] for item in terms}
    line_evidence = (
        read_json(LINE_EVIDENCE)
        if LINE_EVIDENCE.exists()
        else {"chapters": {}, "sourceRefs": []}
    )
    line_evidence_by_chapter = line_evidence.get("chapters", {})

    popular_by_chapter = {}
    for item in POPULAR_LINE_GISTS:
        popular_by_chapter.setdefault(item[0], []).append(item)

    records = {
        chapter["id"]: build_chapter_record(
            chapter,
            popular_by_chapter.get(chapter["id"], []),
            line_evidence_by_chapter.get(chapter["id"], []),
            technique_names,
            term_names,
        )
        for chapter in chapters
    }
    payload = {
        "schemaVersion": 1,
        "scope": "manga-only",
        "policy": {
            "quotes": "長台詞を転載せず、既存の短い引用と名言要旨を分離する。",
            "events": "検証済み重要出来事と既存詳細あらすじの場面文を統合し、近似重複を除く。",
            "dialogueSummaries": "既存詳細あらすじから発言・判断・心情を抽出した要旨。",
            "crosscheckedLines": "異なる二つ以上の漫画記事系統で同一文字列を確認した短い作中語句・発言。話者は原作ページ直接監査まで表示しない。",
        },
        "sourceRefs": [
            POPULAR_SOURCE_REF,
            *line_evidence.get("sourceRefs", []),
        ],
        "counts": {
            "chapters": len(records),
            "detailedEvents": sum(len(item["detailedEvents"]) for item in records.values()),
            "dialogueSummaries": sum(
                len(item["dialogueSummaries"]) for item in records.values()
            ),
            "popularLineGists": sum(
                len(item["popularLineGists"]) for item in records.values()
            ),
            "crosscheckedLines": sum(
                len(item["crosscheckedLines"]) for item in records.values()
            ),
            "highlightKeywords": sum(
                len(item["highlightKeywords"]) for item in records.values()
            ),
        },
        "chapters": records,
    }
    write_json(OUTPUT, payload)
    print(
        "generated chapter highlights: "
        + ", ".join(f"{key}={value}" for key, value in payload["counts"].items())
    )


if __name__ == "__main__":
    main()
