from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
import numpy as np

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
    comments = []
    ratings = []

    for r in reviews:
        # include only reviews with both comment and rating
        if (r["comment"].strip().upper() != "N/A" and r["comment"].strip() and r["rating"]):
            comments.append(r["comment"])
            ratings.append(float(r["rating"]))  # IMDb ratings: 1-10

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
