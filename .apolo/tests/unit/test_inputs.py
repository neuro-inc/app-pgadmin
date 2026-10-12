import pytest
from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_NAMESPACE,
)
from apolo_apps_pgadmin.app_types import PgAdminAppInputs, PgAdminDatabase
from apolo_apps_pgadmin.inputs_processor import PgAdminAppChartValueProcessor
from pydantic import ValidationError

from apolo_app_types.protocols.common import (
    ApoloSecret,
    BasicNetworkingConfig,
    IngressHttp,
    NoAuth,
    Preset,
)
from apolo_app_types.protocols.postgres import CrunchyPostgresUserCredentials

from ..conftest import NAMESPACE, credentials


async def generate(apolo_client, inputs):
    processor = PgAdminAppChartValueProcessor(client=apolo_client)
    return await processor.gen_extra_values(
        input_=inputs,
        app_name="pgadmin-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )


async def test_values(setup_clients, inputs):
    values = await generate(setup_clients, inputs)

    assert values["fullnameOverride"] == f"pgadmin-{APP_ID}"
    assert values["apolo_app_id"] == APP_ID
    assert values["resources"]["limits"]["memory"] == "512M"
    assert values["podLabels"]["platform.apolo.us/preset"] == "cpu-small"
    assert set(values["ingress"]) == {"enabled", "className", "annotations", "hosts"}
    assert values["ingress"]["annotations"]
    assert values["servers"] == [
        {
            "name": "shop",
            "host": f"pg-0a1b-primary.{NAMESPACE}",
            "port": 5432,
            "user": "shop",
            "database": "shop",
            "readOnly": True,
            "passwordSecret": {
                "name": APP_SECRETS_NAME,
                "key": "pg-0a1b-shop-password",
            },
        },
        {
            "name": "CRM",
            "host": f"pg-2c3d-primary.{NAMESPACE}",
            "port": 5432,
            "user": "crm",
            "database": "crm",
            "readOnly": False,
            "passwordSecret": {
                "name": APP_SECRETS_NAME,
                "key": "pg-2c3d-crm-password",
            },
        },
    ]


async def test_preset_too_small(setup_clients, inputs):
    inputs = inputs.model_copy(update={"preset": Preset(name="cpu-micro")})

    with pytest.raises(ValueError, match="at least 512 MB"):
        await generate(setup_clients, inputs)


def test_ingress_without_auth_is_rejected():
    with pytest.raises(
        ValidationError, match="requires an ingress with authentication"
    ):
        PgAdminAppInputs(
            preset=Preset(name="cpu-small"),
            networking=BasicNetworkingConfig(ingress_http=IngressHttp(auth=NoAuth())),
            databases=[PgAdminDatabase(credentials=credentials("shop", "shop"))],
        )


def test_databases_required():
    with pytest.raises(ValidationError, match="at least 1 item"):
        PgAdminAppInputs(preset=Preset(name="cpu-small"), databases=[])


def test_database_name_required():
    with pytest.raises(ValidationError, match="must include a database name"):
        PgAdminDatabase(
            credentials=CrunchyPostgresUserCredentials(
                user="shop",
                password=ApoloSecret(key="shop-password"),
                host="pg-primary",
                port=5432,
            )
        )


def test_display_names_must_differ():
    with pytest.raises(ValidationError, match="same display name"):
        PgAdminAppInputs(
            preset=Preset(name="cpu-small"),
            databases=[
                PgAdminDatabase(credentials=credentials("shop", "shop")),
                PgAdminDatabase(
                    credentials=credentials("shop", "shop", cluster="pg-2c3d")
                ),
            ],
        )


def test_blank_display_name_falls_back_to_database():
    database = PgAdminDatabase(
        credentials=credentials("shop", "shop"), display_name="  "
    )

    assert database.name == "shop"
