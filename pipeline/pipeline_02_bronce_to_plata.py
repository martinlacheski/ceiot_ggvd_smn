import pandas as pd
from pathlib import Path
import logging
from datetime import date

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Definir rutas para capas Bronce y Plata y Diccionario
BASE_DIR = Path(".").resolve()
RAW_DIR = BASE_DIR / "data" / "raw"
BRONCE_DIR = BASE_DIR / "data" / "bronce"
PLATA_DIR = BASE_DIR / "data" / "plata"
PLATA_DIR.mkdir(parents=True, exist_ok=True)
# Crear carpeta para faltantes si no existe
FALTANTES_DIR = BASE_DIR / "data" / "faltantes"
FALTANTES_DIR.mkdir(parents=True, exist_ok=True)
# Crear carpeta para guardar los metadatos
DICCIONARIO_DIR = BASE_DIR / "data" / "diccionario"
DICCIONARIO_DIR.mkdir(parents=True, exist_ok=True)

# Procesamiento de archivos desde Bronce a Plata
def procesar_exploracion_plata():
   # Cargar todos los archivos CSV de la capa Bronce (filtrados por estaciones)
    archivos = list(BRONCE_DIR.rglob("*.csv"))
    dfs = []

    for archivo in archivos:
        df = pd.read_csv(archivo)
        df['estacion_archivo'] = archivo.stem  # Agregar nombre del archivo como identificador de estación
        dfs.append(df)

    # Concatenar todos los DataFrames en uno solo
    df_estaciones = pd.concat(dfs, ignore_index=True)

    
    ## Normalización y combinación de fecha y hora
    
    # Convertir FECHA (DDMMAAAA) a string y formatear como DDMMAAAA
    df_estaciones['FECHA'] = df_estaciones['FECHA'].astype(str).str.zfill(8)

    # Convertir a formato datetime (indicando el formato original)
    df_estaciones['FECHA'] = pd.to_datetime(df_estaciones['FECHA'], format='%d%m%Y', errors='coerce')

    # Asegurar que HORA está en número entero (algunos datasets los tienen como string)
    df_estaciones['HORA'] = df_estaciones['HORA'].astype(int)

    # Crear columna combinada FECHA_HORA como datetime completo
    df_estaciones['FECHA_HORA'] = df_estaciones['FECHA'] + pd.to_timedelta(df_estaciones['HORA'], unit='h')

    # Guardar el archivo con los datos horarios de las estaciones de la provincia
    archivo_horario = PLATA_DIR / "horario_archivo.csv"

    # Guardar el archivo con datos horarios
    df_estaciones.to_csv(archivo_horario, index=False)
    
    
    ## Agrupación diaria de variables por estación

    # Agrupar por estación y fecha para obtener valores resumen diarios
    df_estaciones_group = df_estaciones.groupby(['NOMBRE', 'FECHA']).agg({
        'TEMP': ['mean', 'min', 'max'],
        'PNM': ['mean', 'min', 'max'],
        'HUM': ['mean', 'min', 'max'],
        'DD': 'mean',
        'FF': 'mean'
    }).reset_index()

    # Renombrar columnas para facilitar su uso
    df_estaciones_group.columns = ['ESTACION', 'FECHA',
                                'TEMP_MEAN', 'TEMP_MIN', 'TEMP_MAX',
                                'PNM_MEAN', 'PNM_MIN', 'PNM_MAX',
                                'HUM_MEAN', 'HUM_MIN', 'HUM_MAX',
                                'WIND_DIR_MEAN', 'WIND_SPEED_MEAN']

    
    ## Analisis de cobertura temporal por estacion

    # Crear rango completo de fechas
    rango_fechas = pd.date_range(df_estaciones_group['FECHA'].min(), df_estaciones_group['FECHA'].max())

    # Detectar días faltantes por estación y exportar
    for estacion in df_estaciones_group['ESTACION'].unique():
        fechas_est = pd.to_datetime(df_estaciones_group[df_estaciones_group['ESTACION'] == estacion]['FECHA'].unique())
        dias_faltantes = sorted(set(rango_fechas) - set(fechas_est))

        # Crear archivo por estación
        nombre_archivo = FALTANTES_DIR / f'dias_faltantes_{estacion.replace(" ", "_").lower()}.txt'
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(f"Días faltantes para estación: {estacion}\n")
            f.write(f"Total: {len(dias_faltantes)}\n\n")
            for dia in dias_faltantes:
                f.write(f"{dia.strftime('%Y-%m-%d')}\n")

    ## Análisis exploratorio – valores máximos, mínimos, promedio diario

    # Verificar valores inválidos en DD (mayores a 360)
    valores_dd_invalidos = df_estaciones[df_estaciones['DD'] > 360]['DD'].unique()
    print("Valores inválidos en DD (mayores a 360):", valores_dd_invalidos, "\n")

    # Crear columna de fecha sin hora para agrupar
    df_estaciones['FECHA_DIA'] = df_estaciones['FECHA'].dt.date

    # Crear DD_VALID con NaN en valores > 360 (para excluir del promedio)
    df_estaciones['DD_VALID'] = df_estaciones['DD'].where(df_estaciones['DD'] <= 360, pd.NA)

    # Paso 3: Agrupar por estación y día, y calcular estadísticas
    df_estaciones_group = df_estaciones.groupby(['NOMBRE', 'FECHA_DIA']).agg({
        'TEMP': ['mean', 'min', 'max'],
        'PNM': ['mean', 'min', 'max'],
        'HUM': ['mean', 'min', 'max'],
        'DD_VALID': ['mean'],       # Promedio con valores válidos solamente
        'DD': ['min', 'max'],       # Para conservar min y max sin filtrar
        'FF': ['mean', 'min', 'max']
    }).reset_index()

    # Renombrar columnas para facilitar lectura
    df_estaciones_group.columns = [
        'ESTACION', 'FECHA',
        'TEMP_MEAN', 'TEMP_MIN', 'TEMP_MAX',
        'PNM_MEAN', 'PNM_MIN', 'PNM_MAX',
        'HUM_MEAN', 'HUM_MIN', 'HUM_MAX',
        'WIND_DIR_MEAN',  # <- Esta es la media con valores válidos
        'WIND_DIR_MIN', 'WIND_DIR_MAX',
        'WIND_SPEED_MEAN', 'WIND_SPEED_MIN', 'WIND_SPEED_MAX'
    ]

    # Redondear solo las columnas *_MEAN a 1 decimal
    cols_mean = ['TEMP_MEAN', 'PNM_MEAN', 'HUM_MEAN', 'WIND_DIR_MEAN', 'WIND_SPEED_MEAN']
    df_estaciones_group[cols_mean] = df_estaciones_group[cols_mean].round(1)

    ## Normalización Min-Max: ¿Por qué la aplicamos?

    # Rellenar valores nulos con forward fill
    df_estaciones_group.ffill(inplace=True)

    # Definir columnas *_MEAN para normalizar
    cols_mean = ['TEMP_MEAN', 'PNM_MEAN', 'HUM_MEAN', 'WIND_DIR_MEAN', 'WIND_SPEED_MEAN']

    # Aplicar normalización Min-Max y mostrar ejemplos
    for col in cols_mean:
        min_val = df_estaciones_group[col].min()
        max_val = df_estaciones_group[col].max()
        df_estaciones_group[col + '_NORM'] = (df_estaciones_group[col] - min_val) / (max_val - min_val)

    # Exportar la Capa Plata INICIAL:
    df_estaciones_group.to_csv(PLATA_DIR / 'dataset_plata_inicial.csv', index=False)

    # --- Función para generar metadatos por columna ---
    def generar_metadatos(df):
        metadatos = []
        for col in df.columns:
            serie = df[col]
            tipo = serie.dtype
            no_nulos = serie.notnull().sum()
            nulos = serie.isnull().sum()
            pct_nulos = (nulos / len(serie)) * 100
            unicos = serie.nunique()
            ejemplo = serie.dropna().iloc[0] if no_nulos > 0 else None
            try:
                minimo = serie.min()
                maximo = serie.max()
            except:
                minimo, maximo = None, None

            metadatos.append({
                'Columna': col,
                'Tipo de dato': str(tipo),
                'Valores no nulos': no_nulos,
                'Valores nulos': nulos,
                '% Nulos': round(pct_nulos, 2),
                'Valor mínimo': minimo,
                'Valor máximo': maximo,
                'Valores únicos': unicos,
                'Ejemplo': ejemplo
            })
        return pd.DataFrame(metadatos)

    # --- Diccionario de variables (manual) ---
    diccionario_vars = pd.DataFrame([
        ["ESTACION", "Nombre de la estación meteorológica", "-", "Agrupación principal"],
        ["FECHA", "Fecha de la medición", "AAAA-MM-DD", "Convertido desde DDMMAAAA"],
        ["TEMP_MIN", "Temperatura mínima diaria", "°C", ""],
        ["TEMP_MEAN", "Temperatura promedio diaria", "°C", ""],
        ["TEMP_MAX", "Temperatura máxima diaria", "°C", ""],
        ["PNM_MIN", "Presión mínima diaria", "hPa", ""],
        ["PNM_MEAN", "Presión promedio diaria", "hPa", ""],
        ["PNM_MAX", "Presión máxima diaria", "hPa", ""],
        ["HUM_MIN", "Humedad relativa mínima diaria", "%", ""],
        ["HUM_MEAN", "Humedad relativa promedio diaria", "%", ""],
        ["HUM_MAX", "Humedad relativa máxima diaria", "%", ""],
        ["WIND_DIR_MEAN", "Dirección promedio del viento", "°", "Se excluyeron valores > 360"],
        ["WIND_SPEED_MEAN", "Velocidad promedio del viento", "km/h", ""],
        ["TEMP_MEAN_NORM", "TEMP_MEAN normalizada Min-Max", "[0, 1]", "Para análisis multivariado"],
        ["PNM_MEAN_NORM", "PNM_MEAN normalizada Min-Max", "[0, 1]", ""],
        ["HUM_MEAN_NORM", "HUM_MEAN normalizada Min-Max", "[0, 1]", ""],
        ["WIND_DIR_MEAN_NORM", "WIND_DIR_MEAN normalizada Min-Max", "[0, 1]", ""],
        ["WIND_SPEED_MEAN_NORM", "WIND_SPEED_MEAN normalizada Min-Max", "[0, 1]", ""]
    ], columns=["Columna", "Descripción", "Unidad", "Observaciones"])

    # --- Metadatos generales automáticos ---
    estaciones = df_estaciones['NOMBRE'].unique()
    provincia = estaciones[0].split()[-1].capitalize()
    cobertura_geo = f"Estaciones meteorológicas de la provincia de {provincia}, Argentina"

    fecha_min = df_estaciones['FECHA'].min().strftime('%Y-%m-%d')
    fecha_max = df_estaciones['FECHA'].max().strftime('%Y-%m-%d')
    cobertura_temporal = f"Desde {fecha_min} hasta {fecha_max}"

    metadatos_generales = pd.DataFrame([
        ["Nombre del conjunto de datos", "misiones_plata"],
        ["Fuente original", "Servicio Meteorológico Nacional (SMN)"],
        ["Cobertura geográfica", cobertura_geo],
        ["Cobertura temporal", cobertura_temporal],
        ["Frecuencia", "Datos horarios, agregados a diario"],
        ["Unidad de observación", "Estación meteorológica"],
        ["Formato de archivo", "CSV, Parquet, TXT (delimitado por tabulaciones)"],
        ["Fecha de procesamiento", date.today().isoformat()],
        ["Responsable del procesamiento", "Equipo de análisis de datos - FIUBA"],
        ["Nivel del dataset", "Capa Plata (datos limpios, normalizados y listos para análisis)"]
    ], columns=["Campo", "Valor"])

    # --- Exportar los tres archivos ---
    metadatos_df = generar_metadatos(df_estaciones_group)
    path_metadatos = DICCIONARIO_DIR / 'metadatos_variables.csv'
    path_diccionario = DICCIONARIO_DIR / 'diccionario_variables.csv'
    path_generales = DICCIONARIO_DIR / 'metadatos_generales.csv'

    metadatos_df.to_csv(path_metadatos, index=False)
    diccionario_vars.to_csv(path_diccionario, index=False)
    metadatos_generales.to_csv(path_generales, index=False)
    
    # Imprimir resumen de exportación
    logger.info("✅ Archivos exportados en formato Capa Plata:")
    logger.info(f" - CSV:     {PLATA_DIR / 'dataset_plata_inicial.csv'}")
    logger.info(f"\n Filas exportadas: {len(df_estaciones_group)}")
    logger.info(f" Columnas exportadas: {len(df_estaciones_group.columns)}")
    
def procesar_enriquecimiento_plata():
    archivo_plata = PLATA_DIR / "dataset_plata_inicial.csv"
    archivo_horario = PLATA_DIR / "horario_archivo.csv"
    
    # Cargar el dataset diario
    try:
        df_plata = pd.read_csv(archivo_plata, parse_dates=["FECHA"])
        logger.info("✅ Dataset diario cargado correctamente")
    except FileNotFoundError:
        logger.info("⚠️ El archivo diario no fue encontrado")
        return

    # Cargar el dataset horario
    try:
        df_horario = pd.read_csv(archivo_horario, parse_dates=["FECHA_HORA"])
        logger.info("✅ Dataset horario cargado correctamente")
    except FileNotFoundError:
        logger.info("⚠️ El archivo horario no fue encontrado")
        return
        
    # Generar el rango completo de fechas esperadas
    fechas_totales = pd.date_range(start=df_plata['FECHA'].min(), end=df_plata['FECHA'].max(), freq='D')

    # Obtener todas las combinaciones posibles de fecha y estación
    estaciones = df_plata['ESTACION'].unique()
    index_completo = pd.MultiIndex.from_product([fechas_totales, estaciones], names=['FECHA', 'ESTACION'])

    # Reindexar para insertar NaNs explícitos en las fechas faltantes
    df_plata = df_plata.set_index(['FECHA', 'ESTACION']).reindex(index_completo).reset_index()

    # Verificar fechas faltantes (para exportar listado)
    faltantes = df_plata[df_plata.isnull().any(axis=1)][['ESTACION', 'FECHA']]

    if not faltantes.empty:
        faltantes.to_csv(PLATA_DIR / "fechas_faltantes.txt", index=False, sep='\t')
        logger.info(f"⚠️ Fechas faltantes exportadas a: {PLATA_DIR / 'fechas_faltantes.txt'}")
    else:
        logger.info("✅ No se encontraron fechas faltantes")

    ## Relleno con forward fill por estación
    
    # Ordenar por estación y fecha para aplicar forward fill correctamente
    df_plata_ffill = df_plata.sort_values(['ESTACION', 'FECHA']).copy()
    df_plata_ffill.update(df_plata.groupby('ESTACION').ffill())
    
    ## Imputación con la media de cada estación (solo para columnas numéricas)
    
    # Imputar con la media por estación
    columnas_a_imputar = ['TEMP_MEAN', 'PNM_MEAN', 'HUM_MEAN', 'WIND_SPEED_MEAN', 'WIND_DIR_MEAN']

    for col in columnas_a_imputar:
        df_plata_ffill[col] = df_plata_ffill.groupby('ESTACION')[col].transform(lambda x: x.fillna(x.mean()))
    
    ## Tratamiento de datos faltantes en el dataset horario
    
    # Detectar horarios reales de cada estación
    df_horario['HORA'] = df_horario['FECHA_HORA'].dt.hour
    horarios_por_estacion = df_horario.groupby('NOMBRE')['HORA'].value_counts().unstack(fill_value=0)
    horarios_mas_frecuentes = horarios_por_estacion.idxmax(axis=1)

    # Detectar horarios outlier (menos del 5% de los días)
    outliers_horarios = {}
    for estacion in horarios_por_estacion.index:
        total_dias = df_horario[df_horario['NOMBRE'] == estacion]['FECHA_HORA'].dt.date.nunique()
        outliers = horarios_por_estacion.loc[estacion][
            horarios_por_estacion.loc[estacion] / total_dias < 0.05
        ].index.tolist()
        if outliers:
            outliers_horarios[estacion] = outliers

    # Crear index completo por estación y sus horarios típicos
    df_horario['FECHA'] = df_horario['FECHA_HORA'].dt.floor('D')
    estaciones_h = df_horario['NOMBRE'].unique()
    fecha_h_min = df_horario['FECHA'].min()
    fecha_h_max = df_horario['FECHA'].max()
    # rango_fechas = pd.date_range(start=fecha_h_min, end=fecha_h_max, freq='D')
    if pd.isna(fecha_h_min) or pd.isna(fecha_h_max):
        logger.warning("⚠️ No se puede generar rango de fechas en horario: FECHA contiene NaT")
        return  # o manejar de otra forma

    rango_fechas = pd.date_range(start=fecha_h_min, end=fecha_h_max, freq='D')

    # Crear combinaciones válidas por estación
    porcentaje_frecuencia = 0.05 # al menos en 5% de los días

    index_completo_personalizado = []
    for estacion in estaciones_h:
        total_dias_estacion = df_horario[df_horario['NOMBRE'] == estacion]['FECHA'].nunique()
        horas_validas = horarios_por_estacion.columns[
            (horarios_por_estacion.loc[estacion] / total_dias_estacion) >= porcentaje_frecuencia  
        ].tolist()

        for fecha in rango_fechas:
            for hora in horas_validas:
                index_completo_personalizado.append((estacion, pd.Timestamp(fecha + pd.Timedelta(hours=hora))))

    index_completo_h = pd.MultiIndex.from_tuples(index_completo_personalizado, names=['NOMBRE', 'FECHA_HORA'])

    # Reindexar para insertar valores faltantes en los horarios esperados únicamente
    df_horario_completo = df_horario.set_index(['NOMBRE', 'FECHA_HORA']).reindex(index_completo_h).reset_index()
    
    # Exportar datasets intermedios (si se desea conservar)
    df_plata.to_csv(PLATA_DIR / "dataset_intermedio_horario_con_nan.csv", index=False)
    df_plata_ffill.to_csv(PLATA_DIR / "dataset_intermedio_horario_ffill.csv", index=False)
    df_horario_completo.to_csv(PLATA_DIR / "dataset_intermedio_horario_completo.csv", index=False)

    logger.info("✅ Dataset intermedios generados correctamente")
    
    ## Imputación de datos faltantes basada en promedio entre días anterior y posterior
    
    # Variables a imputar
    variables_objetivo = ['TEMP', 'HUM', 'PNM', 'DD', 'FF']

    df_interp = df_horario_completo.copy()

    # Asegurar FECHA y HORA correctas
    df_interp['FECHA'] = df_interp['FECHA_HORA'].dt.date
    df_interp['HORA'] = df_interp['FECHA_HORA'].dt.hour

    # Ordenar por estación, fecha y hora
    df_interp = df_interp.sort_values(by=['NOMBRE', 'FECHA', 'HORA'])

    # Función de imputación por promedio entre día anterior y posterior
    def imputar_valores(grupo):
        grupo = grupo.copy()  # para evitar advertencias de SettingWithCopy
        for var in variables_objetivo:
            for idx, fila in grupo.iterrows():
                if pd.isna(fila[var]):
                    hora = fila['HORA']
                    fecha = fila['FECHA']

                    # Buscar el valor del día anterior
                    val_ant = grupo[(grupo['HORA'] == hora) & (grupo['FECHA'] < fecha)][var].last_valid_index()
                    val_ant = grupo.at[val_ant, var] if val_ant is not None else None

                    # Buscar el valor del día posterior
                    val_post = grupo[(grupo['HORA'] == hora) & (grupo['FECHA'] > fecha)][var].first_valid_index()
                    val_post = grupo.at[val_post, var] if val_post is not None else None

                    # Asignar promedio o valor disponible
                    if val_ant is not None and val_post is not None:
                        grupo.at[idx, var] = round((val_ant + val_post) / 2, 1)
                    elif val_ant is not None:
                        grupo.at[idx, var] = val_ant
                    elif val_post is not None:
                        grupo.at[idx, var] = val_post
        return grupo

    # Aplicar por estación SIN include_groups
    df_interp = (
        df_interp.groupby('NOMBRE', group_keys=False)
        .apply(imputar_valores)
        .reset_index(drop=True)
    )

    # Redondear valores numéricos a 1 decimal
    for var in variables_objetivo:
        df_interp[var] = df_interp[var].round(1)

    # Ajustar tipos de columnas
    df_interp['HORA'] = df_interp['HORA'].astype('int64')
    if 'estacion_archivo' in df_interp.columns:
        df_interp['estacion_archivo'] = df_interp['estacion_archivo'].astype('int64', errors='ignore')

    # Exportar
    archivo_imputado = PLATA_DIR / "dataset_plata_horario_final.csv"
    df_interp.to_csv(archivo_imputado, index=False)
    logger.info(f"✅ Dataset horario final generado correctamente: {archivo_imputado}")
    
    ## Generar dataset diario imputado (todas las estaciones)

    # Agrupar por estación y fecha
    df_diario_imputado = df_interp.groupby(['NOMBRE', 'FECHA']).agg(
        TEMP_MEAN=('TEMP', 'mean'),
        TEMP_MIN=('TEMP', 'min'),
        TEMP_MAX=('TEMP', 'max'),
        PNM_MEAN=('PNM', 'mean'),
        PNM_MIN=('PNM', 'min'),
        PNM_MAX=('PNM', 'max'),
        HUM_MEAN=('HUM', 'mean'),
        HUM_MIN=('HUM', 'min'),
        HUM_MAX=('HUM', 'max'),
        WIND_DIR_MEAN=('DD', 'mean'),
        WIND_DIR_MIN=('DD', 'min'),
        WIND_DIR_MAX=('DD', 'max'),
        WIND_SPEED_MEAN=('FF', 'mean'),
        WIND_SPEED_MIN=('FF', 'min'),
        WIND_SPEED_MAX=('FF', 'max')
    ).reset_index()

    # Renombrar y ordenar
    df_diario_imputado.rename(columns={'NOMBRE':'ESTACION'}, inplace=True)
    df_diario_imputado['FECHA'] = pd.to_datetime(df_diario_imputado['FECHA'])
    df_diario_imputado = df_diario_imputado.sort_values(by=['ESTACION','FECHA']).reset_index(drop=True)

    # Ajustes de tipos y redondeo

    # Redondear medias a 1 decimal
    cols_float = ['TEMP_MEAN','PNM_MEAN','HUM_MEAN','WIND_DIR_MEAN','WIND_SPEED_MEAN']
    df_diario_imputado[cols_float] = df_diario_imputado[cols_float].round(1)

    # Convertir min y max a enteros
    cols_int = [
        'TEMP_MIN','TEMP_MAX','PNM_MIN','PNM_MAX',
        'HUM_MIN','HUM_MAX',
        'WIND_DIR_MIN','WIND_DIR_MAX',
        'WIND_SPEED_MIN','WIND_SPEED_MAX'
    ]
    df_diario_imputado[cols_int] = df_diario_imputado[cols_int].round().astype(int)

    # Normalización Min-Max de las variables MEAN

    variables_mean = ['TEMP_MEAN','PNM_MEAN','HUM_MEAN','WIND_DIR_MEAN','WIND_SPEED_MEAN']
    for var in variables_mean:
        col_norm = var + '_NORM'
        min_val = df_diario_imputado[var].min()
        max_val = df_diario_imputado[var].max()
        df_diario_imputado[col_norm] = ((df_diario_imputado[var] - min_val) / (max_val - min_val)).round(5)

    # Guardar el dataset diario imputado completo
    archivo_diario_imputado = PLATA_DIR / "dataset_plata_diario_final.csv"
    df_diario_imputado.to_csv(archivo_diario_imputado, index=False)
    logger.info(f"✅ Dataset diario final generado correctamente: {archivo_diario_imputado}")
    
if __name__ == "__main__":
    procesar_exploracion_plata()
    procesar_enriquecimiento_plata()
