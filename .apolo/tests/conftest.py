from decimal import Decimal

import pytest
from apolo_apps_pgadmin.app_types import PgAdminAppInputs, PgAdminDatabase
from apolo_sdk import Preset

from apolo_app_types.protocols.common import ApoloSecret, Preset as PresetInput
from apolo_app_types.protocols.postgres import CrunchyPostgresUserCredentials


pytest_plugins = [
    "apolo_app_types_fixtures.apolo_clients",
]

MEBIBYTE = 1 << 20
PRESETS = {
    "cpu-small": Preset(
        cpu=0.5,
        memory=512 * MEBIBYTE,
        credits_per_hour=Decimal("0.1"),
        available_resource_pool_names=("cpu_pool",),
    ),
    "cpu-micro": Preset(
        cpu=0.1,
        memory=100 * MEBIBYTE,
        credits_per_hour=Decimal("0.01"),
        available_resource_pool_names=("cpu_pool",),
    ),
}
NAMESPACE = "platform--org--project--0a1b2c3d"


def credentials(user, dbname, cluster="pg-0a1b"):
    return CrunchyPostgresUserCredentials(
        user=user,
        password=ApoloSecret(key=f"{cluster}-{user}-password"),
        host=f"{cluster}-primary.{NAMESPACE}",
        port=5432,
        dbname=dbname,
    )


@pytest.fixture
def presets_available():
    return PRESETS


@pytest.fixture
def inputs():
    return PgAdminAppInputs(
        preset=PresetInput(name="cpu-small"),
        databases=[
            PgAdminDatabase(credentials=credentials("shop", "shop")),
            PgAdminDatabase(
                credentials=credentials("crm", "crm", cluster="pg-2c3d"),
                display_name="CRM",
                read_only=False,
            ),
        ],
    )


@pytest.fixture(autouse=True)
def _namespace(monkeypatch):
    monkeypatch.setenv("APOLO_APP_NAMESPACE", NAMESPACE)
