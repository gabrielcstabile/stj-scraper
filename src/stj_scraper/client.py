"""HTTP client com sessão persistente, headers de navegador e retry automático."""

import time
from typing import Any

import httpx

from stj_scraper.logger import get_logger

logger = get_logger(__name__)

_RETRY_DELAYS = [1, 2, 4]  # segundos entre tentativas

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://processo.stj.jus.br/",
}


class STJClient:
    """Cliente HTTP para o portal do STJ com retry automático."""

    def __init__(self) -> None:
        """Inicializa a sessão httpx com headers e timeout padrão."""
        self._session = httpx.Client(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=30.0,
        )

    def get(self, url: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """Realiza GET com até 3 tentativas e backoff exponencial."""
        attempts = len(_RETRY_DELAYS) + 1
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            logger.debug(
                "Requisição iniciada: GET %s params=%s (tentativa %d)",
                url,
                params,
                attempt,
            )
            try:
                response = self._session.get(url, params=params)
                response.raise_for_status()
                logger.debug(
                    "Resposta recebida: status=%d url=%s",
                    response.status_code,
                    response.url,
                )
                return response
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt <= len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt - 1]
                    logger.warning(
                        "Retry acionado (tentativa %d/%d): %s — aguardando %ds",
                        attempt,
                        len(_RETRY_DELAYS) + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        logger.error("Falha final após %d tentativas: %s", attempts, last_exc)
        raise last_exc  # type: ignore[misc]

    def close(self) -> None:
        """Fecha a sessão HTTP."""
        self._session.close()

    def __enter__(self) -> "STJClient":
        """Suporte ao uso como context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Fecha a sessão ao sair do context manager."""
        self.close()
