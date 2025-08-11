# GGVD SMN – Gestión de Grandes Volúmenes de Datos (Servicio Metereológico Nacional - Argentina)

Este proyecto implementa un **pipeline de datos por capas (Bronce → Plata → Oro)** para procesar información meteorológica proveniente del **Servicio Meteorológico Nacional (SMN)** de Argentina.  
Incluye **procesamiento por lotes** y **procesamiento en tiempo real**, con almacenamiento en **TimescaleDB** y visualización en **Grafana**, todo orquestado mediante **Docker Compose**.

---

## 🚀 Características principales

- **Pipeline de datos por capas**:
  - **Bronce**: ingesta de datos crudos.
  - **Plata**: limpieza, estandarización y enriquecimiento.
  - **Oro**: datasets analíticos listos para modelado o visualización.
- **Procesamiento en dos modos**:
  - **Por lotes (batch)**: procesa grandes volúmenes de datos históricos, genera `.csv` listos sin guardar en la base de datos.
  - **En tiempo real (streaming)**: inserta directamente en TimescaleDB los datos tal como llegan de las estaciones meteorológicas.
- **Watchers automáticos** que monitorean directorios y ejecutan pipelines.
- **Base de datos de series temporales**: PostgreSQL + TimescaleDB.
- **pgAdmin** para administración de la base de datos.
- **Grafana** para visualización y monitoreo en tiempo real.
- **Entorno reproducible** con Docker Compose.

---

## 🗂️ Estructura del proyecto

```
ceiot_ggvd_smn/
├─ api/                   # Endpoints y lógica de ingesta en tiempo real
├─ data/
│  ├─ raw/                # Datos crudos descargados
│  ├─ diccionario/        # Diccionario de variables y metadatos del dataset
│  ├─ faltantes/          # Registros o variables con datos faltantes detectados en la limpieza
│  ├─ mineria/            # Resultados y salidas de procesos de minería de datos
│  ├─ clasificacion/      # Resultados y modelos generados en la etapa de clasificación
│  ├─ bronce/             # Datos procesados por ingesta (batch)
│  ├─ plata/              # Datos limpios y estandarizados
│  └─ oro/                # Datasets finales para análisis/modelos
├─ db/                    # Scripts de inicialización de la base de datos
├─ grafana/               # Configuración y dashboards de Grafana
├─ notebooks/             # Procesamiento manual y visualizaciones
├─ pipeline/              # Pipelines Bronce → Plata → Oro
├─ watchers/              # Scripts que monitorean y ejecutan pipelines
├─ docker-compose.yml     # Orquestación de servicios
├─ Dockerfile             # Imagen para entorno de notebooks/pipelines
├─ requirements.txt       # Dependencias Python
├─ env.template           # Variables de entorno base
├─ LICENSE                # Licencia del proyecto
└─ README.md              # Este archivo
```

---

## 🔧 Requisitos

- **Docker** y **Docker Compose** instalados.

---

## ▶️ Ejecución con Docker Compose

### 1) Levantar todos los servicios
```bash
docker compose up --build
```

Esto levantará:

- **Jupyter**: entorno Jupyter con notebooks que ejecutan el pipeline y herramientas de análisis.
- **db**: PostgreSQL con extensión TimescaleDB.
- **pgAdmin**: interfaz de administración de base de datos.
- **grafana**: visualización y dashboards.
- **watchers**: monitorean y procesan datos automáticamente.

---

### 2) Acceso a servicios

| Servicio       | URL                               | Usuario / Pass (por defecto)      |
|----------------|-----------------------------------|------------------------------------|
| Jupyter Lab    | [http://localhost:8888](http://localhost:8888) | Sin Usuario ni Pass (uso local)           |
| pgAdmin        | [http://localhost:5050](http://localhost:5050) | `admin@admin.com` / `admin`        |
| Grafana        | [http://localhost:3000](http://localhost:3000) | `admin` / `admin`                   |
| PostgreSQL     | `localhost:5432`                  | `postgres` / `postgres`            |

---

## 📒 Flujo de trabajo

### **Procesamiento por lotes (Batch)**
1. **Descarga de datos históricos**  
   Colocar archivos crudos del SMN en `data/raw/datohorario`.
2. **Ejecución de pipelines**  
   Los watchers o notebooks ejecutan:
   - `pipeline_01_ingest_to_bronce.py`
   - `pipeline_02_bronce_to_plata.py`
   - `pipeline_03_plata_to_oro.py`
3. **Salida**  
   Se generan `.csv` en las carpetas Bronce, Plata y Oro.  
   **No se insertan en TimescaleDB**.

---

### **Procesamiento en tiempo real (Streaming)**
1. **Recepción de datos de estaciones meteorológicas**  
   Simulados o reales, recibidos mediante endpoints o scripts.
2. **Inserción directa en TimescaleDB**  
   Los datos se almacenan tal cual llegan, con mínima transformación.
3. **Visualización inmediata**  
   Grafana muestra los datos en dashboards configurados en tiempo real.

---

## 🧩 Watchers

- Monitorean directorios de entrada (`data/raw/`).
- Detectan nuevos archivos.
- Ejecutan el pipeline correspondiente.
- Registran en `procesados.csv` para evitar reprocesos.

---

## 📄 Licencia

Este proyecto está bajo **Licencia MIT**.  
Ver [LICENSE](LICENSE) para más detalles.
