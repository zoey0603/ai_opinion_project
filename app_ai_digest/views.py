from django.db.models import Count
from django.shortcuts import render
from django.utils.dateparse import parse_date

from app_news_db.models import NewsArticle
from app_news_db.utils import call_ollama, collect_keyword_counts, fallback_digest
from .models import DigestReport


TOOLS = ["ALL", "ChatGPT", "Gemini", "Claude"]
REPORT_TYPE_LABELS = dict(DigestReport.REPORT_TYPES)


def _filter_news(tool, start_date, end_date):
    qs = NewsArticle.objects.exclude(tool="Other")
    if tool and tool != "ALL":
        qs = qs.filter(tool=tool)
    if start_date:
        qs = qs.filter(date__date__gte=start_date)
    if end_date:
        qs = qs.filter(date__date__lte=end_date)
    return qs.order_by("-date", "-created_at")


def _build_digest_prompt(context, report_type_label):
    return f"""
你是一位熟悉科技新聞與 AI 產業的輿情分析師。請用繁體中文，依照「{report_type_label}」格式生成內容。

分析條件：
- 工具：{context['tool_label']}
- 日期：{context['start_date'] or '不限'} 到 {context['end_date'] or '不限'}
- 總新聞篇數：{context['total_count']}
- 每日聲量：{context['daily_counts']}
- 情緒分布：{context['sentiment_counts']}
- 熱門關鍵字 Top 10：{context['top_keywords']}
- 代表新聞標題：{context['representative_titles']}

請讓內容適合期末專題展示，聚焦新聞聲量、情緒、熱門關鍵字、代表新聞與可觀察趨勢。
"""


def home(request):
    result = None
    error = ""
    representative_news = []
    latest_reports = DigestReport.objects.all()[:5]

    if request.method == "POST":
        tool = request.POST.get("tool", "ALL")
        report_type = request.POST.get("report_type", "5_points")
        start_date = parse_date(request.POST.get("start_date", "") or "")
        end_date = parse_date(request.POST.get("end_date", "") or "")
        news_qs = _filter_news(tool, start_date, end_date)
        total_count = news_qs.count()

        if total_count == 0:
            error = "目前查無資料，請調整工具或日期範圍。"
        else:
            daily_counts = list(
                news_qs.values("date__date").annotate(count=Count("id")).order_by("date__date")
            )
            sentiment_counts = {
                row["sentiment"] or "未標註": row["count"]
                for row in news_qs.values("sentiment").annotate(count=Count("id"))
            }
            top_keywords = collect_keyword_counts(news_qs, topn=10)
            representative_news = list(news_qs[:5])
            representative_titles = [item.title for item in representative_news]

            context = {
                "tool": tool,
                "tool_label": "全部工具" if tool == "ALL" else tool,
                "start_date": start_date,
                "end_date": end_date,
                "total_count": total_count,
                "daily_counts": [{"date": str(row["date__date"]), "count": row["count"]} for row in daily_counts],
                "sentiment_counts": sentiment_counts,
                "top_keywords": top_keywords,
                "representative_titles": representative_titles,
            }
            simple_context = {
                **context,
                "top_keywords": [kw for kw, _ in top_keywords],
            }

            try:
                digest_text = call_ollama(
                    _build_digest_prompt(simple_context, REPORT_TYPE_LABELS.get(report_type, report_type)),
                    timeout=360,
                )
                if not digest_text:
                    raise RuntimeError("Ollama 沒有回傳內容")
            except Exception as exc:
                digest_text = fallback_digest(simple_context)
                error = f"Ollama 暫時無法生成，已改用 fallback 懶人包：{exc}"

            saved_report = DigestReport.objects.create(
                tool=tool,
                start_date=start_date,
                end_date=end_date,
                report_type=report_type,
                total_count=total_count,
                digest_text=digest_text,
            )

            result = {
                "tool": context["tool_label"],
                "start_date": start_date,
                "end_date": end_date,
                "report_type": REPORT_TYPE_LABELS.get(report_type, report_type),
                "total_count": total_count,
                "daily_counts": context["daily_counts"],
                "sentiment_counts": sentiment_counts,
                "top_keywords": top_keywords,
                "digest_text": digest_text,
                "saved_report": saved_report,
            }
            latest_reports = DigestReport.objects.all()[:5]

    return render(request, "app_ai_digest/home.html", {
        "tools": TOOLS,
        "report_types": DigestReport.REPORT_TYPES,
        "result": result,
        "error": error,
        "representative_news": representative_news,
        "latest_reports": latest_reports,
    })


def history(request):
    return render(request, "app_ai_digest/history.html", {
        "reports": DigestReport.objects.all(),
    })
