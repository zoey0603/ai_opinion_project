from collections import Counter

from app_news_db.utils import (
    classify_sentiment_rule,
    classify_tool,
    calculate_tool_relevance,
    extract_keywords_simple,
    find_risk_hits,
)


TOPIC_KEYWORDS = {
    "產品功能與模型發布": ["發布", "推出", "升級", "模型", "功能", "新增", "API", "整合", "支援", "生成式"],
    "企業合作與投資": ["合作", "投資", "收購", "策略", "夥伴", "企業", "導入", "商機", "資金", "估值"],
    "監管法律與版權": ["監管", "法規", "政府", "調查", "禁止", "罰款", "版權", "侵權", "著作權", "訴訟"],
    "資安隱私與濫用": ["資安", "安全", "漏洞", "攻擊", "詐騙", "假訊息", "隱私", "個資", "外洩", "濫用"],
    "市場營運與財務": ["營收", "獲利", "虧損", "裁員", "離職", "財報", "股價", "市場", "成本", "成長"],
    "研究技術與應用": ["研究", "技術", "訓練", "資料", "效能", "準確", "晶片", "算力", "開源", "應用"],
}


def classify_topic_rule(title, content):
    text_title = str(title or "")
    text_body = str(content or "")[:1200]
    scores = Counter()
    matched = {}
    for topic, words in TOPIC_KEYWORDS.items():
        hits = []
        for word in words:
            score = text_title.count(word) * 2 + text_body.count(word)
            if score:
                scores[topic] += score
                hits.append(word)
        if hits:
            matched[topic] = hits
    if not scores:
        return "其他科技新聞", {}, 0
    topic, score = scores.most_common(1)[0]
    return topic, matched, score


def classify_text(title, content):
    title = str(title or "").strip()
    content = str(content or "").strip()
    tool = classify_tool(title, content)
    sentiment = classify_sentiment_rule(title, content)
    keywords = extract_keywords_simple(title, content, topn=10)
    topic, topic_matches, topic_score = classify_topic_rule(title, content)
    risk_type_counts, risk_keywords = find_risk_hits(title, content)
    risk_type = max(risk_type_counts.items(), key=lambda item: item[1])[0] if risk_type_counts else "未命中風險詞"
    tool_relevance = {
        item: calculate_tool_relevance(title, content, item)
        for item in ["ChatGPT", "Gemini", "Claude"]
    }
    explanation_lines = [
        f"工具分類：依標題與內文前段的工具相關度判定為 {tool}。",
        f"情緒分類：使用科技新聞規則式正負詞庫，判定為 {sentiment}。",
        f"主題分類：最高分主題為 {topic}，分數 {topic_score}。",
        f"風險分類：{risk_type}。",
    ]
    return {
        "tool": tool,
        "sentiment": sentiment,
        "topic": topic,
        "topic_matches": topic_matches,
        "risk_type": risk_type,
        "risk_keywords": list(risk_keywords.keys()),
        "keywords": keywords,
        "tool_relevance": tool_relevance,
        "explanation": "\n".join(explanation_lines),
    }
