terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }

  # Хранение стейта в Yandex Object Storage (совместимо с Terraform 1.5.7)
  backend "s3" {
    endpoint = "https://yandexcloud.net"
    bucket   = "class-site-tfstate"
    region   = "ru-central1"
    key      = "production/terraform.tfstate"

    skip_region_validation      = true
    skip_credentials_validation = true
  }
}

variable "yc_token" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "v1"
}

variable "service_account_id" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "flask_secret_key" {
  type      = string
  sensitive = true
  default   = "super-secret-prod-key-12345"
}

variable "network_id" {
  type        = string
  description = "ID VPC-сети для подключения к Managed PostgreSQL"
  default     = ""
}

variable "subnet_id" {
  type        = string
  description = "ID подсети для контейнера"
  default     = ""
}

provider "yandex" {
  token     = var.yc_token
  zone      = "ru-central1-a"
  cloud_id  = "b1g8t1mb8u8pc0dblus6"
  folder_id = "b1g7f31a1r5b3kl9b3f7"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_registry_pull" {
  folder_id = "b1g7f31a1r5b3kl9b3f7"
  role      = "container-registry.images.puller"
  member    = "serviceAccount:${var.service_account_id}"
}

resource "yandex_container_registry" "class_registry" {
  name      = "class-site-registry"
  folder_id = "b1g7f31a1r5b3kl9b3f7"
}

resource "yandex_serverless_container" "class_container" {
  name               = "class-site-container-prod"
  memory             = 256
  execution_timeout  = "60s"
  service_account_id = var.service_account_id

  dynamic "connectivity" {
    for_each = var.network_id != "" ? [1] : []
    content {
      network_id = var.network_id
    }
  }

  image {
    url = "cr.yandex/${yandex_container_registry.class_registry.id}/class-site:${var.image_tag}"

    environment = {
      "DB_HOST"     = "rc1a-smdv2b694hmvhlit.mdb.yandexcloud.net"
      "DB_NAME"     = "class_db"
      "DB_USER"     = "db_admin"
      "DB_PASSWORD" = var.db_password
      "SECRET_KEY"  = var.flask_secret_key
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "yandex_serverless_container_iam_binding" "public_viewer" {
  container_id = yandex_serverless_container.class_container.id
  role         = "serverless.containers.invoker"
  members      = ["system:allUsers"]
}

output "container_registry_id" {
  value = yandex_container_registry.class_registry.id
}

output "website_url" {
  value = yandex_serverless_container.class_container.url
}
