# Mail - Automatizacion CRM Telecentro

Script de automatizacion con Playwright para login en Telecentro/CRM, busqueda de reclamos, descarga de reportes y generacion de CSVs (original y filtrado) por clasificacion.

## Estructura del proyecto
```text
mail/
├─ src/                 # Implementacion Python
│  ├─ login_telecentro.py
│  └─ dividir_filtrados_por_horario.py
├─ scripts/             # Orquestadores y wrappers reales de cron
│  ├─ informe_ras.sh
│  ├─ informe_ras_ventana1.sh
│  └─ informe_ras_ventana2.sh
├─ downloads/           # Salidas CSV
├─ artifacts/           # Debug HTML/PNG
├─ logs/                # Logs de cron y lock
├─ .env                 # Config local
├─ .env.example         # Plantilla
├─ requirements.txt
├─ README.md
└─ (sin wrappers Python en raiz)
```

## Requisitos
- Linux con Python 3.10+
- Acceso de red a hosts internos (`crm.telecentro.local`, `crmweb.telecentro.local`, etc.)

## Setup rapido
```bash
cd /home/neo/mail
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configuracion
1. Copiar plantilla:
```bash
cp .env.example .env
```
2. Editar `.env` con credenciales e IPs internas.
3. Cargar variables:
```bash
set -a; source .env; set +a
```

## Ejecucion
```bash
source .venv/bin/activate
set -a; source .env; set +a
python3 src/login_telecentro.py
```

Tambien podes ejecutar todo desde un solo runner:
```bash
./scripts/informe_ras.sh
```

Para encadenar scripts extra despues de `login_telecentro.py`:
```bash
./scripts/informe_ras.sh otro_script.py "bash script_post.sh"
```

Ejemplo real del postproceso para dividir por keyword y horario:
```bash
./scripts/informe_ras.sh dividir_filtrados_por_horario.py
```

## Estructura recomendada para cron
La forma mas prolija es:
- `informe_ras.sh`: pipeline base (activa venv, carga .env, ejecuta login + extras)
- `informe_ras_ventana1.sh`: wrapper para ventana 1
- `informe_ras_ventana2.sh`: wrapper para ventana 2

Wrappers:
- `informe_ras_ventana1.sh` ejecuta solo `window1` (dia anterior 15:30 -> dia actual 08:30)
- `informe_ras_ventana2.sh` ejecuta solo `window2` (dia actual 08:30 -> dia actual 15:30)
- Cada wrapper escribe en su propia carpeta:
	- `downloads/divididos/window1`
	- `downloads/divididos/window2`
- Los archivos de salida tienen nombre fijo por ventana+keyword y se reemplazan en cada corrida:
	- `window1 - ENVIAR VT.csv`
	- `window1 - PROBLEMA RESUELTO.csv`
	- `window2 - ENVIAR VT.csv`
	- etc.

Variable de control:
- `RAS_SPLIT_ONLY_WINDOW=window1|window2|all`

Ejemplo de cron (lo configuras vos):
```bash
# 08:30 -> ventana 1
30 8 * * * cd /home/neo/mail && ./scripts/informe_ras_ventana1.sh >> logs/cron_ventana1.log 2>&1

# 15:30 -> ventana 2
30 15 * * * cd /home/neo/mail && ./scripts/informe_ras_ventana2.sh >> logs/cron_ventana2.log 2>&1
```

Tip operativo:
- crear carpeta de logs: `mkdir -p /home/neo/mail/logs`

Bloqueo de concurrencia (`flock`):
- `informe_ras.sh` usa lock para evitar corridas superpuestas.
- Si otra ejecucion ya esta activa, la nueva se omite de forma segura.
- Variables opcionales:
	- `RAS_LOCK_FILE` (default: `logs/informe_ras.lock`)
	- `RAS_LOCK_WAIT_SECONDS` (default: `0`, no espera)

Tambien podes correr solo el postproceso:
```bash
source .venv/bin/activate
set -a; source .env; set +a
python3 src/dividir_filtrados_por_horario.py
```

## Salidas
En `downloads/` se generan, por cada clasificacion:
- `NOMBRE_CLASIFICACION - original.csv`
- `NOMBRE_CLASIFICACION - filtrado.csv`

El CSV filtrado contiene:
- `RECLAMO ID`
- `CLIENTE NUMERO`
- `Motivo` (solo keyword detectada)

Keywords consideradas:
- `FALLA MASIVA`
- `PROBLEMA RESUELTO`
- `ENVIAR VT`
- `SIN FALLA`

## Variables importantes (`.env`)
- `TELECENTRO_CLASIFICACIONES`: lista separada por `|` o `,`
- `TELECENTRO_LOOKBACK_DAYS`: ventana de fechas hacia atras
- `CRMWEB_TARGET_IP`, `APICRM_TARGET_IP`, `CRMREP_TARGET_IP`: enrutamiento interno
- `CRM_FORCE_HOST_MAP`: `auto` o `1` para forzar mapeo
- `RAS_WINDOW1_*` y `RAS_WINDOW2_*`: ventanas para dividir por horario
- `RAS_SPLIT_OUTPUT_DIR`: carpeta de salida de CSVs divididos

## Migracion a otro servidor
1. Copiar carpeta del proyecto (sin `.venv` y sin `.env`).
2. Crear nuevo `.venv` en destino e instalar dependencias.
3. Crear `.env` local con credenciales e IPs del entorno destino.
4. Ejecutar igual que en este servidor.
