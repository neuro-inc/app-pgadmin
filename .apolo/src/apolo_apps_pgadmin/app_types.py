import typing as t

from pydantic import ConfigDict, Field, model_validator

from apolo_app_types.protocols.common import (
    AbstractAppFieldType,
    AppInputs,
    AppOutputs,
    BasicNetworkingConfig,
    NoAuth,
    Preset,
    SchemaExtraMetadata,
    SchemaMetaType,
)
from apolo_app_types.protocols.postgres import CrunchyPostgresUserCredentials


class PgAdminDatabase(AbstractAppFieldType):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="Database",
            description="A PostgreSQL database opened in pgAdmin with the "
            "credentials of its user.",
        ).as_json_schema_extra(),
    )
    credentials: CrunchyPostgresUserCredentials = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="PostgreSQL Credentials",
            description="A user of a PostgreSQL application in this project.",
            meta_type=SchemaMetaType.INTEGRATION,
        ).as_json_schema_extra(),
    )
    display_name: str | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Display Name",
            description="Name of the server in pgAdmin. Defaults to the database name.",
            is_advanced_field=True,
        ).as_json_schema_extra(),
    )
    read_only: bool = Field(
        default=True,
        json_schema_extra=SchemaExtraMetadata(
            title="Read Only",
            description="Open every session read-only so that a query cannot "
            "change data by mistake. A user can still turn it off with SET; "
            "for enforced read-only access use a read-only database user.",
        ).as_json_schema_extra(),
    )

    @property
    def name(self) -> str:
        return (self.display_name or "").strip() or t.cast(str, self.credentials.dbname)

    @model_validator(mode="after")
    def _require_database(self) -> t.Self:
        if not self.credentials.dbname:
            msg = "PostgreSQL credentials must include a database name"
            raise ValueError(msg)
        return self


class PgAdminAppInputs(AppInputs):
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="Resource Preset",
            description="At least 512 MB of memory.",
        ).as_json_schema_extra(),
    )
    networking: BasicNetworkingConfig = Field(
        default_factory=BasicNetworkingConfig,
        json_schema_extra=SchemaExtraMetadata(
            title="Networking Settings",
            description="pgAdmin has no login of its own and connects with the "
            "stored credentials, so the ingress must require authentication.",
        ).as_json_schema_extra(),
    )
    databases: list[PgAdminDatabase] = Field(
        ...,
        min_length=1,
        json_schema_extra=SchemaExtraMetadata(
            title="Databases",
            description="PostgreSQL databases available in pgAdmin.",
        ).as_json_schema_extra(),
    )

    @model_validator(mode="after")
    def _require_auth(self) -> t.Self:
        if isinstance(self.networking.ingress_http.auth, NoAuth):
            msg = "pgAdmin requires an ingress with authentication"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _require_distinct_names(self) -> t.Self:
        names = [database.name for database in self.databases]
        if len(set(names)) != len(names):
            msg = "Two databases have the same display name"
            raise ValueError(msg)
        return self


class PgAdminAppOutputs(AppOutputs):
    pass
