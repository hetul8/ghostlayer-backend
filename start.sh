#!/bin/bash
python -m spacy download en_core_web_lg && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
