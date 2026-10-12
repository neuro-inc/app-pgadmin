from apolo_app_types_fixtures.constants import APP_ID
from apolo_apps_pgadmin.outputs_processor import PgAdminAppOutputProcessor

from ..conftest import NAMESPACE
from .test_inputs import generate


async def test_outputs_from_generated_values(setup_clients, inputs):
    values = await generate(setup_clients, inputs)

    outputs = await PgAdminAppOutputProcessor().generate_outputs(
        helm_values=values, app_instance_id="pgadmin-app"
    )

    assert outputs["app_url"]["internal_url"] == {
        "host": f"pgadmin-{APP_ID}.{NAMESPACE}",
        "port": 80,
        "protocol": "http",
        "timeout": 30.0,
        "base_path": "/",
        "api_type": "webapp",
        "__type__": "WebApp",
    }
    assert outputs["app_url"]["external_url"]["host"] == (
        f"pgadmin--{APP_ID}.apps.some.org.neu.ro"
    )
    assert outputs["app_url"]["external_url"]["protocol"] == "https"
    assert outputs["app_url"]["external_url"]["port"] == 443


async def test_outputs_without_ingress():
    outputs = await PgAdminAppOutputProcessor().generate_outputs(
        helm_values={"fullnameOverride": "pgadmin-x", "ingress": {"enabled": False}},
        app_instance_id="pgadmin-app",
    )

    assert outputs["app_url"]["external_url"] is None
