FROM apify/actor-python:3.11

COPY . .

RUN pip install -r requirements.txt

RUN python3 -m playwright install chromium
RUN python3 -m playwright install-deps chromium

CMD ["python3", "-m", "src.main"]
