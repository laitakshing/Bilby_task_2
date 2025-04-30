# docker/Dockerfile

# Use the slim Python base
FROM python:3.12-slim

# Set up a dedicated cache directory for Hugging Face downloads
ENV HF_HOME=/model_cache
VOLUME /model_cache

# Pin protobuf to 3.x to avoid compatibility issues and install gliner
RUN pip install --no-cache-dir "protobuf<4,>=3.20.0" gliner

# Pre-download the GLiNER model into the HF cache during build
# This ensures the model is already available in the image
RUN python - <<EOF
from gliner import GLiNER
# Load and cache the model
GLiNER.from_pretrained("urchade/gliner_multi-v2.1")
EOF

# For faster Hugging Face Hub downloads next time, uncomment:
RUN pip install --no-cache-dir "huggingface_hub[hf_xet]"

# Copy the extraction script
WORKDIR /app
COPY extract.py /app/extract.py

# Entrypoint runs extract.py, which will use the cached model
ENTRYPOINT ["python", "extract.py"]
