# virtual-lab-backend/Dockerfile

# Python 3.10 негізіндегі жеңіл image
FROM python:3.10-slim

# Жұмыс директориясы
WORKDIR /app

# Тәуелділіктерді орнату (кештелген қабаттарды тиімді пайдалану үшін алдымен requirements.txt көшіреміз)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Қалған кодты көшіру
COPY . .

# Портты ашу (ақпарат үшін)
EXPOSE 8000

# Қосымшаны іске қосу
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]