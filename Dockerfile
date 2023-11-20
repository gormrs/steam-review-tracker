FROM python:2.7-slim

WORKDIR /app

COPY src/ .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80


CMD ["python", "steam_review_scraper.py"]
