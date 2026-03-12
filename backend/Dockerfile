FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/backend

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ghostscript \
        libreoffice-calc \
        libreoffice-core \
        libreoffice-impress \
        libreoffice-writer \
        curl \
        fonts-dejavu-core \
        poppler-utils \
        qpdf \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-osd \
    && rm -rf /var/lib/apt/lists/*

COPY . /srv/backend

RUN rm -rf /srv/backend/build /srv/backend/dist /srv/backend/pdforbit_backend.egg-info

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000

CMD ["python", "-m", "app.workers.railway_runner"]
