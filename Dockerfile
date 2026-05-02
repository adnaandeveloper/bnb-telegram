FROM python:3.11-slim

WORKDIR /app

# Installer dependencies først (hurtigere builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopier resten
COPY . .

# Railway kører som worker – ingen port nødvendig
CMD ["python", "bot.py"]