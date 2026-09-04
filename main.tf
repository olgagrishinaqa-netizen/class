terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
}

variable "yc_token" {
  type = string
}

variable "image_tag" {
  type    = string
  default = "v1"
}

provider "yandex" {
  token     = var.yc_token
  zone      = "ru-central1-a"
  cloud_id  = "b1g8t1mb8u8pc0dblus6"
  folder_id = "b1g7f31a1r5b3kl9b3f7"
}

# 1. Привязываем роль к существующему аккаунту (используем его прямой ID)
resource "yandex_resourcemanager_folder_iam_member" "sa_registry_pull" {
  folder_id = "b1g7f31a1r5b3kl9b3f7"
  role      = "container-registry.images.puller"
  member    = "serviceAccount:ajemsqi8mffhfroos00r"
}

# 2. Создаем приватный реестр для Docker-образов
resource "yandex_container_registry" "class_registry" {
  name = "class-site-registry"
}

# 3. Серверный контейнер с привязкой существующего аккаунта
resource "yandex_serverless_container" "class_container" {
  name               = "class-site-container"
  memory             = 256
  execution_timeout  = "15s"
  service_account_id = "ajemsqi8mffhfroos00r"

  image {
    # ВНИМАНИЕ: подставляем новый ID созданного реестра, чтобы не было конфликтов
    url = "cr.yandex/${yandex_container_registry.class_registry.id}/class-site:${var.image_tag}"
    
    environment = {
      "DB_HOST"     = "rc1a-smdv2b694hmvhlit.mdb.yandexcloud.net"
      "DB_NAME"     = "class_db"
      "DB_USER"     = "db_admin"
      "DB_PASSWORD" = "SuperSecurePassword2026!"
    }
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
