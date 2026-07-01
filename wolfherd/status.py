"""Status checks for the wolfherd HTTP endpoint."""

from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.error
import urllib.request

from .config import load_config


@dataclass(frozen=True)
class EndpointStatus:
    url: str
    ok: bool
    detail: str
    http_status: int | None = None

    def as_json(self) -> str:
        return json.dumps(
            {
                "url": self.url,
                "ok": self.ok,
                "detail": self.detail,
                "http_status": self.http_status,
            },
            indent=2,
        )


def check_endpoint(url: str, timeout: int = 5) -> EndpointStatus:
    """Check whether the HTTP MCP endpoint is listening.

    mcp-proxy returns 406 to plain GET /mcp. Treat any HTTP response from the
    endpoint as proof that something is listening; connection failures are bad.
    """

    request = urllib.request.Request(url, headers={"Accept": "text/plain"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return EndpointStatus(
                url=url,
                ok=True,
                detail="endpoint responded",
                http_status=response.status,
            )
    except urllib.error.HTTPError as exc:
        ok = exc.code in {200, 400, 404, 405, 406}
        return EndpointStatus(
            url=url,
            ok=ok,
            detail=f"endpoint returned HTTP {exc.code}",
            http_status=exc.code,
        )
    except OSError as exc:
        return EndpointStatus(url=url, ok=False, detail=str(exc))


def status_json() -> str:
    return check_endpoint(load_config().url).as_json()
