FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home app
COPY agent.py ./

USER app
EXPOSE 8080
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]
