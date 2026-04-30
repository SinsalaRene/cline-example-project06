# Azure Firewall Management - Setup Guide

This guide provides instructions for setting up and configuring the Azure Firewall Management application with Azure integration.

## Prerequisites

- Azure subscription with appropriate permissions
- Python 3.11 or higher
- Azure CLI (optional, for local authentication)

## Azure Service Principal Setup

The application uses Azure Service Principal authentication for API access. Create a service principal with the following steps:

### 1. Create a Service Principal

```bash
az login
az ad sp create-for-rbac --name "firewall-mgmt-service" --role Contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
```

This will output JSON containing:
- `appId` (client_id)
- `password` (client_secret)
- `tenant` (tenant_id)
- `subscription` (subscription_id)

### 2. Configure Firewall Policy Permissions

The service principal needs permissions for firewall management. Assign the required role:

```bash
az role assignment create \
  --role "Network Contributor" \
  --assignee appId_FROM_STEP_2 \
  --scope /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP
```

### 3. Required Permissions

The service principal needs the following Azure permissions:
- `Microsoft.Network/firewallPolicies/read` - Read firewall policies
- `Microsoft.Network/firewallPolicies/write` - Create/update firewall policies
- `Microsoft.Network/firewallPolicies/delete` - Delete firewall policies
- `Microsoft.Network/firewallPolicyRuleCollectionGroups/read` - Read rule collection groups
- `Microsoft.Network/firewallPolicyRuleCollectionGroups/write` - Create/update rule collection groups
- `Microsoft.Network/firewalls/read` - Read firewall status
- `Microsoft.Network/firewalls/write` - Update firewall configuration

## Environment Configuration

### 1. Copy the Environment Template

```bash
cd backend
cp .env.example .env
```

### 2. Configure Azure Settings

Edit the `.env` file with your Azure configuration:

```env
# Azure Configuration
azure_tenant_id=your-tenant-id-here
azure_client_id=your-client-id-here
azure_client_secret=your-client-secret-here
azure_subscription_id=your-subscription-id-here
azure_resource_group=your-resource-group-name
azure_region=eastus

# Database Configuration
database_url=sqlite:///./firewall_mgmt.db

# API Configuration
debug=true
secret_key=your-secret-key-change-in-production-min-16-chars
```

### 3. Required Azure Resources

Before using the application, ensure you have:
1. A resource group for firewall resources
2. A firewall policy created (optional, for initial configuration)

## Creating Azure Firewall Policy

### Via Azure Portal

1. Navigate to **Firewall policies** in the Azure Portal
2. Click **Create**
3. Select your resource group and region
4. Configure the policy settings
5. Click **Review + create**

### Via Azure CLI

```bash
az network firewall policy create \
  --resource-group YOUR_RESOURCE_GROUP \
  --name YOUR_FIREWALL_POLICY_NAME \
  --resource-group YOUR_RESOURCE_GROUP \
  --sku Standard
```

## Using the Azure Integration

### 1. Start the Application

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Test Azure Connection

```bash
curl -X POST http://localhost:8000/api/firewall/azure/status \
  -H "Content-Type: application/json" \
  -d '{
    "azure_resource_group": "your-resource-group",
    "azure_policy_name": "your-policy-name"
  }'
```

### 3. Import Rules from Azure

```bash
curl -X POST http://localhost:8000/api/firewall/import \
  -H "Content-Type: application/json" \
  -d '{
    "azure_resource_group": "your-resource-group",
    "azure_policy_name": "your-policy-name"
  }'
```

## Azure Firewall Rule Format

When importing from Azure, rules follow this structure:

```json
{
  "rule_name": "rule-name",
  "rule_collection_name": "collection-name",
  "priority": 100,
  "action": "Allow",
  "protocol": "Tcp",
  "source_addresses": ["10.0.0.1"],
  "destination_fqdns": ["example.com"],
  "destination_ports": [443]
}
```

### Rule Validation Rules

- **Collection Name**: 3-80 characters, alphanumeric with spaces, underscores, hyphens, dots
- **Priority**: 100-4096 for rule collections
- **Action**: Allow or Deny
- **Protocol**: Tcp, Udp, or Any
- **FQDN**: Valid DNS format
- **IP Address**: Valid IPv4 or CIDR notation
- **Ports**: 1-65535

## Troubleshooting

### Authentication Errors

If you see authentication errors:
1. Verify service principal credentials in `.env`
2. Check service principal permissions in Azure AD
3. Ensure tenant ID matches the service principal's tenant

### Resource Not Found

If resources are not found:
1. Verify resource group name is correct
2. Check firewall policy name matches exactly
3. Ensure the resource exists in the specified region

### Rate Limiting

Azure API has rate limits. If you see rate limit errors:
- The application implements automatic retry with exponential backoff
- Reduce the number of simultaneous operations
- Consider increasing the rate limit configuration

## Azure Firewall Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────>│    Backend       │────>│   Azure API    │
│   (Angular)     │     │   (FastAPI)      │     │   (Azure SDK)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Azure Firewall │
                     │   Policy        │
                     └─────────────────┘
```

## Security Best Practices

1. **Use managed identities** in production instead of client secrets
2. **Store secrets in Azure Key Vault** for production deployments
3. **Use least privilege** when assigning roles to the service principal
4. **Enable audit logging** for firewall policy changes
5. **Use private endpoints** for API access in production