# Use uma imagem base oficial do Python
FROM python:3.11-slim

# Defina o diretório de trabalho no container
WORKDIR /usr/src/app

# Variáveis de ambiente (Render pode sobrescrevê-las)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT 8000 # Render usa a variável PORT, mas podemos definir um default

# Instale dependências do sistema se necessário (ex: para compilar algumas libs)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Copie o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY ./app ./app
COPY ./.env ./.env # O Render injetará variáveis de ambiente, mas pode ser útil para build local
COPY ./rsa_private_key.pem ./rsa_private_key.pem
COPY ./rsa_public_key.pem ./rsa_public_key.pem


# Exponha a porta que o Uvicorn vai rodar
EXPOSE ${PORT}

# Comando para rodar a aplicação usando Uvicorn
# Render injeta a variável PORT. Uvicorn a usará se disponível.
# O host 0.0.0.0 é importante para o Docker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
# Render geralmente define a PORT para 10000 ou outra. O uvicorn no Render
# deve usar a variável de ambiente PORT passada por ele.
# No render.yaml, você pode especificar o startCommand para ser mais explícito.
