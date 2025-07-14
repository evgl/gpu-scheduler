{{/*
Expand the name of the chart.
*/}}
{{- define "gpu-scheduler-check.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "gpu-scheduler-check.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "gpu-scheduler-check.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "gpu-scheduler-check.labels" -}}
helm.sh/chart: {{ include "gpu-scheduler-check.chart" . }}
{{ include "gpu-scheduler-check.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "gpu-scheduler-check.selectorLabels" -}}
app.kubernetes.io/name: {{ include "gpu-scheduler-check.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "gpu-scheduler-check.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "gpu-scheduler-check.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate GPU scheduling map annotation
*/}}
{{- define "gpu-scheduler-check.gpuSchedulingMap" -}}
{{- $lines := list }}
{{- range .Values.gpuScheduling.schedulingMap }}
{{- $line := printf "%v=%s:%s" .podIndex .nodeName .gpuDevices }}
{{- $lines = append $lines $line }}
{{- end }}
{{- join "\n" $lines }}
{{- end }}