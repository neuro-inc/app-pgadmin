import typing as t

from apolo_app_types.clients.kube import get_current_namespace
from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.protocols.common import ServiceAPI
from apolo_app_types.protocols.common.networking import WebApp
from apolo_apps_pgadmin.app_types import PgAdminAppOutputs


SERVICE_PORT = 80
INGRESS_PORT = 443


def _get_external_host(helm_values: dict[str, t.Any]) -> str | None:
    ingress = helm_values.get("ingress") or {}
    hosts = ingress.get("hosts") or []
    if not ingress.get("enabled") or not hosts:
        return None
    return t.cast(str, hosts[0]["host"])


class PgAdminAppOutputProcessor(BaseAppOutputsProcessor[PgAdminAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> PgAdminAppOutputs:
        internal_host = f"{helm_values['fullnameOverride']}.{get_current_namespace()}"
        external_host = _get_external_host(helm_values)
        return PgAdminAppOutputs(
            app_url=ServiceAPI[WebApp](
                internal_url=WebApp(
                    host=internal_host,
                    port=SERVICE_PORT,
                    protocol="http",
                    base_path="/",
                ),
                external_url=WebApp(
                    host=external_host,
                    port=INGRESS_PORT,
                    protocol="https",
                    base_path="/",
                )
                if external_host
                else None,
            ),
        )
