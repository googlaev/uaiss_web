FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ntpsec-ntpdate tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY test.py .
COPY new_uaiss.html .

EXPOSE 8000

CMD sh -c "ntpdate -u pool.ntp.org || true && uvicorn test:app --host 0.0.0.0 --port 8000"
