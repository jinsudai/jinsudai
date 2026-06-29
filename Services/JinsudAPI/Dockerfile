FROM continuumio/miniconda3

RUN apt-get update -y 
RUN apt-get install nano unzip curl -y

# Create conda environment with Python 3.11 to match model training environment
RUN conda create -n jinsudapi python=3.11 -y
RUN echo "conda activate jinsudapi" >> ~/.bashrc
ENV PATH /opt/conda/envs/jinsudapi/bin:$PATH

ENV MLFLOW_TRACKING_URI=https://jinsudai-mlflow.hf.space/
ENV ENVIRONMENT=test

# THIS IS SPECIFIC TO HUGGINFACE
# We create a new user named "user" with ID of 1000
RUN useradd -m -u 1000 user
# We switch from "root" (default user when creating an image) to "user" 
USER user
# We set two environmnet variables 
# so that we can give ownership to all files in there afterwards
# we also add /home/user/.local/bin in the $PATH environment variable 
# PATH environment variable sets paths to look for installed binaries
# We update it so that Linux knows where to look for binaries if we were to install them with "user".
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# We set working directory to $HOME/app (<=> /home/user/app)
WORKDIR $HOME/app

# Install basic dependencies
COPY requirements.txt /dependencies/requirements.txt
RUN pip install -r /dependencies/requirements.txt

# Copy src directory (copied by hf_push_services.py)
COPY --chown=user src/ /home/user/src/

# Copy FastAPI service files
WORKDIR $HOME/src
COPY --chown=user . $HOME/src

CMD uvicorn main:app --host 0.0.0.0 --port 7860 