
# IMDb Analyzer – Sentiment & Rating Prediction System

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Dockerized](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/status-beta-lightgrey)]()

This project is a full-stack AI-powered system that analyzes user reviews from IMDb to classify their sentiment and predict their corresponding numeric ratings. It provides an interactive interface, a backend for inference, automated scraping, and persistent data storage.

---

## Features

- Search IMDb titles and select a movie/series interactively  
- Automatically scrape real reviews from IMDb (text, rating, date)  
- Analyze sentiment using a fine-tuned **BERT** model  
- Predict user rating (1–10) using a **Random Forest Regressor**  
- Visualize:
  - Sentiment distribution (pie chart)
  - Sentiment/rating summary table
  - Review evolution over time (timeline chart)
- Detect inconsistencies between textual sentiment and star ratings  
- Persist all results into a **PostgreSQL** database for future analysis  

---

## AI Models

### BERT – Sentiment Classification  
The sentiment analysis is handled via a BERT model loaded in a Flask microservice. It classifies each review as **POSITIVE** or **NEGATIVE**, returning the associated confidence score.

### Random Forest – Rating Regression  
A RandomForestRegressor is trained using TF-IDF features of reviews to predict the numerical rating. The model also computes the delta between predicted and actual ratings to flag inconsistencies.

---

## Technologies Used

- `Python`, `Flask`, `Streamlit`, `Selenium`
- `Transformers`, `Torch`, `Scikit-learn`
- `PostgreSQL` as the database backend

### Dockerized Deployment
- `Dockerfile` for building the application container  
- `docker-compose.yml` for orchestrating services (Streamlit, Flask, Selenium, DB)  
- `.env` file for environment variable configuration  
- Automatic installation of:
  - Python dependencies (`requirements.txt`)
  - Chrome extension for Selenium
  - BERT model if not yet present

---

## Project Structure

```
IMDb_analyzer/
├── app/                   # Streamlit frontend
├── scraper/               # Selenium-based IMDb scraper
├── api/                   # Flask API with BERT model
├── models/                # RandomForest training/eval logic
├── db/                    # PostgreSQL interactions
├── docker-compose.yml     # Multi-service orchestration
├── Dockerfile             # App container definition
├── .env                   # Environment config
└── README.md
```

---

## How to Run with Docker

Clone the repo and run:

```bash
git clone https://github.com/LucaDR1998/IMDb_analyzer.git
cd IMDb_analyzer
docker-compose up --build
```

Access the Streamlit interface at:  
`http://localhost:8501`

---

## Database Schema

The PostgreSQL table stores:

| Field               | Description                              |
|--------------------|------------------------------------------|
| `movie_title`       | Title of the analyzed movie or show      |
| `comment`           | Text of the IMDb review                  |
| `true_rating`       | Original IMDb star rating (1–10)         |
| `predicted_rating`  | Rating predicted by the Random Forest    |
| `delta`             | Difference between true and predicted    |
| `analysis_timestamp`| Date and time of the analysis            |

---

## Future Improvements

- Automatic model retraining with new data  
- Advanced dashboards (by genre, year, etc.)  
- Fake review detection based on mismatches  
- Recommendation engine based on sentiment trends  

---

## Delivery

The project is publicly available at:  
**https://github.com/LucaDR1998/IMDb_analyzer**

---

## License

This project is licensed under the GPL v3 License.

---

**Author:** [Luca Demicheli Rubio](https://github.com/LucaDR1998)
