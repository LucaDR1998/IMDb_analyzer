from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os

def download_model():
    # model from HuggingFace Hub
    MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
    TARGET_DIR = os.path.join("api", "model")

    # create dir if not exist
    os.makedirs(TARGET_DIR, exist_ok=True)

    print("### Download tokenizer... ###")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.save_pretrained(TARGET_DIR)

    print("### Download model... ###")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.save_pretrained(TARGET_DIR)

    print(f"### Model saved in: {TARGET_DIR} ###")
