# ASK-8: Entra ID sign-in instead of API keys.
#
# The live app (on Render) signs in as the ask-barry-render service principal. Its roles say
# exactly what it may do: call the models and READ the search index. A leaked API key would
# have unlocked everything on the resource, including deleting the index.
#
# Unlike main.tf, these resources are CREATED by Terraform, not imported, so keep the state
# file safe: losing it would leave the app registration unmanaged (it can be imported back).
#
# The client secret is deliberately NOT made here: a Terraform-made password would put
# the secret in the state file. Create it with the Azure CLI instead (docs/azure-setup.md).
#
# Managed identity replaces this service principal once the app runs on Azure compute.

data "azuread_client_config" "current" {}

resource "azuread_application" "render" {
  display_name = "ask-barry-render"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "render" {
  client_id = azuread_application.render.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

# --- The live app: least privilege ------------------------------------------------------------

resource "azurerm_role_assignment" "render_openai_user" {
  scope                = azurerm_cognitive_account.ai_services.id
  role_definition_name = "Cognitive Services OpenAI User" # inference only: no keys, no deployments
  principal_id         = azuread_service_principal.render.object_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "render_search_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader" # query only: can't write or delete documents
  principal_id         = azuread_service_principal.render.object_id
  principal_type       = "ServicePrincipal"
}

# --- You, signed in with `az login`, for local development and ingestion ------------------------
# Owner of the subscription is not enough: Owner manages resources, data-plane roles use them.

resource "azurerm_role_assignment" "me_openai_user" {
  scope                = azurerm_cognitive_account.ai_services.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = data.azuread_client_config.current.object_id
  principal_type       = "User"
}

resource "azurerm_role_assignment" "me_search_writer" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor" # scripts.ingest uploads and deletes chunks
  principal_id         = data.azuread_client_config.current.object_id
  principal_type       = "User"
}

resource "azurerm_role_assignment" "me_search_service" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Service Contributor" # scripts.ingest creates or updates the index schema
  principal_id         = data.azuread_client_config.current.object_id
  principal_type       = "User"
}
