FROM continuumio/miniconda3

RUN apt-get update -y 
RUN apt-get install nano unzip curl -y

# Create user for HuggingFace compatibility
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy dependencies
COPY pyproject.toml /dependencies/pyproject.toml
RUN pip install -e /dependencies

# Copy source code
COPY --chown=user src/ $HOME/app/src/
COPY --chown=user pipelines/WeatherDaily/ $HOME/app/

# Copy config files
COPY --chown=user src/configs/ $HOME/app/src/configs/
COPY --chown=user .env.example $HOME/app/.env.example

CMD ["python", "run_pipeline.py", "--days_ahead", "7"]
