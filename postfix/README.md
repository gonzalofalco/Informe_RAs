# Postfix relay setup

Este directorio contiene una base para configurar Postfix como relay SMTP usando:

- Relay host: `[10.190.89.55]:25`

## Flujo recomendado

1. Instalar paquetes de Postfix.
2. Aplicar los parametros de `main.cf.example` en `/etc/postfix/main.cf`.
3. Recargar servicio.
4. Probar envio.

Tambien podes usar el instalador automatizado de este directorio:

```bash
sudo bash postfix/install_and_verify.sh
```

## Debian/Ubuntu (referencia)

```bash
sudo apt-get update
sudo apt-get install -y postfix mailutils
```

Al instalar, elegir **Satellite system** (o configuracion minima) y luego aplicar los parametros.

## RHEL/CentOS/Rocky (referencia)

```bash
sudo dnf install -y postfix mailx
sudo systemctl enable --now postfix
```

## Aplicar configuracion sugerida

Revisar y adaptar `main.cf.example`.
Luego copiar sus claves a `/etc/postfix/main.cf`.

```bash
sudo postconf -e "relayhost = [10.190.89.55]:25"
sudo postconf -e "inet_interfaces = loopback-only"
sudo postconf -e "mydestination = localhost"
sudo postconf -e "mynetworks = 127.0.0.0/8 [::1]/128"
sudo postconf -e "smtp_tls_security_level = may"
sudo postconf -e "smtp_tls_loglevel = 1"
sudo systemctl restart postfix
```

## Probar envio

```bash
echo "Prueba relay postfix" | mail -s "Test Postfix Relay" destino@empresa.com
```

## Uso con archivo .env (TO/CC/BCC)

Se agrego soporte para variables de entorno en `test_send.sh`.
El script carga automaticamente `postfix/.env`.

Variables disponibles:

- `MAIL_TO`: destinatario principal.
- `MAIL_CC`: copia visible (multiples con coma).
- `MAIL_BCC`: copia oculta (multiples con coma).
- `MAIL_FROM`: remitente visible opcional.
- `MAIL_SUBJECT`: asunto por defecto.
- `MAIL_BODY`: cuerpo por defecto.

Ejecutar:

```bash
cd postfix
./test_send.sh
```

Tambien podes sobreescribir TO por parametro:

```bash
./test_send.sh otro@empresa.com
```

## Logs utiles

```bash
sudo tail -f /var/log/mail.log
# o en RHEL:
sudo tail -f /var/log/maillog
```

## Cola de correos

```bash
mailq
postqueue -p
```

## Notas

- Si el relay en `10.190.89.55:25` restringe por IP origen, hay que habilitar la IP de este host.
- Si luego te piden autenticacion SMTP (usuario/clave), agregamos `sasl_passwd`.

## Problema comun: multiples PTR / identidad inconsistente

Si el relay rechaza con mensajes tipo `reverse DNS mismatch`, `bad HELO`, `multiple PTR` o similares:

- Forzar una sola identidad FQDN para `myhostname` y `smtp_helo_name`.
- Forzar una sola IP de salida SMTP con `smtp_bind_address`.
- Evitar duplicados/conflictos en `/etc/hosts`.

Script recomendado:

```bash
sudo FQDN=srv.OPERACIONES032telecentro.local SHORT_HOST=srv REAL_IP=192.168.112.111 \
	bash postfix/fix_hosts_fqdn_realip.sh
```

Validaciones rapidas:

```bash
postconf -n | grep -E '^(myhostname|smtp_helo_name|smtp_bind_address)\s*='
hostname -f
getent hosts srv.OPERACIONES032telecentro.local
```

Nota: el PTR real lo define DNS (no `/etc/hosts`). Si el PTR de `REAL_IP` no coincide con tu FQDN canonico, hay que pedir ajuste al equipo de DNS/red.

## Alternativa posible: SMTP autenticado (587)

En este entorno se valido que el host `10.190.89.55` acepta conexion TLS en `587`
y anuncia `AUTH PLAIN LOGIN`.

Importante: el hecho de tener `AUTH` disponible no garantiza por si solo que el relay
ignore validaciones de hostname/PTR. Eso depende de la politica del servidor.

Configurar Postfix con credenciales SMTP:

```bash
sudo SMTP_USER='usuario' SMTP_PASS='clave' bash postfix/configure_submission_auth.sh
```

`SMTP_USER` y `SMTP_PASS` deben ser credenciales reales habilitadas por el equipo
de correo para usar ese relay (normalmente una casilla/servicio autorizada).

Opcionalmente podes sobreescribir host/puerto:

```bash
sudo SMTP_HOST=10.190.89.55 SMTP_PORT=587 SMTP_USER='usuario' SMTP_PASS='clave' \
	bash postfix/configure_submission_auth.sh
```

Luego probar envio:

```bash
cd postfix
./test_send.sh
```

Si queres volver al relay sin auth:

```bash
sudo postconf -e 'relayhost = [10.190.89.55]:25'
sudo postconf -X smtp_sasl_auth_enable
sudo postconf -X smtp_sasl_password_maps
sudo postconf -X smtp_sasl_security_options
sudo postconf -X smtp_sasl_tls_security_options
sudo postconf -e 'smtp_tls_security_level = may'
sudo postconf -X smtp_tls_wrappermode
sudo systemctl restart postfix
```
