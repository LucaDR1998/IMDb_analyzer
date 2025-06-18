from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.nn.functional import softmax
import torch
import os

app = Flask(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model")

# loading model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

@app.route("/analyze", methods=["POST"])
def analyze():
    # get the JSON data from POST request body
    data = request.get_json()
    texts = data.get("texts")

    if not texts or not isinstance(texts, list):
        return jsonify({"error": "Missing 'texts' list in request"}), 400

    results = []
    
    for text in texts:
        if not text.strip():
            continue
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs) # model execution
            probs = softmax(outputs.logits, dim=1)[0] # convert logits to class probabilities using softmax
            label_idx = torch.argmax(probs).item()  # get the index of the class with the highest probability
            labels = ["NEGATIVE", "POSITIVE"]
            results.append({
                "label": labels[label_idx],
                "score": round(probs[label_idx].item(), 3),
                "review": text
            })

    return jsonify(results), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
