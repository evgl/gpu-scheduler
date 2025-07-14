#!/bin/bash
# Generate TLS certificates for GPU scheduler webhook

set -e

NAMESPACE=${NAMESPACE:-gpu-scheduler-system}
SERVICE_NAME=${SERVICE_NAME:-gpu-scheduler-webhook}
CERT_DIR=${CERT_DIR:-./certs}

# Create certificate directory
mkdir -p ${CERT_DIR}

# Generate CA private key
openssl genrsa -out ${CERT_DIR}/ca.key 2048

# Generate CA certificate
openssl req -new -x509 -days 365 -key ${CERT_DIR}/ca.key \
  -subj "/C=US/ST=CA/L=San Francisco/O=GPU Scheduler/CN=GPU Scheduler CA" \
  -out ${CERT_DIR}/ca.crt

# Generate webhook private key
openssl genrsa -out ${CERT_DIR}/tls.key 2048

# Generate certificate signing request
cat <<EOF > ${CERT_DIR}/csr.conf
[req]
req_extensions = v3_req
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = ${SERVICE_NAME}
DNS.2 = ${SERVICE_NAME}.${NAMESPACE}
DNS.3 = ${SERVICE_NAME}.${NAMESPACE}.svc
DNS.4 = ${SERVICE_NAME}.${NAMESPACE}.svc.cluster.local
EOF

openssl req -new -key ${CERT_DIR}/tls.key \
  -subj "/C=US/ST=CA/L=San Francisco/O=GPU Scheduler/CN=${SERVICE_NAME}.${NAMESPACE}.svc" \
  -out ${CERT_DIR}/server.csr \
  -config ${CERT_DIR}/csr.conf

# Generate webhook certificate signed by CA
openssl x509 -req -days 365 -in ${CERT_DIR}/server.csr \
  -CA ${CERT_DIR}/ca.crt -CAkey ${CERT_DIR}/ca.key -CAcreateserial \
  -out ${CERT_DIR}/tls.crt \
  -extensions v3_req \
  -extfile ${CERT_DIR}/csr.conf

# Clean up
rm ${CERT_DIR}/server.csr

# Create Kubernetes secret YAML
cat <<EOF > ${CERT_DIR}/webhook-tls-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: gpu-scheduler-webhook-tls
  namespace: ${NAMESPACE}
type: kubernetes.io/tls
data:
  tls.crt: $(base64 -w 0 < ${CERT_DIR}/tls.crt)
  tls.key: $(base64 -w 0 < ${CERT_DIR}/tls.key)
EOF

# Get CA bundle for webhook configuration
CA_BUNDLE=$(base64 -w 0 < ${CERT_DIR}/ca.crt)

echo "Certificates generated successfully!"
echo ""
echo "CA Bundle (for MutatingWebhookConfiguration):"
echo "${CA_BUNDLE}"
echo ""
echo "To create the secret in Kubernetes:"
echo "kubectl apply -f ${CERT_DIR}/webhook-tls-secret.yaml" 