from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from .models import DataUpdateLog, NewsArticle


def news_db(request):
    tool = request.GET.get("tool", "ALL").strip()
    sentiment = request.GET.get("sentiment", "ALL").strip()
    keyword = request.GET.get("keyword", "").strip()
    start_date = parse_date(request.GET.get("start_date", "") or "")
    end_date = parse_date(request.GET.get("end_date", "") or "")

    qs = NewsArticle.objects.all().order_by("-date", "-created_at")
    if tool != "ALL":
        qs = qs.filter(tool=tool)
    if sentiment != "ALL":
        qs = qs.filter(sentiment=sentiment)
    if keyword:
        qs = qs.filter(
            Q(title__icontains=keyword) |
            Q(content__icontains=keyword) |
            Q(keywords__icontains=keyword)
        )
    if start_date:
        qs = qs.filter(date__date__gte=start_date)
    if end_date:
        qs = qs.filter(date__date__lte=end_date)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    tool_counts = {
        item["tool"]: item["count"]
        for item in NewsArticle.objects.values("tool").annotate(count=Count("id"))
    }
    latest_log = DataUpdateLog.objects.order_by("-created_at").first()

    return render(request, "app_news_db/news_db.html", {
        "page_obj": page_obj,
        "total_count": qs.count(),
        "all_count": NewsArticle.objects.count(),
        "tool_counts": tool_counts,
        "latest_log": latest_log,
        "tools": ["ALL", "ChatGPT", "Gemini", "Claude"],
        "sentiments": ["ALL", "正面", "中性", "負面"],
        "selected_tool": tool,
        "selected_sentiment": sentiment,
        "keyword": keyword,
        "start_date": start_date,
        "end_date": end_date,
    })
