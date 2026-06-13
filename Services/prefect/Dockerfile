FROM python:3.11-slim

WORKDIR /src

ENV PREFECT_UI_API_URL=/api

RUN pip install --no-cache-dir prefect

EXPOSE 7860

CMD ["prefect", "server", "start", "--host", "0.0.0.0", "--port", "7860"]