FROM main

WORKDIR /app
COPY main.py utils.py .env ./

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt


ENTRYPOINT ["python", "main.py"]