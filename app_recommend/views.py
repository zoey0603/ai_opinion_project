from collections import Counter

from django.shortcuts import render

from app_news_db.models import NewsArticle


TASK_KEYWORDS = {
    "寫報告": ["報告", "寫作", "摘要", "整理", "文件", "研究", "論文"],
    "查資料": ["搜尋", "資料", "查詢", "知識", "資訊", "研究"],
    "寫程式": ["程式", "開發", "程式碼", "工程師", "除錯", "coding", "軟體"],
    "英文翻譯": ["翻譯", "英文", "語言", "多語", "rewrite"],
    "整理重點": ["摘要", "整理", "重點", "條列", "長文", "文件"],
}


def score_article(text, keywords):
    text = str(text).lower()
    return sum(1 for kw in keywords if kw.lower() in text)


def get_matched_keywords(text, keywords):
    text = str(text).lower()
    return [kw for kw in keywords if kw.lower() in text]


def recommend(request):
    task = request.GET.get("task", "")
    result = None

    if task in TASK_KEYWORDS:
        keywords = TASK_KEYWORDS[task]
        matched_articles = []

        for article in NewsArticle.objects.exclude(tool="Other").order_by("-date", "-created_at"):
            full_text = f"{article.title} {article.content} {article.keywords}"
            match_score = score_article(full_text, keywords)
            if match_score <= 0:
                continue
            matched_articles.append({
                "article": article,
                "match_score": match_score,
                "matched_keywords": get_matched_keywords(full_text, keywords),
            })

        if matched_articles:
            tool_counts = Counter(item["article"].tool for item in matched_articles)
            tool_scores = Counter()
            for item in matched_articles:
                tool_scores[item["article"].tool] += item["match_score"]

            ranking = []
            for tool in ["ChatGPT", "Gemini", "Claude"]:
                ranking.append({
                    "tool": tool,
                    "score": int(tool_scores.get(tool, 0)),
                    "count": int(tool_counts.get(tool, 0)),
                })

            ranking.sort(key=lambda x: (x["score"], x["count"]), reverse=True)
            best_tool = ranking[0]["tool"]

            best_news = [
                item for item in matched_articles
                if item["article"].tool == best_tool
            ]
            best_news.sort(key=lambda item: (item["match_score"], item["article"].date), reverse=True)

            news_examples = []
            for item in best_news[:5]:
                article = item["article"]
                news_examples.append({
                    "title": article.title,
                    "date": article.date,
                    "source": article.source,
                    "link": article.link,
                    "content_short": str(article.content or "")[:180],
                    "match_score": int(item["match_score"]),
                    "matched_keywords": item["matched_keywords"],
                    "tool": article.tool,
                })

            keyword_counter = Counter()
            for item in best_news:
                for kw in str(item["article"].keywords or "").split("|"):
                    kw = kw.strip()
                    if kw and kw not in keywords:
                        keyword_counter[kw] += 1

            related_keywords = [k for k, _ in keyword_counter.most_common(5)]
            best_tool_row = ranking[0]
            reason = (
                f"在與「{task}」相關的資料庫新聞中，{best_tool} 命中 {best_tool_row['count']} 篇，"
                f"累積關聯分數最高（{best_tool_row['score']} 分），"
                f"代表它在這類使用情境中被提及得最集中。"
            )

            result = {
                "task": task,
                "tool": best_tool,
                "reason": reason,
                "ranking": ranking,
                "related_keywords": related_keywords,
                "news_examples": news_examples,
            }
        else:
            result = {
                "task": task,
                "tool": "暫無明確結果",
                "reason": "目前資料庫中找不到和此需求高度相關的新聞，建議擴充資料或調整需求關鍵字。",
                "ranking": [],
                "related_keywords": [],
                "news_examples": [],
            }

    return render(request, "app_recommend/recommend.html", {
        "tasks": list(TASK_KEYWORDS.keys()),
        "task": task,
        "result": result,
    })
