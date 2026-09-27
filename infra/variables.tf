variable "subscription_id" {
  description = "Azure subscription ID. Set with: export TF_VAR_subscription_id=$(az account show --query id -o tsv)"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group that holds the Foundry (AI Services) resource."
  type        = string
  default     = "rg-ask-barry"
}

variable "location" {
  description = "Region of the resource group and the Foundry resource."
  type        = string
  default     = "swedencentral"
}

variable "ai_services_name" {
  description = "Foundry (Azure AI Services) resource that hosts the model deployments."
  type        = string
  default     = "barrybsisk-6154-resource"
}

variable "search_service_name" {
  description = "Azure AI Search service (Free tier)."
  type        = string
  default     = "ask-barry-search"
}

variable "search_location" {
  description = "The search service was created in a different region from the resource group."
  type        = string
  default     = "switzerlandwest"
}

variable "chat_capacity" {
  description = "gpt-4.1-mini rate limit, in thousands of tokens per minute."
  type        = number
  default     = 100
}

variable "embedding_capacity" {
  description = "text-embedding-3-small rate limit, in thousands of tokens per minute."
  type        = number
  default     = 10
}
