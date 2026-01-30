# Dev Containers & Codespaces Quick Start Guide

> **Note:** The Codespace/Dev Container prepopulates the `.env` file in the project root with Neo4j connection settings. Review these values to ensure they are accurate for your environment. If running outside of a Codespace or Dev Container, you must manually set the Neo4j environment variables (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`) in your `.env` file.

## GitHub Codespaces (Cloud) or Local Dev Container (Local Setup)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/neo4j-partners/neo4j-maf-sample-provider)

### Setup Steps

1. **Click the badge above** (or go to repo → Code → Codespaces → New)

2. **Wait for container to build** (~3 minutes)

3. **Run in terminal:**
   ```bash
   # Authenticate with Azure
   az login --use-device-code
   azd auth login --use-device-code

   # Select Azure region and initialize environment
   ./scripts/setup_azure.sh

   # Deploy
   azd up
   ```

   > **Note:** The setup script clears the `.azure/` directory and Azure-related settings from `.env` to ensure a fresh deployment. Neo4j settings in `.env` are preserved. See [docs/AZ_CLI_GUIDE.md](docs/AZ_CLI_GUIDE.md) for details.

4. **Follow the prompts:**
   ```
   ? Enter a unique environment name: mydev
   ? Select an Azure Subscription: 1. Your Subscription
   ? Pick a resource group to use:
     1. Create a new resource group
   > 2. your-existing-resource-group
   ```
   - **Environment name:** Any word (e.g., `mydev`, `dev`)
   - **Resource group:** Select your existing RG, or choose "Create a new resource group"

5. **Restore Neo4j database (optional):**
   If you don't have a pre-populated Neo4j database, restore the sample data:
   ```bash
   uv run scripts/restore_neo4j.py
   ```

6. **Setup environment:**
   ```bash
   uv run setup_env.py
   ```
7. **Run the API Server:**
   ```bash
   uv run uvicorn api.main:create_app --factory --reload
   ```

8. **Test API:**
   ```bash
   # Basic test - check agent status
   uv run python src/test_server.py basic

   # Run all tests (agent, streaming, memory, semantic search, entities)
   uv run python src/test_server.py all
   ```

---

## Overview

This project uses **resource-group-scoped deployment** - all Azure resources deploy into a pre-existing resource group. This enables:

- **Team scenarios**: Participants only need Contributor access on their assigned resource group
- **Codespaces support**: Limited-permission accounts work seamlessly
- **Simpler cleanup**: Delete the resource group to remove everything

### What Gets Deployed

```
Your Resource Group
├── Microsoft Foundry Project (AI Hub + Project)
├── Azure OpenAI Service (gpt-4o + text-embedding-ada-002)
├── Storage Account
├── Container Registry
├── Container Apps Environment
├── Container App (API)
├── Log Analytics Workspace
├── Application Insights
└── Managed Identity + Role Assignments
```

---

## For Individual Users

### Create Your Own Resource Group

```bash
# Login first
az login

# Create resource group
az group create --name rg-my-agents --location eastus

# Set it for azd
azd env set AZURE_RESOURCE_GROUP rg-my-agents

# Deploy
azd up
```

### Supported Regions

Microsoft Foundry only works in these regions:
- eastus2 (Recommended)
- swedencentral
- westus2

---

## Troubleshooting

### Region Not Supported Error

**Cause**: `AZURE_LOCATION` is not set or set to an unsupported region.

**Fix**:
```bash
# Run the setup script to select a supported region
./scripts/setup_azure.sh

# Or set manually
azd env set AZURE_LOCATION eastus2
azd up
```

### Previous Environment Cached

**Cause**: `.azure/` folder or `.env` file has stale settings from a previous deployment (e.g., a deleted resource group).

**Fix**: Run the setup script, which clears stale config automatically:
```bash
./scripts/setup_azure.sh
azd up
```

Or manually:
```bash
# Remove Azure config from .env (keeps Neo4j settings)
sed -i '' '/^AZURE_/d' .env
sed -i '' '/^SERVICE_/d' .env

rm -rf .azure/
azd init -e myenv
azd env set AZURE_LOCATION eastus2
azd up
```

See [docs/AZ_CLI_GUIDE.md](docs/AZ_CLI_GUIDE.md) for details on why `azd init` picks up values from `.env`.

### API Won't Start

**Cause**: Environment variables not loaded.

**Fix**:
```bash
uv run setup_env.py  # Re-pull from azd
uv run uvicorn api.main:create_app --factory --reload
```

### Soft-Delete Error After Recreating Resources

**Cause**: If you previously deployed and then deleted resources, Azure keeps Cognitive Services in a "soft-deleted" state for 90 days. Redeploying with the same environment name causes a conflict.

**Error message**:
```
FlagMustBeSetForRestore: An existing resource with ID '...' has been soft-deleted.
To restore the resource, you must specify 'restore' to be 'true' in the property.
```

**Fix**: Create a new environment with a different name:
```bash
# Remove the old environment
rm -rf .azure/

# Initialize with a new environment name
azd init
# Enter a NEW name when prompted (e.g., "dev2", "mydev2")

# Set the region
./scripts/setup_azure.sh

# Verify region is set correctly
azd env get-values | grep AZURE_LOCATION

# Deploy
azd up
```

---

## Architecture Notes

### Deployment Scope

The Bicep templates deploy at **resource group scope** (not subscription scope):

- No `targetScope = 'subscription'` declaration
- Resource group must exist before deployment
- Location defaults to resource group's location
- User only needs Contributor on the resource group

### Key Files

| File | Purpose |
|------|---------|
| `infra/main.bicep` | Main deployment template |
| `infra/main.parameters.json` | Parameter values from azd env |
| `azure.yaml` | Azure Developer CLI configuration |
| `.devcontainer/devcontainer.json` | Dev Container settings |

### Environment Flow

```
azd env set AZURE_RESOURCE_GROUP <name>
         ↓
    azd up (deploys to RG)
         ↓
  uv run setup_env.py (pulls outputs to .env)
         ↓
    uvicorn (reads .env, starts API)
```
