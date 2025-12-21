FROM python:3.12-slim

WORKDIR /llm

ARG LLM_BASE_URL
ARG LLM_API_KEY
ARG LLM_NAME

ENV LLM_BASE_URL=${LLM_BASE_URL}
ENV LLM_API_KEY=${LLM_API_KEY}
ENV LLM_NAME=${LLM_NAME}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]