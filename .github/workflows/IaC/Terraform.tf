# --- Provider Configuration ---
provider "google" {
  project = "project-cdd074dc-6291-4d7f-a2a" # CHANGE THIS
  region  = "us-central1"
}

# --- Networking ---
resource "google_compute_network" "main_vpc" {
  name                    = "ping-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "us-central1-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = "us-central1"
  network       = google_compute_network.main_vpc.id
}

# Required for Private IP Google Services (Redis/Postgres)
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "private-ip-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.main_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]
  update_on_creation_fail = true

  deletion_policy = "ABANDON"
}

# --- Firewall Rules ---

# 4.1: Allow all internal TCP traffic within the subnet
resource "google_compute_firewall" "allow_internal_tcp" {
  name    = "allow-internal-tcp"
  network = google_compute_network.main_vpc.id

  allow {
    protocol = "tcp"
    # No ports specified means ALL ports are allowed
  }

  source_ranges = ["10.0.1.0/24"]
}

# 4.2: Allow public ingress on ports 80, 6379, 5732 for GCE
resource "google_compute_firewall" "allow_public_ingress" {
  name    = "allow-public-gce-ingress"
  network = google_compute_network.main_vpc.id

  allow {
    protocol = "tcp"
    ports    = ["80", "5732", "6379", "8002"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["public-gce"]
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = google_compute_network.main_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # This is the specific CIDR range used by Google Identity-Aware Proxy
  source_ranges = ["35.235.240.0/20"]
}

resource "google_compute_firewall" "allow_swarm" {
  name    = "allow-docker-swarm"
  network = google_compute_network.main_vpc.id

  allow {
    protocol = "tcp"
    ports = ["2377", "7946"]
  }  # Swarm mgmt + node comms

  allow {
    protocol = "udp"
    ports = ["7946", "4789"]
  }  # Node comms + VXLAN overlay

  source_ranges = ["10.0.1.0/24"]  # internal only
}
# ---------------- x ------------------

# ----- Storage Bucket for configs (GCS) -----------
resource "google_storage_bucket" "app_gcs" {
  name          = "ping-configs"
  location      = "us-central1"
  force_destroy = true 
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "env_file" {
  name   = ".env"
  bucket = google_storage_bucket.app_gcs.name
  
  content = templatefile("${path.module}/templates/env.tpl", {
    redis_host = google_redis_instance.cache.host
  })
}

resource "google_storage_bucket_object" "ini_file" {
  name   = "pgbouncer.ini"
  bucket = google_storage_bucket.app_gcs.name
  
  content = templatefile("${path.module}/templates/pgbouncer.tpl", {
    db_host = google_sql_database_instance.ping_db.ip_address.0.ip_address
  })
}

resource "google_storage_bucket_object" "static_files" {
  for_each = toset([
    "docker-compose.yaml",
    "docker-stack.yaml",
    "userlist.txt",
    "run_docker.sh",
    "run_docker_worker.sh"
  ])

  name   = each.value
  bucket = google_storage_bucket.app_gcs.name
  source = "${path.module}/templates/${each.value}" 
}
# -------- x ----------

# --- Compute Engine (GCE) ---
resource "google_compute_instance" "app_server" {
  name         = "ping-gce-01"
  zone         = "us-central1-c"
  machine_type = "e2-standard-4"
  tags         = ["public-gce"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 10
      type  = "pd-balanced"
    }
  }

  network_interface {
    network    = google_compute_network.main_vpc.id
    subnetwork = google_compute_subnetwork.subnet.id
    access_config {}
  }

  # The replace function strips Windows carriage returns (\r) 
  # making the script Linux-safe regardless of your OS.
  metadata_startup_script = replace(<<-EOF
      #!/bin/bash
      
      # Log output so you can debug via 'cat /var/log/startup-script.log'
      exec > /var/log/startup-script.log 2>&1

      mkdir -p /ping
      cd /ping

      echo "Waiting for apt lock..."
      while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
        sleep 2
      done

      apt-get update
      apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release nano unzip

      # 1. Install Docker
      curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --yes --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

      apt-get update
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin dstat

      # 2. Grant permissions to your user (so 'docker ps' works without sudo)
      usermod -aG docker cheta

      # 3. Authenticate Docker
      gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

      # 4. Pull configs and run
      gcloud storage cp -r gs://ping-configs/* .
      chmod +x run_docker.sh
      ./run_docker.sh
  EOF
  , "\r", "")

  service_account {
    email  = "artifact-registry-puller-898@project-cdd074dc-6291-4d7f-a2a.iam.gserviceaccount.com"
    scopes = ["cloud-platform"]
  }

  depends_on = [
    google_storage_bucket_object.env_file,
    google_storage_bucket_object.ini_file,
    google_storage_bucket_object.static_files
  ]
}

resource "google_compute_instance" "worker" {
  count        = 0                    # number of workers
  name         = "ping-gce-worker-0${count.index + 1}"
  zone         = "us-central1-c"
  machine_type = "e2-standard-8"
  tags         = ["public-gce"]

  boot_disk {
    initialize_params {
      image  = "debian-cloud/debian-11"
      size   = 10
      type   = "pd-balanced"
    }
  }

  network_interface {
    network    = google_compute_network.main_vpc.id
    subnetwork = google_compute_subnetwork.subnet.id
    
    # This empty block gives the VM an ephemeral Public IP
    access_config {}
  }

  metadata_startup_script = replace(<<-EOF
      #!/bin/bash

      # Define and navigate to a working directory
      mkdir -p /ping
      cd /ping

      echo "Waiting for apt lock..."
      while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
        sleep 2
      done
      apt-get update
      apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release nano unzip

      # 1. Install Docker
      # Added --yes to prevent interactive prompts on reboot
      curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --yes --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

      apt-get update
      apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin dstat

      # 3. Authenticate Docker with GCP Artifact Registry (Non-interactive)
      gcloud auth configure-docker us-central1-docker.pkg.dev --quiet

      # 4. Get all config files and docker compose file from GCS and run
      gcloud storage cp -r gs://ping-configs/* .
      chmod +x run_docker_worker.sh
      ./run_docker_worker.sh
  EOF
  , "\r", "")

  service_account {
    email = "artifact-registry-puller-898@project-cdd074dc-6291-4d7f-a2a.iam.gserviceaccount.com"
    scopes = ["cloud-platform"]
  }

  depends_on = [google_compute_instance.app_server]  # manager first
}
# ---------- x -----------

# --- Redis (Memorystore) ---
resource "google_redis_instance" "cache" {
  name               = "ping-redis"
  tier               = "BASIC"
  memory_size_gb     = 8
  region             = "us-central1"
  location_id        = "us-central1-c"
  authorized_network = google_compute_network.main_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version      = "REDIS_6_X"

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

# --- PostgreSQL (Cloud SQL) ---
resource "google_sql_database_instance" "ping_db" {
  name             = "ping-postgres-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_15"
  region           = "us-central1"

  settings {
    # db-standard-2 (2 vCPU, 7.5GB RAM). Better suited for load testing 
    # than f1-micro, without paying for heavy enterprise tiers.
    tier              = "db-custom-2-7680" 
    availability_type = "ZONAL"
    disk_autoresize = false
    disk_size = 10
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main_vpc.id
    }

    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = false 
  depends_on          = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "my_db" {
  name     = "testdb"
  instance = google_sql_database_instance.ping_db.name
}

resource "google_sql_user" "db_user" {
  name     = "postgres"
  instance = google_sql_database_instance.ping_db.name
  password = "Ch92.8%%"
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}