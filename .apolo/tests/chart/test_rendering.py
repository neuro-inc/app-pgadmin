import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from apolo_app_types_fixtures.constants import APP_ID, APP_SECRETS_NAME

from ..unit.test_inputs import generate


CHART_DIR = Path(__file__).parents[3] / "charts" / "pgadmin-app"
RELEASE = "apolo-project-pgadmin-0a1b2c3d"

pytestmark = pytest.mark.skipif(
    not os.environ.get("CI") and shutil.which("helm") is None,
    reason="needs helm",
)


def render(values, tmp_path):
    values_file = tmp_path / "values.json"
    values_file.write_text(json.dumps(values))
    result = subprocess.run(  # noqa: S603
        [
            shutil.which("helm"),
            "template",
            RELEASE,
            str(CHART_DIR),
            "--namespace",
            "project",
            "--values",
            str(values_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    documents = [doc for doc in yaml.safe_load_all(result.stdout) if doc]
    return {(doc["kind"], doc["metadata"]["name"]): doc for doc in documents}


async def test_release(setup_clients, inputs, tmp_path):
    values = await generate(setup_clients, inputs)
    manifests = render(values, tmp_path)
    name = f"pgadmin-{APP_ID}"

    assert set(manifests) == {
        ("ConfigMap", name),
        ("Deployment", name),
        ("Ingress", name),
        ("Service", name),
    }

    ingress = manifests[("Ingress", name)]
    assert ingress["metadata"]["annotations"] == values["ingress"]["annotations"]
    assert ingress["spec"]["rules"][0]["host"] == (
        f"pgadmin--{APP_ID}.apps.some.org.neu.ro"
    )
    assert ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"] == {
        "service": {"name": name, "port": {"name": "http"}}
    }

    servers = json.loads(manifests[("ConfigMap", name)]["data"]["servers.json"])
    assert servers["Servers"]["1"] == {
        "Name": "shop",
        "Group": "Databases",
        "Host": values["servers"][0]["host"],
        "Port": 5432,
        "MaintenanceDB": "shop",
        "DBRestriction": "shop",
        "Username": "shop",
        "ConnectionParameters": {
            "sslmode": "prefer",
            "passfile": "/pgpass/pgpass",
            "options": "-c default_transaction_read_only=on",
        },
    }
    assert "options" not in servers["Servers"]["2"]["ConnectionParameters"]
    assert servers["Servers"]["2"]["Name"] == "CRM"

    pod = manifests[("Deployment", name)]["spec"]["template"]
    assert pod["metadata"]["labels"]["platform.apolo.us/preset"] == "cpu-small"
    assert pod["metadata"]["labels"]["application"] == "pgadmin"
    init = pod["spec"]["initContainers"][0]
    assert init["env"] == [
        {
            "name": "SERVER_PASSWORD_1",
            "valueFrom": {
                "secretKeyRef": {
                    "name": APP_SECRETS_NAME,
                    "key": "pg-0a1b-shop-password",
                }
            },
        },
        {
            "name": "SERVER_PASSWORD_2",
            "valueFrom": {
                "secretKeyRef": {
                    "name": APP_SECRETS_NAME,
                    "key": "pg-2c3d-crm-password",
                }
            },
        },
    ]
    container = pod["spec"]["containers"][0]
    assert container["resources"] == values["resources"]


def server(**overrides):
    return {
        "name": "db",
        "host": "pg-primary",
        "port": 5432,
        "user": "user",
        "database": "db",
        "readOnly": True,
        "passwordSecret": {"name": "s", "key": "k"},
        **overrides,
    }


def run_pgpass(tmp_path, servers, passwords):
    manifests = render({"fullnameOverride": "pgadmin-x", "servers": servers}, tmp_path)
    data = manifests[("ConfigMap", "pgadmin-x")]["data"]
    (tmp_path / "servers.json").write_text(data["servers.json"])
    script = (
        data["pgpass.py"]
        .replace("/config/", f"{tmp_path}/")
        .replace("/pgpass/pgpass", str(tmp_path / "pgpass"))
    )
    return subprocess.run(  # noqa: S603
        [shutil.which("python3"), "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env={
            f"SERVER_PASSWORD_{index}": password
            for index, password in enumerate(passwords, start=1)
        },
    )


def test_pgpass_escaping(tmp_path):
    result = run_pgpass(tmp_path, [server(user="us:er")], ["p:a\\ss"])

    assert result.returncode == 0
    assert (
        tmp_path / "pgpass"
    ).read_text() == "pg-primary:5432:*:us\\:er:p\\:a\\\\ss\n"
    assert (tmp_path / "pgpass").stat().st_mode & 0o777 == 0o600


def test_pgpass_rejects_line_breaks(tmp_path):
    result = run_pgpass(tmp_path, [server()], ["first\nsecond"])

    assert result.returncode == 1
    assert "Server 1: a line break" in result.stderr
    assert "first" not in result.stderr


def test_secret_reference_stays_a_string(tmp_path):
    manifests = render(
        {
            "fullnameOverride": "pgadmin-x",
            "servers": [server(passwordSecret={"name": "123", "key": "true"})],
        },
        tmp_path,
    )
    pod = manifests[("Deployment", "pgadmin-x")]["spec"]["template"]["spec"]

    assert pod["initContainers"][0]["env"][0]["valueFrom"]["secretKeyRef"] == {
        "name": "123",
        "key": "true",
    }


def test_database_with_comma_is_not_restricted(tmp_path):
    manifests = render(
        {"fullnameOverride": "pgadmin-x", "servers": [server(database="a,b")]},
        tmp_path,
    )
    servers = json.loads(manifests[("ConfigMap", "pgadmin-x")]["data"]["servers.json"])

    assert "DBRestriction" not in servers["Servers"]["1"]
    assert servers["Servers"]["1"]["MaintenanceDB"] == "a,b"
