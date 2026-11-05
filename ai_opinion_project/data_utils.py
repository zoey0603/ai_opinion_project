from pathlib import Path
from functools import lru_cache
from collections import Counter
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "ai_news_ready.csv"

@lru_cache(maxsize=1)
def load_news():
    df = pd.read_csv(DATA_PATH)

    # 先把中文日期格式轉成 pandas 看得懂的格式
    df["date"] = (
        df["date"]
        .fillna("")
        .astype(str)
        .str.replace(" 年 ", "-", regex=False)
        .str.replace(" 月 ", "-", regex=False)
        .str.replace(" 日 ", " ", regex=False)
        .str.replace(" 年", "-", regex=False)
        .str.replace(" 月", "-", regex=False)
        .str.replace(" 日", "", regex=False)
        .str.strip()
    )

    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d %H:%M", errors="coerce")

    df["tool"] = df["tool"].fillna("Other")
    df["sentiment"] = df["sentiment"].fillna("中性")
    df["keywords"] = df["keywords"].fillna("")

    return df

def get_tool_counts(df):
    counts = df["tool"].value_counts()
    return {
        "ChatGPT": int(counts.get("ChatGPT", 0)),
        "Gemini": int(counts.get("Gemini", 0)),
        "Claude": int(counts.get("Claude", 0)),
    }

def get_top_keywords(df, tool=None, topn=10):
    if tool and tool != "ALL":
        df = df[df["tool"] == tool]

    counter = Counter()
    for kw_str in df["keywords"].dropna():
        for kw in str(kw_str).split("|"):
            kw = kw.strip()
            if kw:
                counter[kw] += 1

    return counter.most_common(topn)

def get_trend_data(df):
    trend = (
        df.dropna(subset=["date"])
          .groupby([df["date"].dt.date, "tool"])
          .size()
          .unstack(fill_value=0)
          .sort_index()
    )
    return trend

def get_sentiment_counts(df):
    result = (
        df.groupby(["tool", "sentiment"])
          .size()
          .unstack(fill_value=0)
    )
    return result