import streamlit as st
import pandas as pd
from collections import Counter
import plotly.express as px
import re
from core.rating_predictor import train_and_predict_rating
from db.postgre import Postgre
from core.sentiment_analysis import analyze_sentiment
from core.imdb_scraper import search_imdb_titles, get_imdb_reviews, build_imdb_reviews_url

def _format_title_option(result):
    title = result.get("title", "N/A")
    year = result.get("year")
    year_part = f" ({year})" if year and year != "N/A" else ""

    other_info = result.get("other_info") or []
    if isinstance(other_info, list):
        other_info = [str(x).strip() for x in other_info if str(x).strip() and str(x).strip() != "N/A"]
        info_part = f" - {', '.join(other_info)}" if other_info else ""
    else:
        info_part = ""

    return f"{title}{year_part}{info_part}"

def _extract_title_id_from_url(url):
    if not isinstance(url, str):
        return None
    match = re.search(r"/title/(tt\d+)", url)
    return match.group(1) if match else None

def render_metrics_and_pie_chart(counts, average_score):
    labels = list(counts.keys())
    values = list(counts.values())

    # create two columns: left for metrics, right for pie chart
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Review Summary")
        st.metric("▲ Positive reviews", counts.get("POSITIVE", 0))
        st.metric("▼ Negative reviews", counts.get("NEGATIVE", 0))
        st.metric("⌀ Average score", average_score)

    with col2:
        pie_fig = px.pie(
            names=labels,
            values=values,
            title="Percentage Distribution of Sentiments",
            color=labels,
            color_discrete_map={"POSITIVE": "green", "NEGATIVE": "red"},
            hole=0.4
        )
        pie_fig.update_traces(textinfo="percent+label")
        pie_fig.update_layout(height=400)
        st.plotly_chart(pie_fig, use_container_width=True)


def render_review_table(results, reviews):
    # attach the review date to each sentiment result
    for i in range(len(results)):
        results[i]["date"] = reviews[i].get("date", None)

    df = pd.DataFrame(results)
    st.subheader("Review Details")
    st.dataframe(df)
    return df

def render_time_series(df):
    # convert the 'date' column to datetime format
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df_valid = df.dropna(subset=["date", "label"])

    if df_valid.empty:
        st.info("No valid data available to generate a time series chart.")
        return
    # create a new column with year and month (YYYY-MM) for aggregation
    df_valid["year_month"] = df_valid["date"].dt.to_period("M").astype(str)
    grouped = df_valid.groupby(["year_month", "label"]).size().reset_index(name="count")

    fig = px.line(
        grouped,
        x="year_month",
        y="count",
        color="label",
        markers=True,
        title="Monthly trend of reviews over time",
        color_discrete_map={"POSITIVE": "green", "NEGATIVE": "red"}
    )

    fig.update_traces(mode="lines+markers")
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Number of reviews",
        template="plotly_white",
        hovermode="x unified",
        height=500,
        font=dict(size=14)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_rating_prediction(reviews):
    st.subheader("Rating Prediction Analysis")

    with st.spinner("Training rating prediction model..."):
        rating_results = train_and_predict_rating(reviews)

    if not rating_results:
        st.info("Not enough rating data available for training.")
        return

    rating_df = pd.DataFrame(rating_results)

    st.dataframe(
        rating_df[["true_rating", "predicted_rating", "delta", "comment"]],
        use_container_width=True,
        height=400
    )
    st.caption("Comparison between actual user ratings and model-predicted scores.")

    # saving data to db
    try:
        movie_title = st.session_state.get("selected_movie_title", "Unknown")
        db = Postgre()
        db.save_rating_results(movie_title, rating_results)
        db.close()
        st.success("Rating predictions saved to PostgreSQL.")
    except Exception as e:
        st.error(f"Error saving to PostgreSQL: {e}")

def run_dashboard():
    st.set_page_config(page_title="IMDb Sentiment Dashboard", layout="wide")
    st.title("IMDb Sentiment Analysis Dashboard")

    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "selected_option" not in st.session_state:
        st.session_state.selected_option = -1
    if "reviews_cache" not in st.session_state:
        st.session_state.reviews_cache = {}

    query = st.text_input("Enter the name of the movie or TV series to search:", key="query_input")
    query_clean = (query or "").strip()

    if not query_clean:
        return

    if st.session_state.search_query != query_clean:
        with st.spinner("Searching titles on IMDb..."):
            st.session_state.search_results = search_imdb_titles(query_clean)
        st.session_state.search_query = query_clean
        st.session_state.selected_option = -1
        st.session_state.reviews_cache = {}

    results = st.session_state.search_results
    if not results:
        st.warning("No results found for your search.")
        return

    option_values = [-1] + list(range(len(results)))
    selected_idx = st.selectbox(
        "Select a title to analyze:",
        options=option_values,
        format_func=lambda i: "-- Select a title --" if i == -1 else _format_title_option(results[i]),
        key="selected_option",
    )

    if selected_idx == -1:
        return

    selected_row = results[selected_idx]
    selected_url = selected_row.get("url")
    review_url = build_imdb_reviews_url(selected_url)
    if not review_url:
        st.error("Invalid IMDb title URL selected. Please choose another result.")
        return

    title_id = _extract_title_id_from_url(selected_url) or selected_url
    if title_id not in st.session_state.reviews_cache:
        st.info("Fetching reviews from IMDb...")
        fetched_reviews = get_imdb_reviews(review_url)
        if fetched_reviews:
            st.session_state.reviews_cache[title_id] = fetched_reviews

    reviews = st.session_state.reviews_cache.get(title_id, [])
    if not reviews:
        selected_label = _format_title_option(selected_row)
        st.error(f"No reviews were found for selected title: {selected_label}. Try another result from the list.")
        return

    st.success(f"{len(reviews)} reviews retrieved. Starting sentiment analysis with BERT...")
    comments = [r["comment"] for r in reviews if r["comment"].strip() and r["comment"].strip().upper() != "N/A"]
    sentiment_results = analyze_sentiment(comments)

    if not sentiment_results:
        st.error("No results returned from the sentiment model.")
        return

    # calculate aggregated sentiment metrics
    labels = [r["label"] for r in sentiment_results]
    scores = [r["score"] for r in sentiment_results if r["score"] is not None]
    average_score = round(sum(scores) / len(scores), 3) if scores else 0
    counts = Counter(labels)

    # render sentiment summary and visualizations
    render_metrics_and_pie_chart(counts, average_score)
    df = render_review_table(sentiment_results, reviews)
    render_time_series(df)
    st.session_state.selected_movie_title = selected_row.get("title", "Unknown")
    render_rating_prediction(reviews)
