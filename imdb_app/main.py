import os
from api.model_utils import download_model
from output.dashboard import run_dashboard

def main():
    model_dir = os.path.join("api", "model")
    model_filename = "model.safetensors"
    model_path = os.path.join(model_dir, model_filename)

    if not os.path.exists(model_path):
        print("### Model not found. Downloading... ###")
        download_model(model_path)
    else:
        print("### Model found and loaded ###")

    run_dashboard()

if __name__ == "__main__":
    main()

