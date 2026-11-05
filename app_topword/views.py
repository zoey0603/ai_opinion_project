import json
from collections import Counter

from django.shortcuts import render

from app_news_db.models import NewsArticle


def topword(request):
    tool = request.GET.get("tool", "ChatGPT")
    topn = request.GET.get("topn", "10")

    try:
        topn = max(5, min(int(topn), 100))
    except ValueError:
        topn = 10

    qs = NewsArticle.objects.exclude(tool="Other")
    if tool != "ALL":
        qs = qs.filter(tool=tool)

    counter = Counter()
    for article in qs.only("keywords"):
        for kw in str(article.keywords or "").split("|"):
            kw = kw.strip()
            if kw:
                counter[kw] += 1

    keyword_pairs = counter.most_common(topn)
    labels = [x[0] for x in keyword_pairs]
    values = [x[1] for x in keyword_pairs]

    context = {
        "tool": tool,
        "topn": topn,
        "labels": json.dumps(labels, ensure_ascii=False),
        "values": json.dumps(values, ensure_ascii=False),
        "keyword_pairs": keyword_pairs,
        "tools": ["ALL", "ChatGPT", "Gemini", "Claude"],
    }
    return render(request, "app_topword/topword.html", context)
