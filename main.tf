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

provider "yandex" {
  token     = var.yc_token
  zone      = "ru-central1-a"
  cloud_id  = "b1g8t1mb8u8pc0dblus6"
  folder_id = "b1g7f31a1r5b3kl9b3f7"
}

# 1. Сеть и подсеть
resource "yandex_vpc_network" "default_net" {
  name = "class-site-net"
}

resource "yandex_vpc_subnet" "default_subnet" {
  name           = "class-site-subnet"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.default_net.id
  v4_cidr_blocks = ["10.5.0.0/24"]
}

# 2. Сервисный аккаунт для контейнера
resource "yandex_iam_service_account" "sa" {
  name        = "class-site-sa"
  description = "Сервисный аккаунт для скачивания образов"
}

resource "yandex_resourcemanager_folder_iam_member" "sa_registry_pull" {
  folder_id = "b1g7f31a1r5b3kl9b3f7"
  role      = "container-registry.images.puller"
  member    = "serviceAccount:${yandex_iam_service_account.sa.id}"
}

# 3. Приватный реестр для Docker-образов
resource "yandex_container_registry" "class_registry" {
  name = "class-site-registry"
}

# 4. Исправленный Serverless PostgreSQL
resource "yandex_mdb_postgresql_cluster" "serverless_postgres" {
  name        = "class-site-postgres"
  environment = "PRODUCTION"
  network_id  = yandex_vpc_network.default_net.id

  config {
    version = "15"
    # Для serverless-режима указывается специальный тип ресурса
    resources {
      resource_preset_id = "serverless-v1"
      disk_type_id       = "network-ssd"
      disk_size          = 10 # Минимальный размер, фактически плата только за хранение данных
    }
  }

  database {
    name  = "class_db"
    owner = "db_admin"
  }

  user {
    name     = "db_admin"
    password = "SuperSecurePassword2026!"
    permission {
      database_name = "class_db"
    }
  }

  # Хост обязателен, привязываем его к созданной подсети
  host {
    zone      = "ru-central1-a"
    subnet_id = yandex_vpc_subnet.default_subnet.id
  }
}

# 5. Исправленный серверный контейнер
resource "yandex_serverless_container" "class_container" {
  name               = "class-site-container"
  memory             = 256
  execution_timeout  = "15s"
  service_account_id = yandex_iam_service_account.sa.id

  image {
    url = "cr.yandex/${yandex_container_registry.class_registry.id}/class-site:v1"
    
    # Переменные окружения перенесены внутрь блока image
    environment = {
      "DB_HOST"     = yandex_mdb_postgresql_cluster.serverless_postgres.host[0].fqdn
      "DB_NAME"     = "class_db"
      "DB_USER"     = "db_admin"
      "DB_PASSWORD" = "SuperSecurePassword2026!"
    }
  }
}

# 6. Делаем сайт публичным
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
