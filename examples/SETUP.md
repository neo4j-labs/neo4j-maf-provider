# Environment Setup

This guide covers setting up Azure AI Foundry and Neo4j for the sample applications. Both the Python and .NET samples share the same database and Azure resources.

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az login`)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) (`azd`)
- [Neo4j Aura](https://console.neo4j.io) free or paid instance
- Python 3.10+ (for setup scripts)

## 1. Deploy Azure AI Foundry

From the **repo root**, deploy the sample provisioning resources:

```bash
az login
azd auth login
azd up
```

Azure AI Foundry currently requires one of these regions:
- `eastus2` (East US 2)
- `swedencentral` (Sweden Central)
- `westus2` (West US 2)
- `westus3` (West US 3)

If you choose a different region, check Azure AI Foundry availability there before provisioning.

This provisions:
- Azure AI Services account with project management (Foundry)
- Azure AI Project
- Model deployments (GPT-4o, text-embedding-3-small)
- Storage account and required IAM role assignments

If you do not have a `.env` file yet, create one first:

```bash
cp .env.sample .env
```

Before syncing Azure values, make sure your `.env` contains your Neo4j connection values:

```env
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

Then sync the Azure endpoints to your `.env` file:

```bash
python examples/scripts/setup_env.py
```

This populates your `.env` with:
```
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_SERVICES_ENDPOINT=https://...
AZURE_AI_MODEL_NAME=gpt-4o
AZURE_AI_EMBEDDING_NAME=text-embedding-3-small
```

**Alternative: Manual provisioning via Azure CLI**

If you prefer to provision manually instead of using `azd up`:

```bash
# Create resource group
az group create --name rg-neo4j-maf --location eastus2

# Create Azure AI Services resource (with Foundry project management)
az cognitiveservices account create \
  --name neo4j-maf-openai \
  --resource-group rg-neo4j-maf \
  --kind AIServices --sku S0 --location eastus2 \
  --custom-domain neo4j-maf-openai

# Deploy chat model
az cognitiveservices account deployment create \
  --name neo4j-maf-openai --resource-group rg-neo4j-maf \
  --deployment-name gpt-4o --model-name gpt-4o \
  --model-version 2024-08-06 --model-format OpenAI \
  --sku-name GlobalStandard --sku-capacity 20

# Deploy embedding model
az cognitiveservices account deployment create \
  --name neo4j-maf-openai --resource-group rg-neo4j-maf \
  --deployment-name text-embedding-3-small --model-name text-embedding-3-small \
  --model-version 1 --model-format OpenAI \
  --sku-name GlobalStandard --sku-capacity 120

# Assign yourself the Cognitive Services User role
RESOURCE_ID=$(az cognitiveservices account show --name neo4j-maf-openai --resource-group rg-neo4j-maf --query id -o tsv)
az role assignment create --role "Cognitive Services User" \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --scope $RESOURCE_ID
```

Then manually set in `.env`:
```
AZURE_AI_SERVICES_ENDPOINT=https://neo4j-maf-openai.cognitiveservices.azure.com/
AZURE_AI_MODEL_NAME=gpt-4o
AZURE_AI_EMBEDDING_NAME=text-embedding-3-small
```

## 2. Configure .env

If you have not already done so, edit `.env` with your Neo4j credentials:
```
# Neo4j Connection
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

## 3. Load Demo Data into Neo4j

There are two options for loading sample data:

### Option A: Seed Script (quick start)

Generates a small dataset with embeddings. Requires `azure-identity`, `openai`, `neo4j`, and `python-dotenv`:

```bash
pip install azure-identity openai neo4j python-dotenv
az login
python examples/scripts/seed_data.py
```

This creates:
- 3 companies (Apple, Microsoft, NVIDIA) with SEC 10-K filing documents
- 12 text chunks with vector embeddings (text-embedding-3-small)
- 9 risk factors and 15 products linked to companies
- Vector index `chunkEmbeddings` and fulltext index `search_chunks`

### Option B: Full Backup Restore (production-like dataset)

For the complete SEC 10-K filings knowledge graph with thousands of nodes:

1. Download `finance_data.backup` from [neo4j-partners/workshop-financial-data](https://github.com/neo4j-partners/workshop-financial-data/tree/main/backup)
2. Go to your instance in the [Aura Console](https://console.neo4j.io)
3. Click the **...** menu and select **Backup & restore**
4. Click **Upload backup** and drag the backup file
5. Wait for the restore to complete

The backup contains SEC 10-K filings from major companies (Apple, Microsoft, NVIDIA, etc.), with extracted entities, text chunks, and pre-computed vector embeddings.

## 4. Run the Samples

### Python
```bash
cd python
uv sync --prerelease=allow
uv run start-samples
```

### .NET
```bash
az login
cd dotnet
dotnet run --project samples/Neo4j.Samples
```

Both sample apps use the same Neo4j data, same indexes, and same queries — you can compare outputs side by side.

## Cleanup

```bash
az group delete --name rg-neo4j-maf --yes --no-wait
```
