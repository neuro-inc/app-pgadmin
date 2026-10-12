{{- define "pgadmin.fullname" -}}
{{- default .Release.Name .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "pgadmin.selectorLabels" -}}
app.kubernetes.io/name: pgadmin
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "pgadmin.labels" -}}
{{ include "pgadmin.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- with .Values.labels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{- define "pgadmin.servers" -}}
{{- $servers := dict -}}
{{- range $index, $server := .Values.servers -}}
{{- $parameters := dict "sslmode" "prefer" "passfile" "/pgpass/pgpass" -}}
{{- if $server.readOnly -}}
{{- $_ := set $parameters "options" "-c default_transaction_read_only=on" -}}
{{- end -}}
{{- $_ := set $servers (toString (add1 $index)) (dict
  "Name" $server.name
  "Group" $.Values.serverGroup
  "Host" $server.host
  "Port" (int $server.port)
  "MaintenanceDB" $server.database
  "Username" $server.user
  "ConnectionParameters" $parameters
) -}}
{{- if not (contains "," $server.database) -}}
{{- $_ := set (get $servers (toString (add1 $index))) "DBRestriction" $server.database -}}
{{- end -}}
{{- end -}}
{{- dict "Servers" $servers | toPrettyJson -}}
{{- end -}}
