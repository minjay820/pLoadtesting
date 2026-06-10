FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev gnupg2 ca-certificates curl default-jre-headless wget unzip && \
    dpkgArch="$(dpkg --print-architecture)" && \
    if [ "$dpkgArch" = "amd64" ]; then \
        curl -s https://dl.k6.io/key.gpg | gpg --dearmor -o /usr/share/keyrings/k6-archive-keyring.gpg && \
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | tee /etc/apt/sources.list.d/k6.list && \
        apt-get update && \
        apt-get install -y --no-install-recommends k6; \
    else \
        curl -L "https://github.com/grafana/k6/releases/download/v0.51.0/k6-v0.51.0-linux-arm64.tar.gz" | tar -xz && \
        mv k6-v0.51.0-linux-arm64/k6 /usr/local/bin/ && \
        rm -rf k6-v0.51.0-linux-arm64; \
    fi && \
    rm -rf /var/lib/apt/lists/*

RUN wget -q https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.zip && \
    unzip -q apache-jmeter-5.6.3.zip -d /opt && \
    rm apache-jmeter-5.6.3.zip && \
    ln -s /opt/apache-jmeter-5.6.3/bin/jmeter /usr/local/bin/jmeter

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["python", "agent.py"]
