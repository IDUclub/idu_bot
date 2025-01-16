import json

import requests

from src.common.config.config import Config


class VectorizerService:
    def __init__(self, config: Config):
        self.config = config
        self.url = f"http://{config.get('VECTORIZER_HOST')}:{config.get('VECTORIZER_PORT')}/api/v1/vectorizer/vectorize"

    def embed(self, prompt: str) -> list:
        client_cert = self.config.get("CLIENT_CERT")
        ca_cert = "onti-ca.crt"
        client_key = "DECFILE"

        try:
            with requests.post(
                self.url,
                json={"text": prompt},
                cert=(client_cert, client_key),
                verify=ca_cert,
            ) as response:
                if response.status_code == 200:
                    return json.loads(response.text)
                raise RuntimeError("Vectorizer ended not with 200: " + response.text)
        except BaseException as e:
            raise ConnectionError("Failed to call vectorizer: " + str(e))
