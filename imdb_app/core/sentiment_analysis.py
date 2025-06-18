import requests

BERT_API_URL = "http://localhost:5000/analyze"

def analyze_sentiment(reviews):
    try:
        response = requests.post(BERT_API_URL, json={"texts": reviews})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"### Error analyzing: {e} ###")
        return []
