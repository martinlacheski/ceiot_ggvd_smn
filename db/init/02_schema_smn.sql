DROP TABLE IF EXISTS smn_obs CASCADE;

CREATE TABLE smn_obs (
  estacion_nombre TEXT NOT NULL,
  fecha_hora      TIMESTAMPTZ NOT NULL,
  temp_c          DOUBLE PRECISION,
  hum_pct         DOUBLE PRECISION,
  pnm_hpa         DOUBLE PRECISION,
  wind_dir_deg    DOUBLE PRECISION,
  wind_speed_kmh  DOUBLE PRECISION,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (estacion_nombre, fecha_hora)
);

-- Hypertable por tiempo
SELECT create_hypertable('smn_obs', 'fecha_hora', if_not_exists => TRUE);

-- Unicidad por estación + hora (evita duplicados al reingestar)
CREATE UNIQUE INDEX IF NOT EXISTS ux_smn_obs_est_hora
  ON smn_obs (estacion_nombre, fecha_hora);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_smn_obs_ts ON smn_obs (fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_smn_obs_est ON smn_obs (estacion_nombre);