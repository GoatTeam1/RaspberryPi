import json, os, pathlib, sys

def env_bool(name, default=False):
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1","true","yes","y","on")

def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except:
        return default

def add_handler_handlers(cfg):
    handlers = cfg["logger"]["kwargs"]["handlers"]

    if env_bool("ENABLE_SMTP"):
        # Python logging SMTPHandler per documentación
        # mailhost, fromaddr, toaddrs, subject, credentials, secure []
        handlers["SMTP"] = {
            "class": "logging.handlers.SMTPHandler",
            "mailhost": [os.getenv("SMTP_HOST","smtp.local"), env_int("SMTP_PORT",25)],
            "fromaddr": os.getenv("ALERT_FROM","canary@local"),
            "toaddrs": [os.getenv("ALERT_TO","alerts@local")],
            "subject": "OpenCanary Alert",
            "credentials": [os.getenv("SMTP_USERNAME",""), os.getenv("SMTP_PASSWORD","")],
            "secure": []
        }

    if env_bool("ENABLE_WEBHOOK"):
        # WebhookHandler propio de OpenCanary
        handlers["Webhook"] = {
            "class": "opencanary.logger.WebhookHandler",
            "url": os.getenv("WEBHOOK_URL",""),
            "method": "POST",
            "data": {"message": "%(message)s"},
            "status_code": 200
        }

    if env_bool("ENABLE_SYSLOG"):
        handlers["syslog"] = {
            "class": "logging.handlers.SysLogHandler",
            "kwargs": {"address": [os.getenv("SYSLOG_HOST","127.0.0.1"), env_int("SYSLOG_PORT",514)]},
            "formatter": "plain"
        }

def main():
    tmpl_path = pathlib.Path("/opt/opencanary/opencanary.conf.tmpl.json")
    out_path  = pathlib.Path("/etc/opencanaryd")
    out_path.mkdir(parents=True, exist_ok=True)
    conf_path = out_path / "opencanary.conf"

    with tmpl_path.open("r", encoding="utf-8") as f:
        raw = f.read()

    # Sustitución superficial ${VAR}
    def replace_env(text):
        import re
        def repl(m):
            key = m.group(1)
            return os.getenv(key, m.group(0))
        return re.sub(r"\$\{([A-Z0-9_]+)\}", repl, raw)

    # Reemplaza booleans/enteros embebidos
    text = replace_env(raw)
    cfg = json.loads(text)

    # Normaliza booleans/puertos de servicios desde env
    for key in list(cfg.keys()):
        if key.endswith(".enabled"):
            env_var = key.split(".")[0].upper() + "_ENABLED"
            cfg[key] = env_bool(env_var, cfg[key])
        if key.endswith(".port"):
            env_var = key.split(".")[0].upper() + "_PORT"
            cfg[key] = env_int(env_var, cfg[key])

    add_handler_handlers(cfg)

    # Asegura carpeta de logs
    pathlib.Path("/data").mkdir(exist_ok=True, parents=True)

    with conf_path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    # Lanza OpenCanary en foreground (ideal para Docker)
    os.execvp("opencanaryd", ["opencanaryd", "-c", str(conf_path), "--debug"])

if __name__ == "__main__":
    main()
