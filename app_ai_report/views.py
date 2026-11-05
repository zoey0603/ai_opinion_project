from collections import Counter

from django.shortcuts import render, redirect
from django.db.models import Count
from django.utils.dateparse import parse_date

from app_news_db.models import NewsArticle
from app_news_db.utils import call_ollama, fallback_digest
from .models import AnalysisReport


def home(request):
    reports = AnalysisReport.objects.all().order_by('-created_at')[:10]

    context = {
        "tools": ["ChatGPT", "Gemini", "Claude", "ALL"],
        "reports": reports,
    }
    return render(request, "app_ai_report/home.html", context)


def generate_report(request):
    if request.method != "POST":
        return redirect("app_ai_report:home")

    tool = request.POST.get("tool", "ALL").strip()
    start_date_str = request.POST.get("start_date", "").strip()
    end_date_str = request.POST.get("end_date", "").strip()

    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    news_qs = NewsArticle.objects.exclude(tool="Other")

    if tool != "ALL":
        news_qs = news_qs.filter(tool__iexact=tool)

    if start_date:
        news_qs = news_qs.filter(date__date__gte=start_date)
    if end_date:
        news_qs = news_qs.filter(date__date__lte=end_date)

    news_qs = news_qs.order_by("-date")

    total_count = news_qs.count()

    if total_count == 0:
        context = {
            "error": "查無符合條件的新聞資料，請重新選擇條件。",
            "tools": ["ChatGPT", "Gemini", "Claude", "ALL"],
            "reports": AnalysisReport.objects.all().order_by('-created_at')[:10],
        }
        return render(request, "app_ai_report/home.html", context)

    # 每日聲量
    daily_counts_qs = (
        news_qs
        .values("date__date")
        .annotate(count=Count("id"))
        .order_by("date__date")
    )
    daily_counts = [
        {"date": str(item["date__date"]), "count": item["count"]}
        for item in daily_counts_qs
    ]

    # 情緒分布
    sentiment_qs = (
        news_qs
        .values("sentiment")
        .annotate(count=Count("id"))
        .order_by()
    )
    sentiment_counts = {item["sentiment"]: item["count"] for item in sentiment_qs}

    # 熱門關鍵字
    keyword_counter = Counter()
    for item in news_qs:
        for kw in str(item.keywords).split("|"):
            kw = kw.strip()
            if kw:
                keyword_counter[kw] += 1
    top_keywords = keyword_counter.most_common(10)

    # 代表新聞
    top_news = list(news_qs[:5])
    top_titles = [n.title for n in top_news]

    selected_tool_name = "全部工具" if tool == "ALL" else tool

    system_prompt = (
        "你是一位專業的新聞輿情分析師。"
        "請根據提供的新聞統計資料，使用繁體中文撰寫一份結構清楚、專業、適合課堂報告展示的分析報告。"
        "請使用 Markdown 格式。"
    )

    user_prompt = f"""
請分析以下新聞資料，主題為：{selected_tool_name}

分析條件：
- 工具：{selected_tool_name}
- 起始日期：{start_date if start_date else '未限制'}
- 結束日期：{end_date if end_date else '未限制'}
- 總新聞篇數：{total_count}

一、每日聲量趨勢：
{daily_counts}

二、情緒分布：
{sentiment_counts}

三、熱門關鍵字 Top 10：
{top_keywords}

四、代表新聞標題：
{top_titles}

請輸出一份至少 500 字的專業分析報告，內容至少包含：
1. 標題
2. 摘要
3. 聲量分析
4. 情緒分析
5. 關鍵字分析
6. 綜合觀察
7. 建議
8. 總結
"""

    error = ""
    try:
        report_text = call_ollama(f"{system_prompt}\n\n{user_prompt}", timeout=360)
        if not report_text:
            raise RuntimeError("Ollama 沒有回傳報告內容")
    except Exception as e:
        report_text = fallback_digest({
            "total_count": total_count,
            "top_keywords": [kw for kw, _ in top_keywords],
            "representative_titles": top_titles,
        })
        error = f"Ollama 暫時無法生成，已改用 fallback 報告：{e}"

    saved_report = AnalysisReport.objects.create(
        tool=tool,
        start_date=start_date,
        end_date=end_date,
        total_count=total_count,
        report=report_text
    )

    context = {
        "tools": ["ChatGPT", "Gemini", "Claude", "ALL"],
        "generated": True,
        "selected_tool": selected_tool_name,
        "start_date": start_date,
        "end_date": end_date,
        "total_count": total_count,
        "daily_counts": daily_counts,
        "sentiment_counts": sentiment_counts,
        "top_keywords": top_keywords,
        "top_titles": top_titles,
        "report_text": report_text,
        "error": error,
        "saved_report": saved_report,
        "reports": AnalysisReport.objects.all().order_by('-created_at')[:10],
    }
    return render(request, "app_ai_report/home.html", context)


def history(request):
    reports = AnalysisReport.objects.all().order_by('-created_at')

    return render(request, "app_ai_report/history.html", {
        "reports": reports
    })
