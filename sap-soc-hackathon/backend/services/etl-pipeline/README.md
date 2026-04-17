# ETL Pipeline — SAP SOC Hackathon

Ingesta logs de la SAP API cada 5 minutos y los sincroniza a SAP HANA Cloud. Corre de forma autónoma en SAP BTP Cloud Foundry — no depende de ninguna computadora local.

## Cómo funciona

- `app.py` — entrada principal, modo daemon (loop infinito cada 5 min) o manual (una sola ejecución)
- `ingestion.py` — llama la SAP API, parsea los logs y los inserta en HANA
- `connection.py` — conexión a SAP HANA Cloud (usa `VCAP_SERVICES` en BTP, credenciales locales en dev)

## Deploy en SAP BTP Cloud Foundry

```bash
# Login (región us10-001)
cf login -a https://api.cf.us10-001.hana.ondemand.com

# Deploy
cf push -f manifest.yml
```

La app queda corriendo en los servidores de SAP aunque la computadora esté apagada.

## Monitoreo

```bash
# Logs recientes
cf logs soc-etl-pipeline --recent

# Logs en tiempo real
cf logs soc-etl-pipeline

# Estado de la app
cf app soc-etl-pipeline
```

## Gestión

```bash
cf stop soc-etl-pipeline      # Detener
cf restart soc-etl-pipeline   # Reiniciar
cf delete soc-etl-pipeline    # Eliminar
```

## Tablas en HANA

| Tabla | Contenido |
|-------|-----------|
| `SAP_SYSTEM_LOGS` | Logs de sistema (HTTP, IPs, servicios) |
| `SAP_LLM_LOGS` | Logs de modelos LLM (costo, latencia, status) |

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `SAP_API_KEY` | API key para autenticarse en la SAP API |
| `VCAP_SERVICES` | Inyectada automáticamente por BTP con credenciales de HANA |
