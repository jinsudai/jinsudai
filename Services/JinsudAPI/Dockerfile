FROM continuumio/miniconda3

RUN apt-get update -y 
RUN apt-get install nano unzip curl -y

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

# Copy only necessary ml module files for inference (copied by hf_push_services.py)
COPY --chown=user src/ml/__init__.py /home/user/src/ml/
COPY --chown=user src/ml/config/__init__.py /home/user/src/ml/config/
COPY --chown=user src/ml/config/config_loader.py /home/user/src/ml/config/
COPY --chown=user src/ml/config/global_config.py /home/user/src/ml/config/
COPY --chown=user src/ml/utils/__init__.py /home/user/src/ml/utils/
COPY --chown=user src/ml/utils/models/__init__.py /home/user/src/ml/utils/models/
COPY --chown=user src/ml/utils/models/models_inference.py /home/user/src/ml/utils/models/

# Copy config files (copied by hf_push_services.py)
COPY --chown=user src/configs/ /home/user/src/configs/

# Copy FastAPI service files
WORKDIR $HOME/app
COPY --chown=user . $HOME/app

CMD uvicorn main:app --host 0.0.0.0 --port 7860 