import os
from typing import List, Union, Optional

import requests


class ResendClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("RESEND_API_KEY")

        if not self.api_key:
            raise ValueError("RESEND_API_KEY manquant")

        self.base_url = (
            base_url
            or os.getenv("RESEND_BASE_URL")
            or "https://api.resend.com"
        )

    def send_email(
        self,
        from_email: str,
        to: Union[str, List[str]],
        subject: str,
        html: str,
    ) -> dict:
        """
        Envoie un email via Resend.

        Args:
            from_email: adresse expéditeur
            to: destinataire ou liste de destinataires
            subject: sujet
            html: contenu HTML

        Returns:
            dict: réponse JSON de l'API
        """

        if isinstance(to, str):
            to = [to]

        response = requests.post(
            f"{self.base_url}/emails",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email,
                "to": to,
                "subject": subject,
                "html": html,
            },
            timeout=30,
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(
                f"Erreur Resend ({response.status_code}): {response.text}"
            ) from e

        return response.json()