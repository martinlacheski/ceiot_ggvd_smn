FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependencias
RUN apt-get update && apt-get install -y build-essential && \
    pip install --upgrade pip && \
    pip install notebook jupyterlab pandas numpy pyarrow scikit-learn matplotlib seaborn plotly openpyxl prefect

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]