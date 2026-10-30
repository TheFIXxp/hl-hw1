FROM python:3.13.7-slim
WORKDIR /app
COPY generate.py .
USER 10001:10001
ENTRYPOINT ["python", "-u", "generate.py"]
