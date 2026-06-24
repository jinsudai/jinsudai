FROM python:3.11-slim

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_DEFAULT_REGION
ARG AWS_REGION
ARG AWS_ENDPOINT_URL

RUN pip install evidently boto3 s3fs

WORKDIR /app

COPY . .

CMD ["evidently", "ui", "--workspace", "s3://evidently-reports/workspace", "--port", "7860", "--host", "0.0.0.0"]