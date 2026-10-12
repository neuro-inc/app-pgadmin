# app-pgadmin

[pgAdmin](https://www.pgadmin.org/) packaged as an Apolo application: run SQL queries against the PostgreSQL applications of a project from the browser.

## Layout

- `charts/pgadmin-app` deploys the upstream `dpage/pgadmin4` image with the databases preconfigured.
- `charts/pgadmin-app/ci` holds an example of generated values.
- `.apolo/applications.yaml` registers the application in the Apolo catalog.
- `.apolo/src/apolo_apps_pgadmin` holds the input and output types, the processor that turns inputs into chart values, the processor that turns chart values into outputs, and the generated JSON schemas.

## Versions

| Component | Version |
| --- | --- |
| Image `dpage/pgadmin4` | 9.18.0 |

## Inputs

| Input | Meaning |
| --- | --- |
| `preset` | Resources of pgAdmin. At least 512 MB of memory. |
| `networking` | Ingress and its authentication. An ingress without authentication is rejected. |
| `databases[].credentials` | A user of a PostgreSQL application in the project, picked as an integration. |
| `databases[].display_name` | Name of the server in pgAdmin, the database name by default. |
| `databases[].read_only` | Open sessions with `default_transaction_read_only=on`, on by default. |

## How it works

pgAdmin runs in desktop mode: it has no login of its own, the platform ingress authentication protects it. Every database becomes a server in `servers.json`, restricted to its database. An init container writes a `pgpass` file with the passwords into an in-memory volume; the passwords come from `apps-secrets` and never appear in the chart values.

pgAdmin keeps its own state (query history, preferences) on an `emptyDir` volume. It is reset on every restart, which is also how a changed list of databases is applied.

The read-only switch protects against accidental writes, it is not a permission: a session can turn it off with `SET`. Enforced read-only access needs a read-only database user.

## Outputs

| Output | Meaning |
| --- | --- |
| `app_url` | pgAdmin web interface. |
