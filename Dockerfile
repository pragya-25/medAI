FROM python:3.11-slim

WORKDIR /app

# CPU-only PyTorch keeps the image small (about 1 GB instead of 5+ GB with CUDA).
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY service/requirements.txt service/requirements.txt
RUN pip install --no-cache-dir -r service/requirements.txt

COPY ml/ ml/
COPY service/ service/

ENV PYTHONUNBUFFERED=1
# The model weights (best.pt) are NOT baked into the image: they are mounted at runtime
# (see docker-compose.yml) so the image stays reusable and weights stay out of git.
CMD ["uvicorn", "service.api:app", "--host", "0.0.0.0", "--port", "8000"]
