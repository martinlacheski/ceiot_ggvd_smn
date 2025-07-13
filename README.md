# GGVD SMN – Gestión de Grandes Volúmenes de Datos

Este proyecto muestra cómo construir un pipeline de datos por capas (Bronce, Plata, Oro) utilizando datos meteorológicos del Servicio Meteorológico Nacional (SMN) de Argentina. El entorno está preparado para ejecutarse en un contenedor Docker.

## Estructura del Proyecto

- `data/`: contiene los datos crudos descargados y luego los datos procesados
- `notebooks/`: notebooks de procesamiento, análisis y visualización
- `metadata/`: documentación técnica y diccionario de datos

## Requisitos

- Docker

## Cómo usar

### Construir el contenedor

```bash
docker build -t ggvd_smn .
```

### Ejecutar el contenedor

#### ▶️ En Linux / macOS
```bash
docker run -p 8888:8888 -v $(pwd):/app ggvd_smn
```

#### ▶️ En Windows PowerShell
```powershell
docker run -p 8888:8888 -v ${PWD}:/app ggvd_smn
```

#### ▶️ En Windows CMD
```cmd
docker run -p 8888:8888 -v %cd%:/app ggvd_smn
```

> 📝 **Si la ruta local contiene espacios, se recomienda usar comillas:**

**PowerShell:**
```powershell
docker run -p 8888:8888 -v "${PWD}:/app" ggvd_smn
```

**CMD:**
```cmd
docker run -p 8888:8888 -v "%cd%:/app" ggvd_smn
```


### Acceder

Abrir [http://localhost:8888](http://localhost:8888) en el navegador.

🔓 **No se requiere contraseña ni token.**

⚠️ Esta configuración es para uso local o entornos controlados.

## 📄 Licencia

El código fuente de este proyecto está licenciado bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.

---