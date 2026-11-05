import json

from django.db.models import Count
from django.shortcuts import render

from app_news_db.models import NewsArticle


TOOLS = ["ChatGPT", "Gemini", "Claude"]


def trend(request):
    rows = (
        NewsArticle.objects
        .exclude(date__isnull=True)
        .values("date__date", "tool")
        .annotate(count=Count("id"))
        .order_by("date__date")
    )

    dates = sorted({row["date__date"] for row in rows if row["date__date"]})
    count_map = {
        (row["date__date"], row["tool"]): row["count"]
        for row in rows
    }

    labels = [str(day) for day in dates]
    chart_data = {
        tool: [count_map.get((day, tool), 0) for day in dates]
        for tool in TOOLS
    }

    selected_date = request.GET.get("date", "").strip()
    grouped_news = {tool: [] for tool in TOOLS}

    if selected_date:
        selected_qs = (
            NewsArticle.objects
            .filter(date__date=selected_date)
            .order_by("tool", "-date", "-created_at")
        )
        for article in selected_qs:
            article.content_short = (article.content or "")[:180]
            if article.tool in grouped_news:
                grouped_news[article.tool].append(article)

    context = {
        "labels": json.dumps(labels, ensure_ascii=False),
        "chatgpt": json.dumps(chart_data["ChatGPT"], ensure_ascii=False),
        "gemini": json.dumps(chart_data["Gemini"], ensure_ascii=False),
        "claude": json.dumps(chart_data["Claude"], ensure_ascii=False),
        "selected_date": selected_date,
        "grouped_news": grouped_news,
    }
    return render(request, "app_trend/trend.html", context)
