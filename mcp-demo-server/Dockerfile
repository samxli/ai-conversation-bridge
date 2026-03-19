FROM python:3.13-slim@sha256:5a7bc62572092e849a3de833858cd2e5542fe24bc49e3fc54948c8b0d8ca4b29

RUN useradd -m appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY mock_data ./mock_data

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["python", "main.py"]
