import os
import pandas as pd
import requests
import yfinance as yf
import datetime
import re
from dateutil import parser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import json
import matplotlib.pyplot as plt

# Set up SerpAPI Key
SERPAPI_KEY = ""


# Step 1: Fetch News via SerpAPI
def fetch_google_news(query="Deepseek AI", num_results=200, start_date="01/01/2025", end_date="02/03/2025"):
    """Fetches news articles using SerpApi (Google News API)."""
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "tbm": "nws",
        "num": num_results,
        "tbs": f"cdr:1,cd_min:{start_date},cd_max:{end_date}",
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()
        results = response.json()
        articles = []
        if "news_results" in results:
            for news in results["news_results"]:
                articles.append({
                    "title": news.get("title"),
                    "link": news.get("link"),
                    "source": news.get("source"),
                    "published_date": news.get("date"),
                    "snippet": news.get("snippet"),
                })

        # Convert to DataFrame
        news_df = pd.DataFrame(articles)

        # Save JSON & CSV
        with open("news_data.json", "w", encoding="utf-8") as json_file:
            json.dump(results, json_file, indent=4)
        if not news_df.empty:
            news_df.to_csv("deepseek_news.csv", index=False)
            print("News data saved to deepseek_news.csv and news_data.json")
            return news_df, start_date, end_date  # Return DataFrame & Date Range
        else:
            print("⚠ No news articles found.")
            return None, start_date, end_date

    except requests.exceptions.RequestException as e:
        print(f" Error: Failed to fetch news - {e}")
        return None, start_date, end_date


# Step 2: Convert Relative Dates to Actua
def convert_relative_date(date_str): # Converts relative date strings like '1 week ago' to actual dates
    if isinstance(date_str, str):
        match = re.search(r"(\d+)\s+(day|week|month|hour|minute|second)", date_str)
        if match:
            value, unit = int(match.group(1)), match.group(2)
            if "day" in unit:
                return datetime.datetime.today() - datetime.timedelta(days=value)
            elif "week" in unit:
                return datetime.datetime.today() - datetime.timedelta(weeks=value)
            elif "month" in unit:
                return datetime.datetime.today() - datetime.timedelta(days=value * 30)
            elif "hour" in unit:
                return datetime.datetime.today() - datetime.timedelta(hours=value)
            elif "minute" in unit:
                return datetime.datetime.today() - datetime.timedelta(minutes=value)
            elif "second" in unit:
                return datetime.datetime.today() - datetime.timedelta(seconds=value)
        else:
            try:
                return parser.parse(date_str)
            except Exception:
                return None
    return date_str


# Step 3: Apply Sentiment Analysis
def analyze_sentiment(text):
    """Analyzes sentiment using VADER sentiment analysis."""
    analyzer = SentimentIntensityAnalyzer()
    vs = analyzer.polarity_scores(str(text))
    if vs['compound'] >= 0.05:
        return "Positive"
    elif vs['compound'] <= -0.05:
        return "Negative"
    else:
        return "Neutral"


# Step 4: Fetch Stock Data via Yahoo Finance API
def fetch_stock_data(tickers=["GOOGL", "MSFT", "NVDA", "META"], start_date="2025-01-01"):
    """Fetches stock data for AI-related companies using Yahoo Finance API."""
    end_date = datetime.datetime.today().strftime('%Y-%m-%d')

    stock_data = {}
    for ticker in tickers:
        try:
            stock_df = yf.download(ticker, start=start_date, end=end_date)
            stock_df.reset_index(inplace=True)
            stock_df.to_csv(f"{ticker}_stock_data.csv", index=False)
            stock_data[ticker] = stock_df
        except Exception as e:
            print(f" Error fetching stock data for {ticker}: {e}")

    print("\n Stock data fetching completed. CSV files saved.")
    return stock_data


# **Execution: Fetch News & Process Sentiment**
news_df, start_date, end_date = fetch_google_news(start_date="01/01/2025", end_date="02/03/2025")

if news_df is not None:
    # Convert relative dates
    news_df["published_date"] = news_df["published_date"].apply(convert_relative_date)
    news_df["published_date"] = pd.to_datetime(news_df["published_date"], errors='coerce')
    news_df.dropna(subset=["published_date"], inplace=True)

    # Apply sentiment analysis before saving
    news_df["sentiment"] = news_df["title"].apply(analyze_sentiment)
    news_df.to_csv("deepseek_news_with_sentiment.csv", index=False)
    print(" Sentiment analysis completed and saved to deepseek_news_with_sentiment.csv")

# Fetch Stock Data
stock_data = fetch_stock_data()


# **Step 5: Generate Weekly Sentiment Pie Charts**
file_path = "deepseek_news_with_sentiment.csv"
df = pd.read_csv(file_path)

# Convert published_date to datetime format
df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
df.dropna(subset=["published_date"], inplace=True)

# Convert string start/end dates to datetime
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# Filter data within the specified range
df = df[(df["published_date"] >= start_date) & (df["published_date"] <= end_date)]

# Extract year and week number
df["year_week"] = df["published_date"].dt.strftime("%Y-W%U")

# Group by week and count sentiment occurrences
weekly_sentiment = df.groupby(["year_week", "sentiment"]).size().unstack(fill_value=0)

# Create output directory for pie charts
output_dir = "weekly_sentiment_charts"
os.makedirs(output_dir, exist_ok=True)

# Generate and save a pie chart for each week
for week, data in weekly_sentiment.iterrows():
    plt.figure(figsize=(6, 6))
    data.plot.pie(autopct='%1.1f%%', startangle=140, cmap="coolwarm", legend=False)
    plt.title(f"Sentiment Distribution for Week {week}")
    plt.ylabel("")
    plt.savefig(f"{output_dir}/sentiment_week_{week}.png")
    plt.close()
    print(f" Pie chart created for {week} (Data: {data.to_dict()})")
print("\n All weekly sentiment charts have been generated and saved!")


