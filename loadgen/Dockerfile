FROM python:3.13.7-slim
WORKDIR /app
COPY load.py .
USER 10001:10001
ENTRYPOINT ["python", "-u", "load.py"]
