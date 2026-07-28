FROM python:3.12-slim

WORKDIR /app

COPY requirements-lock-python312.txt ./
RUN pip install --no-cache-dir -r requirements-lock-python312.txt

COPY . .

VOLUME ["/app/external_runs"]
CMD ["python", "reproduce.py", "--protocol", "all", "--strict-environment"]
