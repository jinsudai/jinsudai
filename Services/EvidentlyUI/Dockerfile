FROM python:3.11-slim

RUN pip install evidently boto3 s3fs

WORKDIR /app

COPY . .

CMD ["evidently", "ui", "--workspace", "s3://evidently-reports/workspace"]