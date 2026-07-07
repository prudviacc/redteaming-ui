# Deployment Guide — Redteaming UI

Hosting: **Azure Container Apps** (scale-to-zero, no cost when idle)  
Registry: **Azure Container Registry (ACR)**  
Storage: **Azure Files** (persistent profiles and session history)  
Region: your choice

---

## Prerequisites

Azure CLI installed and logged in:
```powershell
az login
```

Set shell variables (run once per terminal session):
```powershell
$RG      = "<resource-group>"
$ACR     = "<acr-name>"
$APP     = "<container-app-name>"
$ENV     = "<container-app-environment>"          # shared with backend
$SA_NAME = "<storage-account-name>"               # globally unique, lowercase
$SHARE   = "<file-share-name>"
$BACKEND = "<backend-container-app-url>"
```

---

## First-Time Deployment

### Step 1 — Build and push the image

Run from the `redteaming_ui\` directory:

```powershell
az acr build --registry $ACR --image redteaming-ui:v1 .
```

### Step 2 — Create Azure Storage Account and File Share

```powershell
az storage account create `
  --name $SA_NAME `
  --resource-group $RG `
  --sku Standard_LRS `
  --location <region>

az storage share-rm create `
  --storage-account $SA_NAME `
  --name $SHARE `
  --resource-group $RG
```

### Step 3 — Create the Container App

```powershell
az containerapp create `
  --name $APP `
  --resource-group $RG `
  --environment $ENV `
  --image "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" `
  --target-port 80 `
  --ingress external `
  --min-replicas 0 `
  --max-replicas 1 `
  --cpu 0.5 --memory 1Gi `
  --system-assigned
```

### Step 4 — Grant ACR pull to the managed identity

```powershell
$PRINCIPAL_ID = az containerapp show --name $APP --resource-group $RG --query "identity.principalId" -o tsv
$ACR_SCOPE    = az acr show --name $ACR --resource-group $RG --query id -o tsv

az role assignment create --role AcrPull --assignee $PRINCIPAL_ID --scope $ACR_SCOPE

az containerapp registry set `
  --name $APP `
  --resource-group $RG `
  --server "$ACR.azurecr.io" `
  --identity system
```

### Step 5 — Update to the real image and set env vars

```powershell
az containerapp update `
  --name $APP `
  --resource-group $RG `
  --image "$ACR.azurecr.io/redteaming-ui:v1" `
  --set-env-vars "AGENT_API_URL=$BACKEND" "AGENT_API_TIMEOUT=300"
```

### Step 6 — Fix ingress port

```powershell
az containerapp ingress update `
  --name $APP `
  --resource-group $RG `
  --target-port 8501
```

### Step 7 — Mount Azure Files for persistent storage

```powershell
$SA_KEY = az storage account keys list `
  --account-name $SA_NAME `
  --resource-group $RG `
  --query "[0].value" -o tsv

az containerapp env storage set `
  --name $ENV `
  --resource-group $RG `
  --storage-name ui-storage `
  --azure-file-account-name $SA_NAME `
  --azure-file-account-key $SA_KEY `
  --azure-file-share-name $SHARE `
  --access-mode ReadWrite
```

Then apply via YAML update — export the current config, add `volumeMounts` and `volumes` sections, and apply:

```powershell
# Export
az containerapp show --name $APP --resource-group $RG --output yaml > containerapp.yaml

# Edit containerapp.yaml: under the container add:
#   volumeMounts:
#   - mountPath: /app/storage
#     volumeName: ui-storage
#
# Replace "volumes: null" with:
#   volumes:
#   - name: ui-storage
#     storageName: ui-storage
#     storageType: AzureFile

# Apply
az containerapp update --name $APP --resource-group $RG --yaml containerapp.yaml
```

### Step 8 — Verify

```powershell
$FQDN = az containerapp show --name $APP --resource-group $RG --query "properties.configuration.ingress.fqdn" -o tsv
Write-Host "UI live at: https://$FQDN"
curl.exe "https://$FQDN/_stcore/health"
# Expected HTTP 200
```

---

## Day-to-Day Operations

### Deploy code changes

```powershell
# Build and push (increment version tag: v2, v3, ...)
az acr build --registry $ACR --image redteaming-ui:v2 .

# Update running app
az containerapp update --name $APP --resource-group $RG --image "$ACR.azurecr.io/redteaming-ui:v2"
```

> Always use explicit version tags — avoids ambiguity and makes rollback easy.

### Manually stop (instant $0 cost)

```powershell
az containerapp update --name $APP --resource-group $RG --min-replicas 0 --max-replicas 0
```

### Resume after manual stop

```powershell
az containerapp update --name $APP --resource-group $RG --min-replicas 0 --max-replicas 1
```

### View live logs

```powershell
az containerapp logs show --name $APP --resource-group $RG --follow
```

### Check revision status

```powershell
az containerapp revision list --name $APP --resource-group $RG `
  --query "[].{name:name, state:properties.runningState, replicas:properties.replicas}" `
  -o table
```

### Rollback to a previous image

```powershell
az containerapp update --name $APP --resource-group $RG --image "$ACR.azurecr.io/redteaming-ui:v1"
```

### Update an env var

```powershell
az containerapp update --name $APP --resource-group $RG `
  --set-env-vars AGENT_API_TIMEOUT=600
```

---

## Scale Behaviour

| Situation | Replicas | Cost |
|---|---|---|
| No traffic for ~5 min | 0 (auto scale-down) | $0 |
| Manually stopped | 0 | $0 |
| First request after idle | Wakes up in ~15s | Billed from wake-up |
| Active traffic | 1 | Billed per vCPU/memory second |

Note: UI is capped at 1 replica — Streamlit is single-process and multiple replicas would give different users different session state.

---

## Troubleshooting

### Page doesn't load / connection refused

App has scaled to zero. Open the URL once — it wakes in ~15s.

### Sidebar shows "Backend Offline"

The backend Container App has scaled to zero. Wait ~15s and retry.

### Registered agents missing after restart

Azure Files mount may not be configured. Re-run Step 7, then verify:
```powershell
az containerapp show --name $APP --resource-group $RG `
  --query "properties.template.volumes" -o json
```

### Image pull error (Unauthorized)

Managed identity lost AcrPull. Re-run Step 4.

### Revision stuck in Activating

```powershell
az containerapp logs show --name $APP --resource-group $RG --follow
```
