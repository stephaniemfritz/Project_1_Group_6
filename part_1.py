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
import scipy.stats as st
import statsmodels.api as sm
from statsmodels.stats.proportion import proportions_ztest

# Set up SerpAPI key to get the news from google
SERPAPI_KEY = ""

# get the news
def fetch_google_news(query="Deepseek AI", num_results=100, start_date="01/01/2025", end_date="02/03/2025"):
    news_df=pd.DataFrame()
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "tbm": "nws",
        "num": num_results,
        "tbs": f"cdr:1,cd_min:{start_date},cd_max:{end_date}",
    }
    for i in range(50):
        try:
            params['offset']=i*100
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
            news_df = pd.concat([news_df,pd.DataFrame(articles)])

            # Save JSON & CSV

        except requests.exceptions.RequestException as e:
            print(f" Error: Failed to fetch news - {e}")
            return None
    news_df.to_csv("deepseek_news.csv", index=False)
    with open("news_data.json", "w", encoding="utf-8") as json_file:
        json.dump(results, json_file, indent=4)

        print(f" News data saved ({len(news_df)} articles).")
    return news_df if not news_df.empty else None



# Convert relative dates to actual dates
def convert_relative_date(date_str):
    if isinstance(date_str, str):
        match = re.search(r"(\d+)\s+(day|week|month|hour|minute|second)", date_str)
        if match:
            value, unit = int(match.group(1)), match.group(2)
            delta = {
                "day": datetime.timedelta(days=value),
                "week": datetime.timedelta(weeks=value),
                "month": datetime.timedelta(days=value * 30),
                "hour": datetime.timedelta(hours=value),
                "minute": datetime.timedelta(minutes=value),
                "second": datetime.timedelta(seconds=value),
            }
            return datetime.datetime.today() - delta.get(unit, datetime.timedelta(days=0))
        try:
            return parser.parse(date_str)
        except ValueError:
            return None
    return date_str


# Sentiment Analysis Function
def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    vs = analyzer.polarity_scores(str(text))
    return "Positive" if vs['compound'] >= 0.05 else "Negative" if vs['compound'] <= -0.05 else "Neutral"


# Get the stock data
def fetch_stock_data(tickers=["GOOGL", "MSFT", "NVDA", "META"], start_date="2023-01-01"):
    end_date = datetime.datetime.today().strftime('%Y-%m-%d')
    stock_data = {}

    for ticker in tickers:
        try:
            stock_df = yf.download(ticker, start=start_date, end=end_date)
            if not stock_df.empty:
                stock_df.reset_index(inplace=True)
                stock_df.to_csv(f"{ticker}_stock_data.csv", index=False)
                stock_data[ticker] = stock_df
                print(f" Stock data saved: {ticker} ({len(stock_df)} records).")
        except Exception as e:
            print(f" Error fetching stock data for {ticker}: {e}")

    return stock_data


# Execution:
news_df = fetch_google_news()

if news_df is not None:
    news_df["published_date"] = news_df["published_date"].apply(convert_relative_date)
    news_df["published_date"] = pd.to_datetime(news_df["published_date"], errors="coerce")
    news_df.dropna(subset=["published_date"], inplace=True)

    # Do the  sentiment analysis
    news_df["sentiment"] = news_df["title"].apply(analyze_sentiment)
    news_df.to_csv("deepseek_news_with_sentiment.csv", index=False)
    print("Sentiment analysis completed and saved.")

# Get the stock data
stock_data = fetch_stock_data()


# make sentiment Pie Charts by week
def generate_sentiment_charts(file_path="deepseek_news_with_sentiment.csv"):
    df = pd.read_csv(file_path)
     # Convert date columns
    df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce")
    df.dropna(subset=["published_date"], inplace=True)

    # get year and week number
    df["year_week"] = df["published_date"].dt.strftime("%Y-W%U")

    # Group by week and count sentiment count
    weekly_sentiment = df.groupby(["year_week", "sentiment"]).size().unstack(fill_value=0)
    weekly_sentiment.to_csv('Weekly Sentiment Numbers.csv')
    # Create output directory
    output_dir = "weekly_sentiment_charts"
    os.makedirs(output_dir, exist_ok=True)

    # make pie charts
    for week, data in weekly_sentiment.iterrows():
        plt.figure(figsize=(6, 6))
        data.plot.pie(autopct='%1.1f%%', startangle=140, cmap="coolwarm", legend=False)
        plt.title(f"Sentiment Distribution for Week {week}")
        plt.ylabel("")
        plt.savefig(f"{output_dir}/sentiment_week_{week}.png")
        plt.close()
        print(f" Pie chart created for {week}")

    print("\nAll weekly sentiment charts have been generated and saved!")
    return weekly_sentiment


# Run Sentiment Chart
weekly_sentiment=generate_sentiment_charts()


# Resaserch question # 1. AI stock vs. Nasdaq Composite Index
tickers = {
    "GOOGL": "Google",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "META": "Meta",
     "IBM": "IBM",
      "AAPL":"Apple",
       "T": "AT&T",
    "^IXIC": "Nasdaq Composite"  # Nasdaq Composite Index
}

# Define the date range (past two years)
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=2*365)


# Get stock data
stock_data = {}
for ticker, name in tickers.items():
    try:
        data = yf.download(ticker, start=start_date, end=end_date)
        if not data.empty:
            # Use 'Adj Close' if available, otherwise use 'Close'
            stock_data[ticker] = data["Adj Close"] if "Adj Close" in data else data["Close"]
            print(f" Fetched data for {name} ({ticker})")
        else:
            print(f" No data found for {name} ({ticker})")
    except Exception as e:
        print(f" Error fetching data for {name} ({ticker}): {e}")

# Normalize stock
normalized_data = {}
for ticker, prices in stock_data.items():
    normalized_data[ticker] = (prices / prices.iloc[0]) * 100  # Normalize to starting price

# Plot the data
plt.figure(figsize=(12, 6))
for ticker, prices in normalized_data.items():
    plt.plot(prices, label=tickers[ticker])

plt.title("Stock Price Performance of AI Tech Companies vs Nasdaq Composite (Past 2 Years)")
plt.xlabel("Date")
plt.ylabel("Normalized Price (Starting Price = 100)")
plt.legend(loc="upper left")
plt.grid(True)
plt.show()
print(weekly_sentiment)
neutrals=[weekly_sentiment.loc['2025-W03','Neutral'],weekly_sentiment.loc['2025-W04','Neutral']]
totals=[weekly_sentiment.loc['2025-W03'].sum(),weekly_sentiment.loc['2025-W04'].sum()]
print('The p-value that the proportion of articles that were neutral about the issue of AI is higher in week 4 than in week three is '+str( proportions_ztest(neutrals,totals,alternative='smaller')[1]))
neutrals=[weekly_sentiment.loc['2025-W04','Neutral'],weekly_sentiment.loc['2025-W05','Neutral']]
totals=[weekly_sentiment.loc['2025-W04'].sum(),weekly_sentiment.loc['2025-W05'].sum()]
print('The p-value that the proportion of articles that were neutral about the issue of AI is higher in week 5 than in week 4 is '+str( proportions_ztest(neutrals,totals,alternative='smaller')[1]))
