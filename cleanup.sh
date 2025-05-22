#!/bin/bash

echo "--- Starting Sales Forecasting Platform Cleanup ---"

# --- Configuration (must match setup.sh) ---
PG_CLUSTER_NAME="your-app-db"
PG_NAMESPACE="default"
DASHBOARD_SERVICE_NAME="streamlit-dashboard-service"
DASHBOARD_NAMESPACE="default"
PG_SECRET_NAME="your-db-secrets"

# 1. Delete Application Deployments
echo "Deleting Streamlit Dashboard deployment and service..."
kubectl delete -f k8s/streamlit-deployment.yaml --ignore-not-found -n "$DASHBOARD_NAMESPACE"

# Optional: Delete your API deployment
# echo "Deleting Forecasting API deployment..."
# kubectl delete -f k8s/your_api_deployment.yaml --ignore-not-found -n "$PG_NAMESPACE"

# 2. Delete PostgreSQL Cluster and PVCs
echo "Deleting PostgreSQL cluster '$PG_CLUSTER_NAME' and associated resources..."
kubectl delete postgresql "$PG_CLUSTER_NAME" -n "$PG_NAMESPACE" --ignore-not-found
# PVCs are often left behind by default for safety. Delete them explicitly if they are not re-used.
# This assumes the PVCs are named like 'data-<pod-name>-<random-string>' by the operator
# You might need to adjust this if your operator's PVC naming differs
kubectl get pvc -l cluster-name="$PG_CLUSTER_NAME" -n "$PG_NAMESPACE" -o custom-columns=NAME:.metadata.name --no-headers | xargs -r kubectl delete pvc -n "$PG_NAMESPACE"

echo "Deleting PostgreSQL secret..."
kubectl delete secret "$PG_SECRET_NAME" -n "$PG_NAMESPACE" --ignore-not-found

# Wait for PG pods to terminate to avoid conflicts with operator removal
echo "Waiting for PostgreSQL pods to terminate..."
kubectl wait --for=delete pod -l "application=spilo,cluster-name=${PG_CLUSTER_NAME}" -n "$PG_NAMESPACE" --timeout=300s --for=delete || true # Use true to prevent script from failing if pods are already gone


# 3. Uninstall Operators
echo "Uninstalling Zalando PostgreSQL Operator..."
helm uninstall postgres-operator -n postgres-operator --wait --cascade=background --timeout=300s

echo "Uninstalling Cert-Manager..."
helm uninstall cert-manager -n cert-manager --wait --cascade=background --timeout=300s

echo "--- Cleanup Complete! ---"
echo "You may also want to stop Minikube if you are done: minikube stop"