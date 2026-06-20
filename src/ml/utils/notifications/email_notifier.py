"""
Module de notification par email pour les événements SFTP.

Ce module fournit une classe pour envoyer des notifications par email
lorsqu'un fichier est reçu sur le serveur SFTP.

Supporte deux providers:
- SMTP: Configuration SMTP traditionnelle
- Resend: Utilisation de l'API Resend

Exemple d'utilisation avec SMTP:
    from ml.utils.notifications.email_notifier import EmailNotifier
    
    notifier = EmailNotifier(
        provider="smtp",
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        sender_email="sender@example.com",
        sender_password="password",
        recipient_emails=["recipient1@example.com"]
    )

Exemple d'utilisation avec Resend:
    from ml.utils.notifications.email_notifier import EmailNotifier
    
    notifier = EmailNotifier(
        provider="resend",
        resend_api_key="re_xxxxx",
        from_email="noreply@yourdomain.com",
        recipient_emails=["recipient1@example.com"]
    )
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Classe pour envoyer des notifications par email.
    Supporte SMTP et Resend.
    """

    def __init__(
        self,
        provider: str = "smtp",
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        recipient_emails: Optional[List[str]] = None,
        use_tls: bool = True,
        resend_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise le notificateur email.

        Args:
            provider: Type de provider ("smtp" ou "resend")
            smtp_server: Serveur SMTP (ex: smtp.gmail.com)
            smtp_port: Port SMTP (ex: 587 pour TLS, 465 pour SSL)
            sender_email: Email de l'expéditeur (SMTP)
            sender_password: Mot de passe de l'expéditeur (SMTP)
            recipient_emails: Liste des emails des destinataires
            use_tls: Utiliser TLS (SMTP)
            resend_api_key: Clé API Resend
            from_email: Email expéditeur (Resend)
            config: Dictionnaire de configuration (optionnel, priorité sur les paramètres individuels)
        """
        # Priorité: config > paramètres individuels > variables d'environnement
        if config:
            self.provider = config.get("provider", provider)
            self.smtp_server = config.get("smtp", {}).get("server", smtp_server)
            self.smtp_port = config.get("smtp", {}).get("port", smtp_port)
            self.use_tls = config.get("smtp", {}).get("use_tls", use_tls)
            self.sender_email = config.get("sender_email", sender_email)
            self.sender_password = config.get("sender_password", sender_password)
            self.recipient_emails = config.get("recipient_emails", recipient_emails)
            self.resend_api_key = config.get("resend", {}).get("api_key", resend_api_key) or os.getenv("RESEND_API_KEY")
            self.from_email = config.get("resend", {}).get("from_email", from_email)
        else:
            self.provider = provider
            self.smtp_server = smtp_server
            self.smtp_port = smtp_port
            self.sender_email = sender_email
            self.sender_password = sender_password
            self.recipient_emails = recipient_emails
            self.use_tls = use_tls
            self.resend_api_key = resend_api_key or os.getenv("RESEND_API_KEY")
            self.from_email = from_email

        # Validation
        if self.provider == "smtp":
            if not self.smtp_server or not self.sender_email or not self.sender_password:
                raise ValueError("Configuration SMTP incomplète: smtp_server, sender_email et sender_password requis")
        elif self.provider == "resend":
            if not self.resend_api_key or not self.from_email:
                raise ValueError("Configuration Resend incomplète: resend_api_key et from_email requis")
        else:
            raise ValueError(f"Provider non supporté: {self.provider}. Options: 'smtp', 'resend'")

        if not self.recipient_emails:
            raise ValueError("recipient_emails est requis")

        logger.info(f"Notificateur email initialisé (provider: {self.provider}) pour {len(self.recipient_emails)} destinataires")

    def _send_email(
        self,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Envoie un email selon le provider configuré.

        Args:
            subject: Sujet de l'email
            body: Corps du texte de l'email
            html_body: Corps HTML de l'email (optionnel)

        Returns:
            True si succès, False sinon
        """
        if self.provider == "smtp":
            return self._send_email_smtp(subject, body, html_body)
        elif self.provider == "resend":
            return self._send_email_resend(subject, body, html_body)
        else:
            logger.error(f"Provider non supporté: {self.provider}")
            return False

    def _send_email_smtp(
        self,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Envoie un email via SMTP.

        Args:
            subject: Sujet de l'email
            body: Corps du texte de l'email
            html_body: Corps HTML de l'email (optionnel)

        Returns:
            True si succès, False sinon
        """
        try:
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipient_emails)
            msg['Subject'] = subject

            # Ajouter le corps texte
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Ajouter le corps HTML si fourni
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)

            # Connexion au serveur SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                # Authentification
                server.login(self.sender_email, self.sender_password)

                # Envoi
                server.send_message(msg)

            logger.info(f"Email SMTP envoyé avec succès: {subject}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email SMTP: {e}")
            return False

    def _send_email_resend(
        self,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Envoie un email via l'API Resend.

        Args:
            subject: Sujet de l'email
            body: Corps du texte de l'email
            html_body: Corps HTML de l'email (optionnel)

        Returns:
            True si succès, False sinon
        """
        try:
            import resend

            # Utiliser le corps HTML si disponible, sinon le corps texte
            content = html_body if html_body else body
            content_type = "html" if html_body else "text"

            # Envoyer à tous les destinataires
            for recipient in self.recipient_emails:
                params = {
                    "from": self.from_email,
                    "to": [recipient],
                    "subject": subject,
                    content_type: content
                }

                resend.Emails.send(params)

            logger.info(f"Email Resend envoyé avec succès: {subject}")
            return True

        except ImportError:
            logger.error("La bibliothèque resend n'est pas installée. Installez-la avec: pip install resend")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email Resend: {e}")
            return False

    def notify_file_received(
        self,
        filename: str,
        file_size: int,
        remote_path: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Notifie la réception d'un fichier sur le serveur SFTP.

        Args:
            filename: Nom du fichier
            file_size: Taille du fichier en octets
            remote_path: Chemin distant du fichier
            timestamp: Timestamp de réception (défaut: maintenant)

        Returns:
            True si succès, False sinon
        """
        if timestamp is None:
            timestamp = datetime.now()

        subject = f"[SFTP] Nouveau fichier reçu: {filename}"

        # Corps texte
        body = f"""
Nouveau fichier reçu sur le serveur SFTP

Détails:
- Fichier: {filename}
- Taille: {file_size:,} octets ({file_size / 1024:.2f} KB)
- Chemin distant: {remote_path}
- Date de réception: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Le fichier sera traité automatiquement et les valeurs réelles seront mises à jour dans la base de données.

---
Ceci est un message automatique du système de traitement SFTP.
"""

        # Corps HTML
        html_body = f"""
<html>
<body>
    <h2>Nouveau fichier reçu sur le serveur SFTP</h2>
    
    <table border="1" cellpadding="10" cellspacing="0">
        <tr>
            <td><strong>Fichier</strong></td>
            <td>{filename}</td>
        </tr>
        <tr>
            <td><strong>Taille</strong></td>
            <td>{file_size:,} octets ({file_size / 1024:.2f} KB)</td>
        </tr>
        <tr>
            <td><strong>Chemin distant</strong></td>
            <td>{remote_path}</td>
        </tr>
        <tr>
            <td><strong>Date de réception</strong></td>
            <td>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
    </table>
    
    <p>Le fichier sera traité automatiquement et les valeurs réelles seront mises à jour dans la base de données.</p>
    
    <hr>
    <p><em>Ceci est un message automatique du système de traitement SFTP.</em></p>
</body>
</html>
"""

        return self._send_email(subject, body, html_body)

    def notify_drift_detected(
        self,
        drift_results: Dict[str, Any],
        model_name: str,
        run_id: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Notifie la détection de drift dans le modèle.

        Args:
            drift_results: Résultats de la détection de drift
            model_name: Nom du modèle
            run_id: ID de la run
            timestamp: Timestamp de détection (défaut: maintenant)

        Returns:
            True si succès, False sinon
        """
        if timestamp is None:
            timestamp = datetime.now()

        subject = f"[DRIFT ALERT] Drift détecté pour le modèle {model_name}"

        # Extraire les informations de drift
        data_drift = drift_results.get('data_drift', {})
        concept_drift = drift_results.get('concept_drift', {})
        overall_drift = drift_results.get('overall_drift_detected', False)

        # Corps texte
        body = f"""
ALERTE DE DRIFT DÉTECTÉE

Modèle: {model_name}
Run ID: {run_id}
Date de détection: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Drift global détecté: {overall_drift}

=== DATA DRIFT ===
"""

        if data_drift:
            if data_drift.get('drift_detected'):
                body += "Drift détecté: OUI\n"
                features_drift = data_drift.get('features_drift', {})
                drifted_count = data_drift.get('drifted_features_count', 0)
                total_count = data_drift.get('total_features_analyzed', 0)
                body += f"Features avec drift: {drifted_count}/{total_count}\n"

                for feature, info in features_drift.items():
                    if info.get('drift_detected'):
                        body += f"  - {feature}: PSI={info.get('psi', 0):.4f}\n"
            else:
                body += "Drift détecté: NON\n"
        else:
            body += "Non analysé\n"

        body += """
=== CONCEPT DRIFT ===
"""

        if concept_drift:
            pred_drift = concept_drift.get('prediction_drift', {})
            perf_drift = concept_drift.get('performance_drift', {})

            if pred_drift.get('drift_detected'):
                body += "Drift de prédictions: OUI\n"
                body += f"  - Mean drift: {pred_drift.get('mean_drift', 0):.4f}\n"
                body += f"  - Std drift: {pred_drift.get('std_drift', 0):.4f}\n"
            else:
                body += "Drift de prédictions: NON\n"

            if perf_drift:
                if perf_drift.get('drift_detected'):
                    body += "Drift de performance: OUI\n"
                    body += f"  - MAE drift: {perf_drift.get('mae_drift', 0):.4f}\n"
                    body += f"  - R² drift: {perf_drift.get('r2_drift', 0):.4f}\n"
                else:
                    body += "Drift de performance: NON\n"
        else:
            body += "Non analysé\n"

        body += """
Recommandation: Envisager un retraining du modèle.

---
Ceci est un message automatique du système de monitoring de drift.
"""

        # Corps HTML
        drift_color = "red" if overall_drift else "green"

        html_body = f"""
<html>
<body>
    <h2 style="color: {drift_color}">ALERTE DE DRIFT DÉTECTÉE</h2>
    
    <table border="1" cellpadding="10" cellspacing="0">
        <tr>
            <td><strong>Modèle</strong></td>
            <td>{model_name}</td>
        </tr>
        <tr>
            <td><strong>Run ID</strong></td>
            <td>{run_id}</td>
        </tr>
        <tr>
            <td><strong>Date de détection</strong></td>
            <td>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
        <tr>
            <td><strong>Drift global détecté</strong></td>
            <td style="color: {drift_color}; font-weight: bold;">{'OUI' if overall_drift else 'NON'}</td>
        </tr>
    </table>
    
    <h3>DATA DRIFT</h3>
"""

        if data_drift:
            if data_drift.get('drift_detected'):
                html_body += "<p style='color: red;'><strong>Drift détecté: OUI</strong></p>"
                features_drift = data_drift.get('features_drift', {})
                drifted_count = data_drift.get('drifted_features_count', 0)
                total_count = data_drift.get('total_features_analyzed', 0)
                html_body += f"<p>Features avec drift: {drifted_count}/{total_count}</p>"

                html_body += "<table border='1' cellpadding='5' cellspacing='0'>"
                html_body += "<tr><th>Feature</th><th>PSI</th><th>Drift</th></tr>"
                for feature, info in features_drift.items():
                    drift_color_feature = "red" if info.get('drift_detected') else "green"
                    html_body += f"""
                    <tr>
                        <td>{feature}</td>
                        <td>{info.get('psi', 0):.4f}</td>
                        <td style='color: {drift_color_feature};'>{'OUI' if info.get('drift_detected') else 'NON'}</td>
                    </tr>
                    """
                html_body += "</table>"
            else:
                html_body += "<p style='color: green;'><strong>Drift détecté: NON</strong></p>"
        else:
            html_body += "<p>Non analysé</p>"

        html_body += "<h3>CONCEPT DRIFT</h3>"

        if concept_drift:
            pred_drift = concept_drift.get('prediction_drift', {})
            perf_drift = concept_drift.get('performance_drift', {})

            if pred_drift.get('drift_detected'):
                html_body += "<p style='color: red;'><strong>Drift de prédictions: OUI</strong></p>"
                html_body += "<ul>"
                html_body += f"<li>Mean drift: {pred_drift.get('mean_drift', 0):.4f}</li>"
                html_body += f"<li>Std drift: {pred_drift.get('std_drift', 0):.4f}</li>"
                html_body += "</ul>"
            else:
                html_body += "<p style='color: green;'><strong>Drift de prédictions: NON</strong></p>"

            if perf_drift:
                if perf_drift.get('drift_detected'):
                    html_body += "<p style='color: red;'><strong>Drift de performance: OUI</strong></p>"
                    html_body += "<ul>"
                    html_body += f"<li>MAE drift: {perf_drift.get('mae_drift', 0):.4f}</li>"
                    html_body += f"<li>R² drift: {perf_drift.get('r2_drift', 0):.4f}</li>"
                    html_body += "</ul>"
                else:
                    html_body += "<p style='color: green;'><strong>Drift de performance: NON</strong></p>"
        else:
            html_body += "<p>Non analysé</p>"

        html_body += """
    <p style='color: orange;'><strong>Recommandation:</strong> Envisager un retraining du modèle.</p>
    
    <hr>
    <p><em>Ceci est un message automatique du système de monitoring de drift.</em></p>
</body>
</html>
"""

        return self._send_email(subject, body, html_body)

    def notify_file_processed(
        self,
        filename: str,
        records_processed: int,
        predictions_updated: int,
        success: bool,
        error_message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Notifie le traitement d'un fichier.

        Args:
            filename: Nom du fichier
            records_processed: Nombre d'enregistrements traités
            predictions_updated: Nombre de prédictions mises à jour
            success: Si le traitement a réussi
            error_message: Message d'erreur si échec
            timestamp: Timestamp du traitement (défaut: maintenant)

        Returns:
            True si succès, False sinon
        """
        if timestamp is None:
            timestamp = datetime.now()

        status = "SUCCÈS" if success else "ÉCHEC"
        subject = f"[SFTP] Traitement fichier: {filename} - {status}"

        # Corps texte
        body = f"""
Résultat du traitement du fichier SFTP

Détails:
- Fichier: {filename}
- Statut: {status}
- Enregistrements traités: {records_processed}
- Prédictions mises à jour: {predictions_updated}
- Date de traitement: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

        if error_message:
            body += f"- Erreur: {error_message}\n"

        body += """
---
Ceci est un message automatique du système de traitement SFTP.
"""

        # Corps HTML
        status_color = "green" if success else "red"
        html_body = f"""
<html>
<body>
    <h2 style="color: {status_color}">Résultat du traitement du fichier SFTP</h2>
    
    <table border="1" cellpadding="10" cellspacing="0">
        <tr>
            <td><strong>Fichier</strong></td>
            <td>{filename}</td>
        </tr>
        <tr>
            <td><strong>Statut</strong></td>
            <td style="color: {status_color}; font-weight: bold;">{status}</td>
        </tr>
        <tr>
            <td><strong>Enregistrements traités</strong></td>
            <td>{records_processed}</td>
        </tr>
        <tr>
            <td><strong>Prédictions mises à jour</strong></td>
            <td>{predictions_updated}</td>
        </tr>
        <tr>
            <td><strong>Date de traitement</strong></td>
            <td>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
"""

        if error_message:
            html_body += f"""
        <tr>
            <td><strong>Erreur</strong></td>
            <td style="color: red;">{error_message}</td>
        </tr>
"""

        html_body += """
    </table>
    
    <hr>
    <p><em>Ceci est un message automatique du système de traitement SFTP.</em></p>
</body>
</html>
"""

        return self._send_email(subject, body, html_body)

    def notify_batch_completed(
        self,
        total_files: int,
        successful: int,
        failed: int,
        total_records: int,
        total_updated: int,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Notifie la complétion d'un traitement par lots.

        Args:
            total_files: Nombre total de fichiers
            successful: Nombre de fichiers traités avec succès
            failed: Nombre de fichiers en échec
            total_records: Nombre total d'enregistrements traités
            total_updated: Nombre total de prédictions mises à jour
            timestamp: Timestamp du traitement (défaut: maintenant)

        Returns:
            True si succès, False sinon
        """
        if timestamp is None:
            timestamp = datetime.now()

        success_rate = (successful / total_files * 100) if total_files > 0 else 0

        subject = f"[SFTP] Traitement par lots terminé: {successful}/{total_files} fichiers"

        # Corps texte
        body = f"""
Rapport de traitement par lots SFTP

Résumé:
- Fichiers totaux: {total_files}
- Succès: {successful}
- Échecs: {failed}
- Taux de succès: {success_rate:.2f}%
- Enregistrements traités: {total_records}
- Prédictions mises à jour: {total_updated}
- Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

---
Ceci est un message automatique du système de traitement SFTP.
"""

        # Corps HTML
        html_body = f"""
<html>
<body>
    <h2>Rapport de traitement par lots SFTP</h2>
    
    <table border="1" cellpadding="10" cellspacing="0">
        <tr>
            <td><strong>Fichiers totaux</strong></td>
            <td>{total_files}</td>
        </tr>
        <tr>
            <td><strong>Succès</strong></td>
            <td style="color: green;">{successful}</td>
        </tr>
        <tr>
            <td><strong>Échecs</strong></td>
            <td style="color: red;">{failed}</td>
        </tr>
        <tr>
            <td><strong>Taux de succès</strong></td>
            <td>{success_rate:.2f}%</td>
        </tr>
        <tr>
            <td><strong>Enregistrements traités</strong></td>
            <td>{total_records}</td>
        </tr>
        <tr>
            <td><strong>Prédictions mises à jour</strong></td>
            <td>{total_updated}</td>
        </tr>
        <tr>
            <td><strong>Date</strong></td>
            <td>{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
    </table>
    
    <hr>
    <p><em>Ceci est un message automatique du système de traitement SFTP.</em></p>
</body>
</html>
"""

        return self._send_email(subject, body, html_body)
