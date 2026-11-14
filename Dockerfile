FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd -r -u 10001 arena
COPY tournament.py research.py dashboard.py /app/
COPY templates /app/templates
RUN mkdir -p /app/runtime && chown -R arena:arena /app/runtime
USER arena
CMD ["python", "tournament.py"]
