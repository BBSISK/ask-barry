# Endpoints only: keys are never read or output by Terraform.

output "ai_services_endpoint" {
  description = "Base endpoint for Azure OpenAI (AZURE_OPENAI_ENDPOINT)."
  value       = azurerm_cognitive_account.ai_services.endpoint
}

output "search_endpoint" {
  description = "Azure AI Search endpoint (AZURE_SEARCH_ENDPOINT)."
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}
