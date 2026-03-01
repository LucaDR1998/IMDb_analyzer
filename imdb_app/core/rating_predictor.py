from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
import numpy as np
import re

class RatingRegressor:
    def __init__(self):
        self.pipeline = make_pipeline(
            TfidfVectorizer(max_features=1000),
            RandomForestRegressor(n_estimators=100, random_state=42) # 100 trees
        )
        self.trained = False

    def fit(self, comments, ratings):
        self.pipeline.fit(comments, ratings)
        self.trained = True

    def predict(self, comments):
        if not self.trained:
            raise ValueError("Model is not trained yet.") # Prevent predictions before training
        return self.pipeline.predict(comments)

    def evaluate(self, comments, true_ratings):
        preds = self.predict(comments)
        deltas = preds - np.array(true_ratings) # difference between predicted and true ratings
        return preds, deltas


def train_and_predict_rating(reviews):
    def parse_rating(value):
        if value is None:
            return None

        text = str(value).strip()
        if not text or text.upper() == "N/A":
            return None

        # Handles formats like "10", "10/10", "8.5/10".
        match = re.search(r"\d+(?:[.,]\d+)?", text)
        if not match:
            return None

        numeric = float(match.group(0).replace(",", "."))
        if numeric < 0 or numeric > 10:
            return None
        return numeric

    comments = []
    ratings = []

    for r in reviews:
        comment = str(r.get("comment", "")).strip()
        parsed_rating = parse_rating(r.get("rating"))

        # include only reviews with both comment and valid rating
        if comment and comment.upper() != "N/A" and parsed_rating is not None:
            comments.append(comment)
            ratings.append(parsed_rating)  # IMDb ratings: 1-10

    if not comments:
        return None

    regressor = RatingRegressor()
    regressor.fit(comments, ratings)

    predictions, deltas = regressor.evaluate(comments, ratings)

    results = []
    for i in range(len(comments)):
        results.append({
            "comment": comments[i],
            "true_rating": ratings[i],
            "predicted_rating": round(predictions[i], 1),
            "delta": round(deltas[i], 1)
        })

    return results    
