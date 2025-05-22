#!/bin/bash

# --- Configuration ---
MINIKUBE_MEMORY="6144mb" # 6GB RAM for Minikube
MINIKUBE_CPUS="3"        # 3 CPUs for Minikube
PG_CLUSTER_NAME="your-app-db" # Matches metadata.name in my-pg-cluster.yaml
PG_NAMESPACE="default"   # Matches namespace in my-pg-cluster.yaml
DASHBOARD_SERVICE_NAME="streamlit-dashboard-service" # Adjust to your Streamlit Service name
DASHBOARD_NAMESPACE="default" # Adjust to your Streamlit Service namespace
PG_SECRET_NAME="your-db-secrets"
PG_APP_USER_PASSWORD="12345678" # IMPORTANT: Change this! In real setup, would prompt or read from env.

# --- Helper Functions ---

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Docker (required for Minikube Docker driver)
install_docker() {
    if ! command_exists docker; then
        echo "Docker not found. Installing Docker..."
        sudo apt update || { echo "Failed to update apt. Aborting."; exit 1; }
        sudo apt install -y docker.io || { echo "Failed to install docker.io. Aborting."; exit 1; }
        echo "Adding current user to docker group. You might need to log out and back in for changes to take effect."
        sudo usermod -aG docker "$USER" || { echo "Failed to add user to docker group."; }
        newgrp docker # Apply group change immediately if possible
    else
        echo "Docker is already installed."
    fi
}

# Install kubectl
install_kubectl() {
    if ! command_exists kubectl; then
        echo "kubectl not found. Installing kubectl..."
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" || { echo "Failed to download kubectl. Aborting."; exit 1; }
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl || { echo "Failed to install kubectl. Aborting."; exit 1; }
        rm kubectl
        echo "kubectl installed."
    else
        echo "kubectl is already installed."
    fi
}

# Install Helm
install_helm() {
    if ! command_exists helm; then
        echo "Helm not found. Installing Helm..."
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash || { echo "Failed to install Helm. Aborting."; exit 1; }
        echo "Helm installed."
    else
        echo "Helm is already installed."
    fi
}

# Install Minikube
install_minikube() {
    if ! command_exists minikube; then
        echo "Minikube not found. Installing Minikube..."
        curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64 || { echo "Failed to download minikube. Aborting."; exit 1; }
        sudo install minikube-linux-amd64 /usr/local/bin/minikube || { echo "Failed to install minikube. Aborting."; exit 1; }
        rm minikube-linux-amd64
        echo "Minikube installed."
    else
        echo "Minikube is already installed."
    fi
}

wait_for_pod_ready() {
    local label_selector="$1"
    local namespace="$2"
    echo "Waiting for pods with label selector '$label_selector' in namespace '$namespace' to be ready (timeout 10 min)..."
    kubectl wait --for=condition=ready pod -l "$label_selector" -n "$namespace" --timeout=600s || { echo >&2 "Pods did not become ready in time. Check 'kubectl describe pod -l $label_selector -n $namespace'"; exit 1; }
    echo "Pods ready!"
}

# --- Main Setup Script ---

echo "--- Starting Sales Forecasting Platform Setup ---"

# #  1. Install Prerequisites if missing
echo "Checking and installing prerequisites: Docker, kubectl, Helm, Minikube..."
install_docker
install_kubectl
install_helm
install_minikube
echo "All prerequisites checked/installed."

# 2. Minikube Setup
echo "Checking Minikube status..."
if ! minikube status &> /dev/null; then
    echo "Minikube not running or configured. Starting Minikube..."
    minikube start --driver=docker --memory ${MINIKUBE_MEMORY} --cpus ${MINIKUBE_CPUS} || { echo "Failed to start Minikube. Ensure Docker is running and you are in the 'docker' group."; exit 1; }
elif [[ $(minikube status -f "{{.Driver}}") != "docker" ]]; then
    echo "Minikube is running with a different driver. Please stop it (minikube stop) and restart with --driver=docker."
    exit 1
else
    echo "Minikube is already running."
fi
eval $(minikube docker-env) # Ensure Docker commands use Minikube's daemon

# 3. Install Cert-Manager
echo "Installing Cert-Manager..."
helm repo add jetstack https://charts.jetstack.io --force-update &>/dev/null
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.14.0 \
  --set installCRDs=true || { echo "Failed to install Cert-Manager."; exit 1; }
wait_for_pod_ready "app.kubernetes.io/instance=cert-manager" "cert-manager"

# 4. Install Zalando PostgreSQL Operator
echo "Installing Zalando PostgreSQL Operator..."
helm repo add postgres-operator-charts https://opensource.zalando.com/postgres-operator/charts/postgres-operator

# install the postgres-operator
helm install postgres-operator postgres-operator-charts/postgres-operator

# add repo for postgres-operator-ui
helm repo add postgres-operator-ui-charts https://opensource.zalando.com/postgres-operator/charts/postgres-operator-ui

# install the postgres-operator-ui
helm install postgres-operator-ui postgres-operator-ui-charts/postgres-operator-ui || { echo "Failed to install PostgreSQL Operator."; exit 1; }
# wait_for_pod_ready "app=postgres-operator" "default"

# 5. Create PostgreSQL Secret
echo "Creating PostgreSQL user secret..."
# Using --overwrite=true to update if already exists, --dry-run=client -o yaml | kubectl apply -f - for idempotent creation
kubectl create secret generic your-app-db.your-app-user.credentials \
  --from-literal=username=your-app-user \
  --from-literal=password=your_secret_password || { echo "Failed to create PG secret."; exit 1; }
echo "PG secret '$PG_SECRET_NAME' created/updated."

# 6. Deploy PostgreSQL Cluster
echo "Deploying PostgreSQL Cluster..."
kubectl apply -f k8s/pg-cluster.yaml || { echo "Failed to deploy PostgreSQL Cluster."; exit 1; }
# wait_for_pod_ready "application=spilo,cluster-name=${PG_CLUSTER_NAME}" "$PG_NAMESPACE"
echo "PostgreSQL cluster '$PG_CLUSTER_NAME' is deployed and ready."

# 7. Build and Deploy Docker Images (for Streamlit and API)
eval $(minikube docker-env) 
echo "Building Docker image for Streamlit Dashboard..."
minikube image build -t streamlit-dashboard-image-98167732:latest ./dashboard_development || { echo "Failed to build Streamlit image."; exit 1; }
echo "Building Docker image for Forecasting API..."
minikube image build -t forecasting-api-image-98167732:latest ./api_development || { echo "Failed to build API image."; exit 1; }

echo "Deploying Streamlit Dashboard..."
# Ensure streamlit-deployment.yaml uses image: streamlit-dashboard-image:latest
eval $(minikube docker-env)
kubectl apply -f k8s/streamlit-deployment.yaml || { echo "Failed to deploy Streamlit Dashboard."; exit 1; }
wait_for_pod_ready "app=streamlit-dashboard" "$DASHBOARD_NAMESPACE"
echo "Streamlit Dashboard deployed."

echo "Deploying Forecasting API..."
# Ensure api-deployment.yaml uses image: forecasting-api-image:latest
eval $(minikube docker-env) 
kubectl apply -f k8s/api-deployment.yaml || { echo "Failed to deploy Forecasting API."; exit 1; }
wait_for_pod_ready "app=forecasting-api" "$PG_NAMESPACE"
echo "Forecasting API deployed."

echo "--- Setup Complete! ---"

echo "To access your Dashboard:"
echo "1. Run: minikube service $DASHBOARD_SERVICE_NAME -n $DASHBOARD_NAMESPACE"
echo "   (This will open the dashboard in your browser. Keep this terminal open.)"
echo ""
echo "To connect to PostgreSQL from your laptop (for testing):"
echo "1. Run: kubectl port-forward service/$PG_CLUSTER_NAME 5432:5432 -n $PG_NAMESPACE"
echo "   (Keep this terminal open)"
echo "2. In a new terminal: psql -h localhost -p 5432 -U your_app_user -d your_database_name"
echo ""
echo "To clean up all deployed resources, run: ./cleanup.sh"