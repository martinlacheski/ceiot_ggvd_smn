# Instalar la imagen base de Python 3.10 slim
FROM python:3.10-slim

# Establecer variables de entorno
ENV DEBIAN_FRONTEND=noninteractive

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar requirements.txt al contenedor
COPY requirements.txt .

# Instalar dependencias
RUN apt-get update && apt-get install -y build-essential && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Exponer el puerto de Jupyter Notebook
EXPOSE 8888

# Ejecutar Jupyter Notebook al iniciar el contenedor
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]