# Ask Barry's Azure resources, described as code (Stage 7e).
#
# These resources were first created by hand in the Azure portal (Stage 3, see docs/azure-setup.md).
# imports.tf adopts them into Terraform state, so a plan should show only imports: nothing is
# created, changed or destroyed. prevent_destroy guards every resource against an accidental
# replacement.
#
# Deliberately not managed here:
#   - the Foundry project inside the AI Services resource (provider support is recent);
#   - the subscription budget alert (created in the portal; importing it needs its exact alert settings);
#   - keys and secrets: Terraform never reads or outputs them.

resource "azurerm_resource_group" "ask_barry" {
  name     = var.resource_group_name
  location = var.location

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_cognitive_account" "ai_services" {
  name                          = var.ai_services_name
  resource_group_name           = azurerm_resource_group.ask_barry.name
  location                      = azurerm_resource_group.ask_barry.location
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = var.ai_services_name
  local_auth_enabled            = false # ASK-22: Entra ID only; API keys are rejected
  public_network_access_enabled = true
  project_management_enabled    = true

  # As created in the portal: public access, no IP restrictions.
  network_acls {
    default_action = "Allow"
    ip_rules       = []
  }

  identity {
    type = "SystemAssigned"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_cognitive_deployment" "chat" {
  name                   = "gpt-4.1-mini"
  cognitive_account_id   = azurerm_cognitive_account.ai_services.id
  version_upgrade_option = "OnceNewDefaultVersionAvailable"
  rai_policy_name        = "Microsoft.DefaultV2"

  model {
    format  = "OpenAI"
    name    = "gpt-4.1-mini"
    version = "2025-04-14"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.chat_capacity
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                   = "text-embedding-3-small"
  cognitive_account_id   = azurerm_cognitive_account.ai_services.id
  version_upgrade_option = "OnceNewDefaultVersionAvailable"
  rai_policy_name        = "Microsoft.DefaultV2"

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.embedding_capacity
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_search_service" "search" {
  name                          = var.search_service_name
  resource_group_name           = azurerm_resource_group.ask_barry.name
  location                      = var.search_location
  sku                           = "free"
  local_authentication_enabled  = false # ASK-22: Entra ID only (auth_failure_mode only applies with keys on)
  public_network_access_enabled = true

  # Azure reports the free semantic ranker as "free", but the provider rejects that setting on
  # the Free tier: leave it as Azure has it rather than trying to "fix" it.
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [semantic_search_sku]
  }
}
