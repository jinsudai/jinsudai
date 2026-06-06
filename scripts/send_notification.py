#!/usr/bin/env python3
"""Script pour envoyer des notifications (email + log) après chaque tâche."""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Charge les variables d'environnement depuis .env.secrets
load_dotenv(find_dotenv(".env.secrets"), override=True)


def load_settings():
    """Charge la configuration depuis .vibe_settings"""
    settings_path = Path(__file__).parent.parent / ".vibe_settings"
    if not settings_path.exists():
        raise FileNotFoundError("Fichier .vibe_settings introuvable")
    
    with open(settings_path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_email(api_key, from_email, to_email, subject, body):
    """Envoie un email via Resend API"""
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "html": f"<pre>{body.replace(chr(10), '<br>')}</pre>",
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.RequestException as e:
        return False, str(e)


def write_log(log_file, message):
    """Écrit dans le fichier de log"""
    log_path = Path(__file__).parent.parent / log_file
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}\n"
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_message)


def notify(task_name, details=""):
    """Envoie une notification pour une tâche terminée"""
    settings = load_settings()
    config = settings.get("notifications", {})
    
    if not config.get("enabled", False):
        return
    
    # Email notification
    email_config = config.get("email", {})
    if email_config.get("provider") == "resend":
        api_key = os.environ.get(email_config.get("api_key_env", "RESEND_API_KEY"))
        from_email = os.environ.get(email_config.get("from_env", "RESEND_FROM_EMAIL"))
        to_email = os.environ.get(email_config.get("to_env", "RESEND_TO_EMAIL"))
        
        if api_key and from_email and to_email:
            subject = email_config.get("subject_template", "[Vibe] {task_name}").format(
                task_name=task_name
            )
            body = email_config.get("body_template", "Tâche terminée: {task_name}\nDétails: {details}").format(
                task_name=task_name,
                details=details,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            success, result = send_email(api_key, from_email, to_email, subject, body)
            if not success:
                print(f"[ERREUR EMAIL] {result}")
        else:
            print("[AVERTISSEMENT] Variables Resend manquantes dans l'environnement")
    
    # Log file
    log_file = config.get("log_file")
    if log_file:
        write_log(log_file, f"Tâche terminée: {task_name}")
    
    # Console
    console_format = config.get("console_format")
    if console_format:
        print(console_format.format(task_name=task_name, details=details))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        notify(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
