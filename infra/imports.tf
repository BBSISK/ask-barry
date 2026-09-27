# Adopt the resources that already exist (created in the portal in Stage 3).
# Terraform 1.6+: plan shows "to import", apply records them in state; nothing is recreated.

locals {
  rg_id = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}"
  ai_id = "${local.rg_id}/providers/Microsoft.CognitiveServices/accounts/${var.ai_services_name}"
}

import {
  to = azurerm_resource_group.ask_barry
  id = local.rg_id
}

import {
  to = azurerm_cognitive_account.ai_services
  id = local.ai_id
}

import {
  to = azurerm_cognitive_deployment.chat
  id = "${local.ai_id}/deployments/gpt-4.1-mini"
}

import {
  to = azurerm_cognitive_deployment.embedding
  id = "${local.ai_id}/deployments/text-embedding-3-small"
}

import {
  to = azurerm_search_service.search
  id = "${local.rg_id}/providers/Microsoft.Search/searchServices/${var.search_service_name}"
}
