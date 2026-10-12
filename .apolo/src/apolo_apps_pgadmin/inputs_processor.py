import re
import typing as t

from apolo_app_types.app_types import AppType
from apolo_app_types.helm.apps.base import BaseChartValueProcessor
from apolo_app_types.helm.apps.common import gen_extra_values
from apolo_apps_pgadmin.app_types import PgAdminAppInputs


FULLNAME_PREFIX = "pgadmin"
MIN_MEMORY_MIB = 480
INGRESS_KEYS = ("enabled", "className", "annotations", "hosts")
MEMORY_UNITS = {
    "Ki": 1 << 10,
    "Mi": 1 << 20,
    "Gi": 1 << 30,
    "Ti": 1 << 40,
    "k": 10**3,
    "M": 10**6,
    "G": 10**9,
    "T": 10**12,
}
MEBIBYTE = 1 << 20


def get_fullname(app_id: str) -> str:
    return f"{FULLNAME_PREFIX}-{app_id}"


def _parse_memory(value: str) -> int:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([A-Za-z]*)", value.strip())
    if not match or (match.group(2) and match.group(2) not in MEMORY_UNITS):
        msg = f"Unsupported memory quantity: {value}"
        raise ValueError(msg)
    return int(float(match.group(1)) * MEMORY_UNITS.get(match.group(2), 1))


class PgAdminAppChartValueProcessor(BaseChartValueProcessor[PgAdminAppInputs]):
    async def gen_extra_values(
        self,
        input_: PgAdminAppInputs,
        app_name: str,
        namespace: str,
        app_id: str,
        app_secrets_name: str,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> dict[str, t.Any]:
        extra_values = await gen_extra_values(
            apolo_client=self.client,
            preset_type=input_.preset,
            app_id=app_id,
            app_type=AppType.PgAdmin,
            namespace=namespace,
            ingress_http=input_.networking.ingress_http,
        )
        memory_limit = _parse_memory(extra_values["resources"]["limits"]["memory"])
        if memory_limit // MEBIBYTE < MIN_MEMORY_MIB:
            msg = (
                f"Preset {input_.preset.name} has {memory_limit // MEBIBYTE} MiB "
                "of memory, pgAdmin needs at least 512 MB"
            )
            raise ValueError(msg)

        return {
            "apolo_app_id": extra_values["apolo_app_id"],
            "fullnameOverride": get_fullname(app_id),
            "resources": extra_values["resources"],
            "tolerations": extra_values["tolerations"],
            "affinity": extra_values["affinity"],
            "podLabels": extra_values["podLabels"],
            "ingress": {
                key: extra_values["ingress"][key]
                for key in INGRESS_KEYS
                if key in extra_values["ingress"]
            },
            "servers": [
                {
                    "name": database.name,
                    "host": database.credentials.host,
                    "port": database.credentials.port,
                    "user": database.credentials.user,
                    "database": database.credentials.dbname,
                    "readOnly": not database.allow_writes,
                    "passwordSecret": {
                        "name": app_secrets_name,
                        "key": database.credentials.password.key,
                    },
                }
                for database in input_.databases
            ],
        }
