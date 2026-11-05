from django.db.models import Count
from django.shortcuts import render

from app_news_db.models import NewsArticle
from .classifier import classify_text
from .models import ClassificationRecord


def home(request):
    result = None
    similar_news = []
    sample_article = NewsArticle.objects.exclude(tool="Other").order_by("-date", "-created_at").first()
    initial_title = ""
    initial_text = ""

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        input_text = request.POST.get("input_text", "").strip()
        if input_text or title:
            result = classify_text(title, input_text)
            ClassificationRecord.objects.create(
                title=title,
                input_text=input_text,
                predicted_tool=result["tool"],
                predicted_sentiment=result["sentiment"],
                predicted_topic=result["topic"],
                predicted_risk_type=result["risk_type"],
                keywords=result["keywords"],
                explanation=result["explanation"],
            )
            similar_qs = NewsArticle.objects.filter(tool=result["tool"]).order_by("-date", "-created_at")
            keyword_list = [item for item in result["keywords"].split("|") if item]
            if keyword_list:
                filtered = []
                for article in similar_qs[:80]:
                    haystack = f"{article.title} {article.keywords} {article.content[:300]}"
                    overlap = sum(1 for keyword in keyword_list if keyword in haystack)
                    if overlap:
                        filtered.append((overlap, article))
                filtered.sort(key=lambda item: item[0], reverse=True)
                similar_news = [article for _, article in filtered[:5]]
            else:
                similar_news = list(similar_qs[:5])
    elif sample_article:
        initial_title = sample_article.title
        initial_text = sample_article.content[:500]

    recent_records = ClassificationRecord.objects.order_by("-created_at")[:8]
    topic_rows = list(
        ClassificationRecord.objects.values("predicted_topic")
        .annotate(count=Count("id"))
        .order_by("-count", "predicted_topic")[:8]
    )
    return render(request, "app_text_classification/home.html", {
        "result": result,
        "similar_news": similar_news,
        "recent_records": recent_records,
        "topic_rows": topic_rows,
        "initial_title": initial_title,
        "initial_text": initial_text,
    })
