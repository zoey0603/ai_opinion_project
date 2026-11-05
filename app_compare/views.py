import json
from collections import Counter

from django.db.models import Count
from django.shortcuts import render

from app_news_db.models import NewsArticle


TOOLS = ["ChatGPT", "Gemini", "Claude"]


def _top_keywords(tool, topn=5):
    counter = Counter()
    for article in NewsArticle.objects.filter(tool=tool).only("keywords"):
        for kw in str(article.keywords or "").split("|"):
            kw = kw.strip()
            if kw:
                counter[kw] += 1
    return [kw for kw, _ in counter.most_common(topn)]


def compare(request):
    compare_rows = []
    for tool in TOOLS:
        qs = NewsArticle.objects.filter(tool=tool)
        count = qs.count()
        sentiment_counts = {
            row["sentiment"] or "未標註": row["count"]
            for row in qs.values("sentiment").annotate(count=Count("id"))
        }
        positive = int(sentiment_counts.get("正面", 0))
        neutral = int(sentiment_counts.get("中性", 0))
        negative = int(sentiment_counts.get("負面", 0))
        positive_rate = round((positive / count) * 100, 1) if count > 0 else 0
        negative_rate = round((negative / count) * 100, 1) if count > 0 else 0

        compare_rows.append({
            "tool": tool,
            "count": count,
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "positive_rate": positive_rate,
            "negative_rate": negative_rate,
            "top5": _top_keywords(tool, topn=5),
        })

    most_news_tool = max(compare_rows, key=lambda x: x["count"])
    most_positive_tool = max(compare_rows, key=lambda x: x["positive_rate"])
    most_negative_tool = max(compare_rows, key=lambda x: x["negative_rate"])

    context = {
        "compare_rows": compare_rows,
        "most_news_tool": most_news_tool,
        "most_positive_tool": most_positive_tool,
        "most_negative_tool": most_negative_tool,
        "count_labels": json.dumps([row["tool"] for row in compare_rows], ensure_ascii=False),
        "count_values": json.dumps([row["count"] for row in compare_rows], ensure_ascii=False),
        "positive_values": json.dumps([row["positive"] for row in compare_rows], ensure_ascii=False),
        "neutral_values": json.dumps([row["neutral"] for row in compare_rows], ensure_ascii=False),
        "negative_values": json.dumps([row["negative"] for row in compare_rows], ensure_ascii=False),
    }
    return render(request, "app_compare/compare.html", context)
