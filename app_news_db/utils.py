from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import re

import requests
from bs4 import BeautifulSoup
from django.core.management import call_command
from django.utils import timezone
from django.utils.dateparse import parse_datetime


POSITIVE_WORDS = [
    "推出", "發布", "升級", "強化", "成長", "提升", "合作", "投資", "突破", "創新",
    "獲利", "擴大", "改善", "支援", "領先", "整合", "開放", "新增", "優化", "成功",
    "採用", "導入", "擴展", "加速", "效率", "商機", "成效", "增長",
]

NEGATIVE_WORDS = [
    "下滑", "裁員", "離職", "爭議", "訴訟", "侵權", "風險", "監管", "禁止", "調查",
    "外洩", "漏洞", "錯誤", "失敗", "延遲", "幻覺", "不準確", "批評", "衝擊", "虧損",
    "撤換", "警告", "罰款", "危機", "濫用", "詐騙", "攻擊", "資安",
]

STOPWORDS = {
    "以及", "但是", "如果", "因為", "所以", "可以", "可能", "表示", "指出", "目前",
    "相關", "透過", "使用", "成為", "提供", "進行", "這個", "一個", "新聞", "科技",
    "今日", "報導", "公司", "市場", "更多", "人工", "智慧", "他們", "我們", "你們",
    "the", "and", "for", "with", "from", "that", "this", "will", "have", "has",
}

TECH_TERMS = [
    "ChatGPT", "OpenAI", "Gemini", "Claude", "Anthropic", "Google", "AI", "API",
    "模型", "搜尋", "企業", "晶片", "生成式", "機器人", "資料", "雲端", "安全", "監管",
    "版權", "隱私", "訴訟", "投資", "合作", "模型", "用戶", "功能", "工具", "平台",
]

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"
ALLOWED_TOOLS = {"ChatGPT", "Gemini", "Claude"}
TECHNEWS_BASE_URL = "https://technews.tw/category/ai/"
TOOL_TERMS = {
    "ChatGPT": ["chatgpt", "openai", "gpt-4", "gpt-4o", "gpt-5"],
    "Gemini": ["gemini"],
    "Claude": ["claude", "anthropic"],
}
OTHER_TOPIC_TERMS = [
    "nvidia", "輝達", "gpu", "晶片", "半導體", "台積電", "tsmc", "美光", "marvell",
    "android", "google 搜尋", "搜尋引擎", "創業", "創辦人", "人才", "離職", "裁員",
    "資料中心", "伺服器", "算力", "財報", "股價", "投資人",
]
NOISE_MARKERS = [
    "文章看完覺得有幫助",
    "請我們喝杯咖啡",
    "關鍵字:",
    "Post navigation",
    "從這裡可透過《Google 新聞》追蹤 TechNews",
    "我們偵測",
    "AD Block",
]


def _to_text(value):
    if value is None:
        return ""
    return str(value)


def classify_tool(title, content):
    scores = []
    for tool in ["ChatGPT", "Gemini", "Claude"]:
        relevance = calculate_tool_relevance(title, content, tool)
        if relevance["is_relevant"]:
            scores.append((relevance["relevance_score"], tool))

    if not scores:
        return "Other"
    scores.sort(reverse=True)
    return scores[0][1]


def calculate_tool_relevance(title, content, tool):
    title_text = _to_text(title).lower()
    content_text = _to_text(content).lower()
    content_front = content_text[:500]
    content_mid = content_text[:1200]
    content_full_short = content_text[:2500]
    terms = TOOL_TERMS.get(tool, [])
    matched_terms = []
    score = 0

    for term in terms:
        title_hits = title_text.count(term)
        front_hits = content_front.count(term)
        mid_hits = max(content_mid.count(term) - front_hits, 0)
        later_hits = max(content_full_short.count(term) - front_hits - mid_hits, 0)

        if title_hits or front_hits or mid_hits or later_hits:
            matched_terms.append(term)

        score += title_hits * 8
        score += front_hits * 3
        score += mid_hits * 1.5
        score += min(later_hits, 3) * 0.5

    other_topic_score = 0
    for term in OTHER_TOPIC_TERMS:
        if title_text.count(term):
            other_topic_score += 4
        elif content_front.count(term):
            other_topic_score += 1

    title_has_tool = any(title_text.count(term) for term in terms)
    front_hits_total = sum(content_front.count(term) for term in terms)
    mid_hits_total = sum(content_mid.count(term) for term in terms)
    total_hits = sum(content_full_short.count(term) for term in terms)

    is_relevant = False
    if title_has_tool and score >= 8:
        is_relevant = True
    elif front_hits_total >= 2 and score >= 6:
        is_relevant = True
    elif front_hits_total >= 1 and mid_hits_total >= 3 and score >= 7:
        is_relevant = True
    elif total_hits >= 5 and score >= 8:
        is_relevant = True

    if other_topic_score >= 4 and not title_has_tool and total_hits <= 1:
        is_relevant = False
    if total_hits == 1 and not title_has_tool and front_hits_total == 0:
        is_relevant = False

    return {
        "relevance_score": round(score - min(other_topic_score, 4), 2),
        "matched_terms": matched_terms,
        "is_relevant": is_relevant,
    }


def classify_sentiment_rule(title, content):
    title = _to_text(title)
    content_short = _to_text(content)[:1000]
    pos_score = 0
    neg_score = 0

    for word in POSITIVE_WORDS:
        pos_score += title.count(word) * 2
        pos_score += content_short.count(word)

    for word in NEGATIVE_WORDS:
        neg_score += title.count(word) * 2
        neg_score += content_short.count(word)

    if pos_score - neg_score >= 2:
        return "正面"
    if neg_score - pos_score >= 2:
        return "負面"
    return "中性"


def extract_keywords_simple(title, content, topn=10):
    text = f"{_to_text(title)} {_to_text(content)[:1200]}"
    tokens = []
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9.+_-]{1,}", text))
    tokens.extend(re.findall(r"[\u4e00-\u9fff]{2,}", text))

    counter = Counter()
    for token in tokens:
        token = token.strip()
        if not token or token in STOPWORDS or token.isdigit():
            continue
        if re.fullmatch(r"\W+", token):
            continue
        if len(token) < 2:
            continue
        if token in TECH_TERMS or re.search(r"[A-Za-z]", token) or len(token) <= 8:
            counter[token] += 1

    return "|".join([word for word, _ in counter.most_common(topn)])


def call_ollama(prompt, model_name=None, timeout=360):
    payload = {
        "model": model_name or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def fallback_digest(context):
    keywords = ", ".join(context.get("top_keywords", [])) or "暫無明顯關鍵字"
    titles = context.get("representative_titles", [])
    title_text = "\n".join([f"- {title}" for title in titles]) or "- 目前查無代表新聞"
    return (
        f"本期間共蒐集 {context.get('total_count', 0)} 篇新聞。"
        f"熱門關鍵字包含 {keywords}，可看出媒體關注焦點集中在近期 AI 工具的產品、企業與風險議題。\n\n"
        f"代表新聞：\n{title_text}\n\n"
        "綜合觀察：建議持續追蹤聲量變化、負面新聞比例與高頻風險詞，作為後續輿情判讀依據。"
    )


def fallback_risk_summary(results):
    if not results:
        return "目前查無資料，暫時無法形成風險摘要。"
    highest = max(results, key=lambda item: item.get("risk_score", 0))
    return (
        f"目前風險分數最高的是 {highest.get('tool')}，主要風險類別為"
        f"{highest.get('main_risk_type', '未明確')}。建議優先觀察負面新聞、監管詞與安全詞是否持續增加。"
    )


def fallback_hot_event(event):
    keywords = event.get("top_keywords") or "暫無明顯關鍵字"
    return (
        f"此日聲量上升可能與代表新聞中出現的主題有關，熱門關鍵字包含 {keywords}，"
        f"顯示媒體關注焦點集中於 {keywords.split('|')[0] if isinstance(keywords, str) else keywords}。"
    )


def clean_article_text(text):
    cleaned = _to_text(text)
    for marker in NOISE_MARKERS:
        idx = cleaned.find(marker)
        if idx >= 0:
            cleaned = cleaned[:idx]
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_technews_date(soup):
    time_tag = soup.select_one("time[datetime]")
    if time_tag and time_tag.get("datetime"):
        parsed = parse_datetime(time_tag["datetime"])
        if parsed:
            return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)

    text = soup.get_text(" ", strip=True)
    match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(\d{1,2}):(\d{2})", text)
    if match:
        y, m, d, hh, mm = [int(x) for x in match.groups()]
        return timezone.make_aware(datetime(y, m, d, hh, mm))
    return timezone.now()


def fetch_article(url, session=None):
    session = session or requests.Session()
    response = session.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    content_node = None
    for selector in [
        "div.entry-content",
        "article .entry-content",
        "div.post-content",
        "div.single-post-content",
        "article",
    ]:
        content_node = soup.select_one(selector)
        if content_node:
            break

    paragraphs = []
    if content_node:
        for p in content_node.select("p"):
            text = p.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)

    return {
        "date": parse_technews_date(soup),
        "source": "TechNews 科技新報",
        "content": clean_article_text("\n".join(paragraphs)),
    }


def fetch_technews_ai_pages(start_page=1, end_page=10, start_date=None, end_date=None, stop_before_start=False):
    session = requests.Session()
    items = []
    seen_links = set()
    start_date = start_date
    end_date = end_date

    for page in range(start_page, end_page + 1):
        list_url = TECHNEWS_BASE_URL if page == 1 else f"{TECHNEWS_BASE_URL}page/{page}/"
        response = session.get(list_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        page_dates = []

        for link_node in soup.select("td.maintitle h1.entry-title a"):
            title = link_node.get_text(" ", strip=True)
            link = link_node.get("href", "").strip()
            if not title or not link or link in seen_links:
                continue
            seen_links.add(link)

            article = fetch_article(link, session=session)
            article_date = timezone.localtime(article["date"]).date() if article["date"] else None
            if article_date:
                page_dates.append(article_date)
            if start_date and article_date and article_date < start_date:
                continue
            if end_date and article_date and article_date > end_date:
                continue

            tool = classify_tool(title, article["content"])
            items.append({
                "title": title,
                "link": link,
                "date": article["date"],
                "source": article["source"],
                "content": article["content"],
                "tool": tool,
                "sentiment": classify_sentiment_rule(title, article["content"]),
                "keywords": extract_keywords_simple(title, article["content"]),
            })

        if stop_before_start and start_date and page_dates and max(page_dates) < start_date:
            break

    return items


def month_date_range(year, month):
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def update_technews_ai(start_page=1, end_page=36, start_date=None, end_date=None, stop_before_start=False):
    from app_news_db.models import NewsArticle

    imported = 0
    updated = 0
    unchanged = 0
    items = fetch_technews_ai_pages(
        start_page=start_page,
        end_page=end_page,
        start_date=start_date,
        end_date=end_date,
        stop_before_start=stop_before_start,
    )
    for item in items:
        existing = NewsArticle.objects.filter(link=item["link"]).first()
        defaults = {
            "title": item["title"],
            "date": item["date"],
            "source": item["source"],
            "content": item["content"],
            "tool": item["tool"],
            "sentiment": item["sentiment"],
            "keywords": item["keywords"],
        }
        if existing is None:
            NewsArticle.objects.create(link=item["link"], **defaults)
            imported += 1
            continue

        changed_fields = []
        for field, value in defaults.items():
            if getattr(existing, field) != value:
                setattr(existing, field, value)
                changed_fields.append(field)

        if changed_fields:
            existing.save(update_fields=changed_fields)
            updated += 1
        else:
            unchanged += 1

    return {
        "fetched": len(items),
        "imported": imported,
        "updated": updated,
        "unchanged": unchanged,
        "message": f"抓取 {len(items)} 筆，新增 {imported} 筆，更新 {updated} 筆，未變更 {unchanged} 筆。",
    }


def ensure_news_updated_today(start_page=1, end_page=1):
    from app_news_db.models import DataUpdateLog

    today = timezone.localdate()
    latest_success = (
        DataUpdateLog.objects
        .filter(name="technews_ai", status="success")
        .order_by("-last_updated", "-created_at")
        .first()
    )

    if latest_success and latest_success.last_updated and timezone.localtime(latest_success.last_updated).date() == today:
        return latest_success

    latest_log = DataUpdateLog.objects.filter(name="technews_ai").order_by("-created_at").first()
    if latest_log and latest_log.last_updated and timezone.localtime(latest_log.last_updated).date() == today:
        if latest_log.status == "failed":
            return latest_log

    try:
        call_command("update_news", start_page=start_page, end_page=end_page)
        latest = DataUpdateLog.objects.filter(name="technews_ai").order_by("-created_at").first()
        return latest
    except Exception as exc:
        return DataUpdateLog.objects.create(
            name="technews_ai",
            last_updated=timezone.now(),
            status="failed",
            message=f"自動更新失敗，已保留既有資料：{exc}",
        )


def collect_keyword_counts(news_qs, topn=10):
    counter = Counter()
    for article in news_qs:
        for keyword in _to_text(article.keywords).split("|"):
            keyword = keyword.strip()
            if keyword:
                counter[keyword] += 1
    return counter.most_common(topn)


def find_risk_hits(title, content):
    from app_risk_alert.risk_keywords import RISK_WORDS_BY_TYPE

    text = f"{_to_text(title)} {_to_text(content)[:1000]}".lower()
    type_counts = defaultdict(int)
    keywords = Counter()
    for risk_type, words in RISK_WORDS_BY_TYPE.items():
        for word in words:
            count = text.count(word.lower())
            if count:
                type_counts[risk_type] += count
                keywords[word] += count
    return dict(type_counts), keywords
