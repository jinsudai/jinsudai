FROM python:3.11-slim

WORKDIR /app

RUN pip install prefect==3.7.0

ENV PREFECT_API_URL=https://jenedai-prefect.hf.space/api
ENV PREFECT_WORK_POOL=default

CMD prefect worker start --pool default