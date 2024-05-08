# Testbed

Container orchestration for the Global Named Data Networking Testbed.

## Overview

All services are run with Docker Compose and pull automatically built images from upstream repositories. A cron job in the `master` container polls this Git repository and deploys changes automatically.

The various components are:
- [framework](./framework/): Template rendering (Jinja2) and service management (Docker Compose) framework
- [host_vars](./host_vars/): Host-specific configuration
- [templates](./templates/): Jinja2 templates for service configuration
- [scripts](./scripts/): Shell scripts and cron jobs
- [anchors](./anchors/): Testbed trust anchor certificates

The global services configuration is defined in [docker-compose.yml](docker-compose.yml) and [config.yml](config.yml).

## Usage

1. A recent version of Docker must be installed on the target node.
1. Clone this repository (conventionally to `/home/ndnops/testbed`).
1. Define secrets in a `.env` file in the root directory of this repo..
1. Add a `MANAGED_HOST` variable to the `.env`, e.g. `MANAGED_HOST=UCLA`.
1. Define host-specific Docker Compose profiles as `COMPOSE_PROFILES` in `.env`.
1. Run `docker-compose up -d` to start the node.

The master node starts first and renders the templates. After this, the master runs a cron job to poll the Git repository.

A cron job is required on the host for some tasks. Make sure the cron user is present in the `docker` group.

```cron
*/5 * * * * /bin/bash /home/ndnops/testbed/scripts/cron-host.sh
```

## Certificate Management

The master container will automatically attempt to get certificates initiall if they don't exist. Certificates will not be automatically renewed. To renew certificates, run the following command:

```bash
# Renew certificates
docker compose exec master bash /testbed/dist/ndncert/renew.sh --force
docker compose exec master bash /testbed/dist/nlsr/renew.sh --force
docker compose exec master bash /testbed/dist/ndn-python-repo/renew.sh --force

# Restart containers
docker compose restart nlsr ndncert serve-certs ndn-python-repo
```

To get the list of currently installed certificates, run

```bash
docker compose exec -e HOME=/testbed/dist/ndncert master ndnsec list -c
docker compose exec -e HOME=/testbed/dist/nlsr master ndnsec list -c
docker compose exec -e HOME=/testbed/dist/ndn-python-repo master ndnsec list -c
```

## Development

For debugging and development, you can define `DEBUG=1` in your `.env` file. This will prevent the `dist` folder from auto-rendering and disable git polling. You can then use docker compose as usual to manage the containers.

## Unattended Upgrades

Set up unattended upgrades on the host to automatically install security updates.

```bash
sudo apt-get update && sudo apt-get install unattended-upgrades
```

The following configuration is recommended:

```conf
# /etc/apt/apt.conf.d/50unattended-upgrades

Unattended-Upgrade::Allowed-Origins {
        "${distro_id}:${distro_codename}";
        "${distro_id}:${distro_codename}-security";
        "${distro_id}ESMApps:${distro_codename}-apps-security";
        "${distro_id}ESM:${distro_codename}-infra-security";
        "${distro_id}:${distro_codename}-updates";
        "${distro_id}:${distro_codename}-proposed";
        "${distro_id}:${distro_codename}-backports";
        "Docker:${distro_codename}";
};

Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
```

Enable automatic updates in the following file:

```conf
# /etc/apt/apt.conf.d/20auto-upgrades

APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
```

After this, enable the service and run the initial upgrade:

```bash
sudo systemctl enable unattended-upgrades
sudo systemctl start unattended-upgrades
sudo unattended-upgrades --debug
```
