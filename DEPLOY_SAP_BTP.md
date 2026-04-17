# 🚀 Guía de Deploy en SAP BTP

Estos son los pasos exactos para deployar el proyecto en **SAP Business Technology Platform (BTP)**.

## 📋 Requisitos Previos

1. **Cuenta SAP BTP** con acceso a Cloud Foundry (CF)
2. **Cloud Foundry CLI** instalado → [Descargar](https://github.com/cloudfoundry/cli/releases)
3. **MBT (Multi-target Build Tool)** instalado → [Descargar](https://github.com/SAP/cloud-mta-build-tool/releases)
4. **Make** instalado (Windows: usar [GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm))

---

## 🔑 Paso 1: Conectarte a SAP BTP

```bash
# Login a Cloud Foundry
cf login -a https://api.cf.us10.hana.ondemand.com

# Selecciona tu ORG y SPACE cuando se te pida
# Org: (tu-organizacion)
# Space: (tu-espacio, ej: dev)
```

**Verifica que estés conectado:**
```bash
cf target
```

**Esperado:**
```
api endpoint:   https://api.cf.us10.hana.ondemand.com
api version:    3.108.0
user:           tu-usuario@email.com
org:            tu-org
space:          dev
```

---

## 📦 Paso 2: Hacer Build del Proyecto

```bash
# Desde la carpeta sap-soc-hackathon
cd sap-soc-hackathon

# Hacer build MTA
mbt build -t mta_archives

# Esto crea: mta_archives/sap-soc-platform_1.0.0.mtar
```

---

## 🌐 Paso 3: Deployar el MTAR a SAP BTP

```bash
# Deploy el archivo .mtar creado
cf deploy mta_archives/sap-soc-platform_1.0.0.mtar

# Esto deployará:
# ✓ API Gateway
# ✓ ETL Pipeline (cada 5 minutos)
# ✓ ML Engine
# ✓ Alerting Service
# ✓ Frontend
```

---

## ⚡ Alternativa Rápida: Deploy Solo del ETL Pipeline

Si solo quieres actualizar el ETL Pipeline (sin esperar a compilar todo):

```bash
cd sap-soc-hackathon/backend/services/etl-pipeline

# Push directamente
cf push -f manifest.yml

# Verifica que se está ejecutando
cf app soc-etl-pipeline
```

---

## ✅ Verificar el Deploy

```bash
# Ver apps deployadas
cf apps

# Ver logs en tiempo real
cf logs soc-etl-pipeline --recent

# Ver detalles de la app
cf app soc-etl-pipeline
```

**Esperado en logs:**
```
[2026-04-16T20:30:00] Starting ingestion...
[2026-04-16T20:30:05] Done — total=150 system=100 llm=50
[2026-04-16T20:35:00] Starting ingestion...  # Cada 5 minutos
...
```

---

## 🔄 Desplegar una Actualización

Si haces cambios a los servicios:

```bash
# 1. Commit y push a GitHub
git add .
git commit -m "cambios..."
git push origin main

# 2. Hacer build nuevamente
mbt build -t mta_archives

# 3. Redeploy
cf deploy mta_archives/sap-soc-platform_1.0.0.mtar

# O solo el ETL:
cf push -f sap-soc-hackathon/backend/services/etl-pipeline/manifest.yml
```

---

## 🐛 Troubleshooting

### Error: "No such file or directory: mta_archives/..."

```bash
# Asegúrate que estás en la carpeta sap-soc-hackathon
cd sap-soc-hackathon
mbt build -t mta_archives
```

### Error: "Not authenticated. Trying to get a new token"

```bash
# Re-login a Cloud Foundry
cf login -a https://api.cf.us10.hana.ondemand.com
```

### Ver logs de la app deployada

```bash
cf logs soc-etl-pipeline --recent
# o en tiempo real:
cf logs soc-etl-pipeline
```

### Detener/Reiniciar una app

```bash
# Detener
cf stop soc-etl-pipeline

# Reiniciar
cf restart soc-etl-pipeline

# Eliminar
cf delete soc-etl-pipeline
```

---

## 📊 Cambios Realizados

✅ **ETL Pipeline** ahora:
- Se ejecuta **cada 5 minutos** (antes: 30 minutos)
- Corre en modo **DAEMON** automáticamente
- Ingesta logs de SAP API continuamente
- Sincroniza datos a SAP HANA Cloud

---

## 🎯 Próximos Pasos

1. **Instalar CF CLI** si no lo tienes
2. **Instalar MBT** si no lo tienes
3. **Ejecutar los comandos de deploy** (Paso 1-3 arriba)
4. **Verificar logs** para confirmar que funciona

---

## 📝 Notas

- La app está configurada en **manifest.yml** para correr sin ruta expuesta (`no-route: true`)
- Los datos se sincronizan automáticamente cada 5 minutos
- Los logs se pueden ver en tiempo real con `cf logs soc-etl-pipeline`
- Para ver qué datos trae, revisa la tabla `SAP_SYSTEM_LOGS` en HANA

**Última actualización:** Abril 16, 2026
