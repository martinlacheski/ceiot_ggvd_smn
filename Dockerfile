# Instalar la imagen base de Python 3.10 slim
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Crear usuario no root
RUN useradd -ms /bin/bash jovyan

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar requirements.txt al contenedor
COPY requirements.txt .

# Instalar dependencias del sistema y Python
RUN apt-get update && apt-get install -y build-essential && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Cambiar a usuario jovyan
USER jovyan

# Exponer el puerto de Jupyter Notebook
EXPOSE 8888

# Ejecutar Jupyter Notebook al iniciar el contenedor
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--NotebookApp.token=", "--NotebookApp.password="]


