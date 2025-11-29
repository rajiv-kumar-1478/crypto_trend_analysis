from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import os
from collections import Counter
import re

app = Flask(__name__)
CORS(app)

CSV_FOLDER = 'Data'  # Adjust this to match your folder path

# Load and normalize all CSV files
def load_all_data():
    all_data = []

    for coin_file in os.listdir(CSV_FOLDER):
        if coin_file.endswith('.csv'):
            file_path = os.path.join(CSV_FOLDER, coin_file)
            try:
                coin_df = pd.read_csv(file_path, encoding='utf-8-sig')
                coin_df.columns = coin_df.columns.str.strip().str.lower()

                required = {'date', 'polarity', 'sentiment', 'close_price_next_day_minus_same_day'}
                if not required.issubset(set(coin_df.columns)):
                    print(f"Skipping {coin_file}, missing columns: {required - set(coin_df.columns)}")
                    continue

                coin_df['tag'] = coin_file.split('.')[0]  # Add coin name tag
                all_data.append(coin_df)
            except Exception as e:
                print(f"Error loading {coin_file}: {e}")

    if all_data:
        df = pd.concat(all_data, ignore_index=True)
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])

        # Normalize sentiment: keep -1 to 1 range
        sentiment_abs_max = max(abs(df['polarity'].min()), abs(df['polarity'].max()))
        df['normalized_sentiment'] = df['polarity'] / sentiment_abs_max

        # Normalize price (0 to 1)
        price_min = df['close_price_next_day_minus_same_day'].min()
        price_max = df['close_price_next_day_minus_same_day'].max()
        df['close_price_next_day_minus_same_day'] = (df['close_price_next_day_minus_same_day'] - price_min) / (price_max - price_min)

        return df
    else:
        raise ValueError("No valid CSV files found")

try:
    df = load_all_data()
except Exception as e:
    print(f"Error loading data: {e}")
    df = pd.DataFrame()


@app.route('/api/sentiment', methods=['GET'])
def get_sentiment_data():
    if df.empty:
        return jsonify({"error": "Data not loaded correctly"}), 500

    coin = request.args.get('coin', 'bitcoin').lower()
    days = int(request.args.get('days', 7))

    filtered = df[df['tag'].str.lower() == coin].copy()
    latest_date = filtered['date'].max()

    if pd.isnull(latest_date):
        return jsonify({
            "labels": [],
            "sentimentScores": [],
            "positiveCounts": [],
            "negativeCounts": [],
            "neutralCounts": [],
            "priceChanges": [],
            "topPositive": [],
            "topNegative": []
        })

    start_date = latest_date - pd.Timedelta(days=days)
    filtered = filtered[filtered['date'] >= start_date]

    # Normalize sentiment
    filtered['normalized_sentiment'] = filtered['polarity']

    # Normalize price changes to [-1, 1]
    price_min = filtered['close_price_next_day_minus_same_day'].min()
    price_max = filtered['close_price_next_day_minus_same_day'].max()

    if price_max != price_min:
        filtered['close_price_next_day_minus_same_day'] = 2 * (
            (filtered['close_price_next_day_minus_same_day'] - price_min) / (price_max - price_min)
        ) - 1
    else:
        filtered['close_price_next_day_minus_same_day'] = 0

    # Daily averages
    daily_sentiment = filtered.groupby('date')['normalized_sentiment'].mean().reset_index()
    daily_sentiment['date'] = daily_sentiment['date'].astype(str) # Include year

    daily_price_change = filtered.groupby('date')['close_price_next_day_minus_same_day'].mean().reset_index()
    daily_price_change['date'] = daily_price_change['date'].astype(str)  # Include year
    price_changes = daily_price_change.set_index('date').reindex(daily_sentiment['date'])['close_price_next_day_minus_same_day'].fillna(0).round(2).tolist()

    # Sentiment counts
    filtered['sentiment'] = filtered['sentiment'].str.lower()
    counts = filtered.groupby(['date', 'sentiment']).size().unstack(fill_value=0).reset_index()
    counts.columns = [col.lower() if col != 'date' else col for col in counts.columns]
    counts['date'] = pd.to_datetime(counts['date']).astype(str)  # Include year

    def get_label_counts(label):
        return counts.set_index('date').reindex(daily_sentiment['date']).get(label.lower(), pd.Series([0]*len(daily_sentiment))).fillna(0).astype(int).tolist()

    pos_counts = get_label_counts('positive')
    neg_counts = get_label_counts('negative')
    neu_counts = get_label_counts('neutral')

    # Top 5 positive/negative summaries
    if 'summary' in filtered.columns:
        top_pos = filtered[filtered['sentiment'] == 'positive'].sort_values(by='polarity', ascending=False).head(5)['summary'].dropna().tolist()
        top_neg = filtered[filtered['sentiment'] == 'negative'].sort_values(by='polarity').head(5)['summary'].dropna().tolist()
    else:
        top_pos = []
        top_neg = []

    return jsonify({
        "labels": daily_sentiment['date'].tolist(),
        "sentimentScores": daily_sentiment['normalized_sentiment'].round(4).tolist(),
        "positiveCounts": pos_counts,
        "negativeCounts": neg_counts,
        "neutralCounts": neu_counts,
        "priceChanges": price_changes,
        "topPositive": top_pos,
        "topNegative": top_neg,
    })



@app.route('/api/wordcloud', methods=['GET'])
def get_wordcloud():
    if df.empty:
        return jsonify({"error": "Data not loaded correctly"}), 500

    coin = request.args.get('coin', 'bitcoin').lower()
    days = int(request.args.get('days', 7))
    limit = int(request.args.get('limit', 1000))  

    filtered = df[df['tag'].str.lower() == coin].copy()
    latest_date = filtered['date'].max()

    if pd.isnull(latest_date):
        return jsonify({"words": []})

    start_date = latest_date - pd.Timedelta(days=days)
    filtered = filtered[filtered['date'] >= start_date]

    if 'summary' not in filtered.columns:
        return jsonify({"words": []})

    summaries = filtered['summary'].dropna().astype(str).head(limit)

    all_text = ' '.join(summaries).lower()
    all_text = re.sub(r'[^a-zA-Z\s]', ' ', all_text)
    all_text = re.sub(r'\s+', ' ', all_text)

    stopwords = {
    "the", "and", "for", "to", "of", "in", "on", "with", "is", "a", "an", "this",
    "that", "from", "by", "as", "are", "it", "its", "be", "has", "have", "was",
    "at", "but", "not", "or", "they", "he", "she", "you", "we", "us", "them",
    "their", "our", "his", "her", "i", "my", "me", "your", "yours", "will",
    "would", "can", "could", "should", "may", "might", "must", "shall", "do",
    "does", "did", "had", "been", "being", "so", "if", "then", "there", "here",
    "also", "about", "because", "while", "were", "which", "what", "when", "where",
    "who", "whom", "how", "than", "too", "very", "just", "into", "over", "under",
    "again", "more", "most", "some", "any", "each", "such", "no", "nor", "only",
    "own", "same", "off", "out", "up", "down", "all", "both", "few", "many",
    "ever", "always", "sometimes", "never", "still", "yet", "though", "although",
    "each", "every", "per", "via"
}


    words = [word for word in all_text.split() if word not in stopwords and len(word) > 3]

    if not words:
        return jsonify({"words": [{"text": "no-keywords", "value": 1}]})

    word_freq = Counter(words).most_common(100)

    return jsonify({
        "words": [{"text": word, "value": count} for word, count in word_freq]
    })


@app.route('/api/correlation', methods=['GET'])
def get_correlation():
    coin = request.args.get('coin', 'bitcoin').lower()
    days = int(request.args.get('days', 7))

    filtered = df[df['tag'].str.lower() == coin].copy()
    latest_date = filtered['date'].max()

    if pd.isnull(latest_date):
        return jsonify({"correlation": None, "directional_accuracy": None})

    start_date = latest_date - pd.Timedelta(days=days)
    filtered = filtered[filtered['date'] >= start_date]

    if len(filtered) < 2:
        return jsonify({"correlation": None, "directional_accuracy": None})

    try:
        corr = round(filtered['polarity'].corr(filtered['close_price_next_day_minus_same_day']), 4)

        filtered['sentiment_direction'] = filtered['polarity'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        filtered['price_direction'] = filtered['close_price_next_day_minus_same_day'].apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))

        correct = (filtered['sentiment_direction'] == filtered['price_direction']).sum()
        total = len(filtered)
        directional_accuracy = round((correct / total) * 100, 2)

        return jsonify({
            "correlation": corr,
            "directional_accuracy": directional_accuracy
        })

    except Exception:
        return jsonify({"correlation": None, "directional_accuracy": None})


if __name__ == '__main__':
    app.run(debug=True)
