# SentinelPi

Honeypot reproducible y endurecido para Raspberry Pi basado en **OpenCanary** (con opción de ampliar a Cowrie/T-Pot). Provee emulación de servicios comunes, registro estructurado de eventos y canales de alerta (archivo, SMTP, Webhook y Syslog) usando **Docker** y **docker-compose**.

> **Objetivo**: desplegar un honeypot realista en una Raspberry Pi con mínima fricción, aislado, auditable y listo para integrarse a un SIEM o pipeline de respuesta a incidentes.

---

## Índice

- [Arquitectura](#arquitectura)
- [Características](#características)
- [Requisitos](#requisitos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación rápida (Quickstart)](#instalación-rápida-quickstart)
- [Configuración](#configuración)
  - [.env](#env)
  - [Servicios emulados](#servicios-emulados)
  - [Alertas y logging](#alertas-y-logging)
- [Operación](#operación)
  - [Arranque, parada y estado](#arranque-parada-y-estado)
  - [Verificación y pruebas](#verificación-y-pruebas)
  - [Logs y conservación de evidencias](#logs-y-conservación-de-evidencias)
- [Endurecimiento](#endurecimiento)
  - [Aislamiento de red](#aislamiento-de-red)
  - [Límites de egreso](#límites-de-egreso)
  - [Colisiones de puertos](#colisiones-de-puertos)
- [Mantenimiento](#mantenimiento)
  - [Rotación de logs](#rotación-de-logs)
  - [Actualizaciones](#actualizaciones)
  - [Respaldo y restauración](#respaldo-y-restauración)
- [Integración con SIEM](#integración-con-siem)
- [Solución de problemas](#solución-de-problemas)
- [Preguntas frecuentes](#preguntas-frecuentes)
- [Hoja de ruta](#hoja-de-ruta)
- [Glosario de términos](#glosario-de-términos)
- [Advertencias legales](#advertencias-legales)
- [Licencia](#licencia)

---

## Arquitectura

- **Contenedor principal**: OpenCanary (Python) ejecutado en **modo de red `host`** para exponer puertos “bien conocidos” sin NAT y mejorar la verosimilitud del señuelo.
- **Configuración dinámica**: un *entrypoint* genera `opencanary.conf` a partir de un template (`opencanary.conf.tmpl.json`) y variables de entorno definidas en `.env`.
- **Persistencia**: los eventos se guardan en `./data/opencanary.log` (montado en `/data` del contenedor).
- **Alertas**: opt-in por `.env` hacia SMTP (correo), Webhook (HTTP POST) o Syslog (UDP/TCP).

> **Nota**: el modo `host` solo está disponible y recomendado en Linux. Para Raspberry Pi OS / Ubuntu Server en ARM es la opción más simple y precisa.

---

## Características

- Emulación de múltiples servicios (HTTP, Telnet, MySQL, FTP, SMB, RDP, TFTP, NTP, SSH opcional).
- Banners y *skins* configurables (por ejemplo, “NAS login” en HTTP).
- Ignora tu IP local y loopback para reducir ruido en logs.
- Salida JSON plana compatible con parsers de SIEM.
- Deploy reproducible (Dockerfile multi-arquitectura ARM/x86).
- Script opcional de endurecimiento de egreso vía `iptables`.

---

## Requisitos

- **Hardware**: Raspberry Pi 3B+ o superior (recomendado Pi 4/5), 2 GB RAM mínimo.
- **SO**: Raspberry Pi OS (64-bit) o Ubuntu Server (ARM64).
- **Software**: Docker Engine y Docker Compose Plugin instalados.
- **Red**: IP estática o reserva DHCP para la Pi; segmento aislado o VLAN dedicada recomendado.

---

## Estructura del proyecto

```
SentinelPi/
├─ .env
├─ docker-compose.yml
├─ opencanary/
│  ├─ Dockerfile
│  ├─ entrypoint.py
│  └─ opencanary.conf.tmpl.json
├─ hardening/
│  └─ outbound-lockdown.sh         # opcional
└─ data/                            # se crea en primera ejecución; contiene opencanary.log
```

---

## Instalación rápida (Quickstart)

```bash
# 1) Clona o copia el proyecto a tu Raspberry Pi
cd /opt
sudo git clone <repo> SentinelPi
cd SentinelPi

# 2) Edita variables mínimas en .env (HOST_IP, servicios a habilitar)
nano .env

# 3) Construye e inicia
sudo docker compose build
sudo docker compose up -d

# 4) Sigue los logs
sudo docker logs -f opencanary
```

**Verifica puertos** desde otra máquina:
```bash
nmap -sS -Pn -p 21,22,23,80,3306 <IP_DEL_PI>
curl -I http://<IP_DEL_PI>/
telnet <IP_DEL_PI> 23
mysql -h <IP_DEL_PI> -P 3306 -u root -ppassword
```

---

## Configuración

### `.env`

Variables principales (ejemplo resumido):
```dotenv
TZ=America/Mexico_City
NODE_ID=pi-canary-01
HOST_IP=192.168.1.50

HTTP_ENABLED=true
HTTP_PORT=80
TELNET_ENABLED=true
TELNET_PORT=23
MYSQL_ENABLED=true
MYSQL_PORT=3306
SSH_ENABLED=false

ENABLE_SMTP=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=usuario@gmail.com
SMTP_PASSWORD=APP_PASSWORD
ALERT_FROM=canary@tudominio.com
ALERT_TO=alertas@tudominio.com

ENABLE_WEBHOOK=false
WEBHOOK_URL=https://tu-endpoint/webhook

ENABLE_SYSLOG=false
SYSLOG_HOST=127.0.0.1
SYSLOG_PORT=514
```

> Mantén `SSH_ENABLED=false` si usas el SSH real de la Raspberry Pi en el puerto 22.

### Servicios emulados

Cada servicio tiene sufijos `.enabled` y `.port`. Activa solo los necesarios para el perfil de “señuelo” que busques. Ejemplos comunes:
- **HTTP (80)** con *skin* de NAS/login básico.
- **Telnet (23)** para atracción de scripts de fuerza bruta.
- **MySQL (3306)** con banner típico.
- **FTP (21), SMB (445), RDP (3389), TFTP (69), NTP (123)** opcionales.

### Alertas y logging

- **Archivo**: siempre activo, `./data/opencanary.log`.
- **SMTP**: requiere `ENABLE_SMTP=true` y credenciales válidas (usa *App Password* si empleas Gmail).
- **Webhook**: `ENABLE_WEBHOOK=true` + `WEBHOOK_URL` (recibe `{"message":"<evento>"}`).
- **Syslog**: `ENABLE_SYSLOG=true` + `SYSLOG_HOST`/`SYSLOG_PORT` (parsers del SIEM).

---

## Operación

### Arranque, parada y estado
```bash
sudo docker compose up -d        # iniciar
sudo docker compose ps           # estado
sudo docker compose logs -f      # logs de todos
sudo docker logs -f opencanary   # logs solo del honeypot
sudo docker compose down         # detener
```

### Verificación y pruebas

Ejecuta algunas conexiones de prueba (desde otra máquina) para generar eventos. Revisa `./data/opencanary.log`. Los registros son líneas JSON; cada entrada incluye timestamp, servicio, IP de origen, acción y metadatos del intento.

### Logs y conservación de evidencias

- Copia y **no alteres** los archivos si van a utilizarse como evidencia.
- Para exportar con *hash* de integridad:
  ```bash
  sha256sum data/opencanary.log > data/opencanary.log.sha256
  ```

---

## Endurecimiento

### Aislamiento de red

- Coloca la Pi en **VLAN/segmento aislado** o DMZ con reglas estrictas hacia tu red interna.
- No mezcles servicios reales de producción en el mismo host que el honeypot.

### Límites de egreso

Opcional: bloquea egreso excepto DNS/NTP/SMTP/HTTPS (para alertas).
```bash
sudo bash hardening/outbound-lockdown.sh
```

### Colisiones de puertos

- Si la Pi ya usa **SSH:22** o **HTTP:80**, **no habilites** esos servicios en el honeypot o mueve el servicio real a otro puerto.
- Verifica con `sudo ss -lntup` qué puertos están ocupados.

---

## Mantenimiento

### Rotación de logs

Configura `logrotate` en el host (ejemplo):
```
/opt/SentinelPi/data/opencanary.log {
  weekly
  rotate 8
  copytruncate
  compress
  missingok
  notifempty
}
```

### Actualizaciones
```bash
# actualizar la imagen y reiniciar
sudo docker compose build --no-cache
sudo docker compose up -d
```

### Respaldo y restauración

- **Respaldo**: `data/` (logs) + tu `.env`.
- **Restauración**: reinstala dependencias y vuelve a levantar con los mismos archivos.

---

## Integración con SIEM

- **Syslog**: habilita `ENABLE_SYSLOG=true` y apunta a tu colector (UDP/TCP 514).
- **Webhook**: envía eventos a un *ingestor* HTTP (por ejemplo, un receptor que normalice y reenvíe a tu SIEM).
- **Estructura de evento**: JSON plano por línea; mapea campos clave (fecha, servicio, ip_origen, acción, credenciales si aplica).

---

## Solución de problemas

- **No veo puertos abiertos**: confirma `network_mode: host` y que el servicio esté `*_ENABLED=true` en `.env`.
- **SMTP no envía**: habilita puerto 587/TLS en tu firewall, usa *App Password* y revisa `SMTP_HOST/PORT/USERNAME/PASSWORD`.
- **Conflicto con SSH/HTTP reales**: desactiva esos servicios en `.env` o mueve el servicio real a otro puerto.
- **Logs vacíos**: genera tráfico desde otra máquina (curl/telnet/nmap) y revisa `opencanary.log` en `./data/`.

---

## Preguntas frecuentes

**¿Puedo añadir un honeypot de alta interacción (SSH/Telnet)?**  
Sí. Integra **Cowrie** como servicio adicional en el mismo `docker-compose.yml` para capturar sesiones y binarios. Requiere almacenamiento y control de riesgos adicionales.

**¿Puedo usar SentinelPi sin Docker?**  
Es posible instalar OpenCanary nativo, pero se pierde reproducibilidad y aislamiento. La ruta soportada aquí es Docker.

**¿Se puede exponer a Internet?**  
Técnicamente sí, pero **no recomendado** sin una DMZ/vuln‑lab y monitoreo continuo. Preferible iniciar en red interna segmentada.

---

## Hoja de ruta

- Plantillas de ingestión (Elastic/Chronicle).
- Servicio opcional Cowrie para SSH/Telnet de alta interacción.
- Dashboard de métricas (Grafana/Prometheus) opcional.
- Playbooks de IR para eventos comunes (credential stuffing, escaneo, RDP/SMB probes).

---

## Glosario de términos

- **Honeypot**: sistema señuelo diseñado para atraer, registrar y estudiar actividades maliciosas, sin prestar servicios productivos reales.
- **OpenCanary**: honeypot *low‑interaction* en Python que emula múltiples servicios y genera eventos estructurados. Es ligero y sencillo de desplegar.
- **Cowrie**: honeypot de **alta interacción** para SSH/Telnet que permite sesiones falsas y captura de comandos/archivos. Complementa a OpenCanary.
- **T‑Pot**: distribución que agrupa varios honeypots e integraciones; mayor cobertura pero más consumo y complejidad.
- **Low‑interaction vs High‑interaction**: los primeros simulan protocolos y responden con banners/respuestas simples; los segundos permiten interacción más profunda (sesiones, archivos), elevando valor forense y riesgo.
- **Docker**: plataforma de contenedores que empaqueta aplicaciones con sus dependencias para ejecución aislada y reproducible.
- **Docker Compose**: herramienta para definir y ejecutar aplicaciones multi‑contenedor usando un archivo `docker-compose.yml`.
- **`network_mode: host`**: modo de red de Docker que hace que el contenedor comparta la pila de red del host (Linux), evitando NAT y exponiendo puertos directamente.
- **NAT (Network Address Translation)**: traducción de direcciones/puertos que puede interferir con la verosimilitud de algunos honeypots cuando se hace *port‑mapping*.
- **SIEM (Security Information and Event Management)**: plataforma que centraliza, normaliza y correlaciona eventos de seguridad para detección y respuesta.
- **Syslog**: protocolo de registro de eventos (UDP/TCP 514) ampliamente soportado por sistemas y dispositivos de red.
- **Webhook**: mecanismo de **push** vía HTTP/HTTPS donde un sistema envía eventos a una URL destino (por ejemplo, a un ingestor propio o a un servidor de automatización).
- **SMTP**: protocolo de correo saliente. En entornos con autenticación moderna (por ejemplo Gmail), se recomienda usar **App Password** en lugar de la contraseña de la cuenta.
- **VLAN**: red local virtual que segmenta el tráfico dentro de la misma infraestructura física para aislar dominios de broadcast y reducir superficie de ataque lateral.
- **DMZ (Demilitarized Zone)**: zona de red perimetral separada de la red interna, pensada para exponer servicios de forma controlada.
- **Banner**: cadena de identificación que ciertos servicios muestran al conectarse (versión, producto). En honeypots ayuda a simular software verosímil.
- **Skin**: apariencia o *plantilla* de interfaz (p. ej., pantalla de login HTTP). OpenCanary incluye algunas para simular dispositivos/servicios.
- **JSON Lines (JSONL)**: formato donde cada línea del archivo es un objeto JSON independiente; útil para procesar y enviar a SIEMs.
- **Logrotate**: herramienta de Linux para rotar, comprimir y gestionar historiales de logs.
- **Servicios emulados comunes**:
  - **HTTP (80)**, **Telnet (23)**, **SSH (22)**, **FTP (21)**, **MySQL (3306)**, **SMB (445)**, **RDP (3389)**, **TFTP (69)**, **NTP (123)**.
- **Nmap**: escáner de red usado para descubrir hosts y servicios (útil para verificar exposición del honeypot).
- **Hash de integridad**: firma (por ejemplo, SHA‑256) para garantizar que un archivo de log no ha sido alterado después de su recolección.

---

## Advertencias legales

Opera SentinelPi únicamente en redes que administras y con autorización explícita. No ejecutes artefactos capturados en la misma máquina del honeypot. Cumple las leyes y políticas internas aplicables. El equipo mantenedor no se hace responsable del uso indebido.

---

## Licencia

Este proyecto se publica bajo **MIT License** por defecto. Puedes reemplazar la licencia según políticas de tu organización.
