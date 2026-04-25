# Usa a imagem oficial do Python
FROM python:3.13-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para Selenium + Firefox
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    firefox-esr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala o GeckoDriver (necessário para controlar o Firefox)
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.35.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.35.0-linux64.tar.gz

# Copia arquivos de dependências
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY app/ ./app/

# Expõe a porta para o servidor web
EXPOSE 5000

# Comando para executar a aplicação
CMD ["python", "-m", "app.main"]