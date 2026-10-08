# Endpoints only: keys are never read or output by Terraform.

output "ai_services_endpoint" {
  description = "Base endpoint for Azure OpenAI (AZURE_OPENAI_ENDPOINT)."
  value       = azurerm_cognitive_account.ai_services.endpoint
}

output "search_endpoint" {
  description = "Azure AI Search endpoint (AZURE_SEARCH_ENDPOINT)."
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}

# ASK-8: IDs for Render's AZURE_TENANT_ID and AZURE_CLIENT_ID. Identifiers, not secrets.

output "render_tenant_id" {
  description = "Entra tenant (AZURE_TENANT_ID on Render)."
  value       = data.azuread_client_config.current.tenant_id
}

output "render_client_id" {
  description = "ask-barry-render app registration (AZURE_CLIENT_ID on Render)."
  value       = azuread_application.render.client_id
}

# ASK-34: set as the repository VARIABLE AZURE_CLIENT_ID (Settings > Secrets and variables > Actions > Variables).

output "github_client_id" {
  description = "ask-barry-github app registration, used by the nightly refresh workflow."
  value       = azuread_application.github.client_id
}
