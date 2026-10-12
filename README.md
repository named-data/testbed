# Testbed

Container orchestration for the Global Named Data Networking Testbed.

[![Lint](https://github.com/named-data/testbed/actions/workflows/lint.yml/badge.svg)](https://github.com/named-data/testbed/actions/workflows/lint.yml)
[![Docker](https://github.com/named-data/testbed/actions/workflows/docker.yml/badge.svg)](https://github.com/named-data/testbed/actions/workflows/docker.yml)
[![Status Page](https://img.shields.io/website?url=https%3A%2F%2Fnamed-data.github.io%2Ftestbed%2F&up_message=online&down_message=offline&label=status%20page)](https://named-data.github.io/testbed/)
[![Map](https://img.shields.io/badge/map-live-brightgreen)](https://play.ndn.today/?testbed=1)

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
*/6 * * * * /bin/bash /home/ndnops/testbed/scripts/cron-host.sh
```

## Certificate Management

The master container provisions certificates before marking itself ready and checks them for renewal every five minutes. To force renewal manually, run the following commands:

```bash
# Renew certificates
docker compose exec master bash /testbed/dist/ndncert/renew.sh --force
docker compose exec master bash /testbed/dist/nlsr/renew.sh --force
docker compose exec master bash /testbed/dist/ndn-python-repo/renew.sh --force
docker compose exec master bash /testbed/dist/ndnd-repo/renew.sh --force

# Restart containers
docker compose restart nlsr ndncert serve-certs ndn-python-repo ndnd-repo
```

To get the list of currently installed certificates, run

```bash
docker compose exec -e HOME=/testbed/dist/ndncert master ndnsec list -c
docker compose exec -e HOME=/testbed/dist/nlsr master ndnsec list -c
docker compose exec -e HOME=/testbed/dist/ndn-python-repo master ndnsec list -c
docker compose exec ndnd-repo /ndnd sec key-list dir:///config/keys

# For root CA only
docker compose exec -e HOME=/testbed/root-ca-home master ndnsec list -c
```

## NDNd Repository

Each node runs the pinned `ndnd-repo` container with identity `<default_prefix>/ndnd/repo` (e.g. `/ndn/edu/ucla/ndnd/repo`). Master generates a dedicated key, obtains a certificate from the local site CA, and installs the public chain selected by `globals.ndnd_repo_anchors`. The repo can write only its keychain and storage; it has no access to CA private keys or master renewal scripts.

Certificates last up to 90 days, bounded by the issuing chain, and renew with 30 days remaining. Renewal reuses the key and restarts the repo when credentials change. Failed signing preserves the installed certificate. Pending dependent renewals and service reloads survive a partially failed site renewal and retry on the next poll. Back up `dist/ndnd-repo/keys` and `dist/ndnd-repo/storage`. Group enrollment ends on restart by design; applications enroll again while stored data persists.

Before merging this change into the branch polled by nodes, publish an NDNd image containing commit `cfffe287` or later and rebuild `testbed-master` from this Dockerfile. The master needs `python-ndn==0.5.2` to compile NDNd's LVS format; the previously pinned master image and January NDNd image are incompatible. Use the two repositories' existing Docker workflows; no new CI is needed. Compose keeps the existing dated-image convention. Publish the dated images pinned in Compose before rollout; if the workflows publish on a different date, update the pins to those published tags.

Master compiles the management trust schema while rendering configuration. Any user certified directly by a configured testbed site may enroll or leave groups; user identities may have one to five components below that site's prefix. Send commands to `<site>/ndnd/repo/32=cmd`, with embedded signed Data named `<user>/32=repo/<version>`. Publish application security-config objects as `<user>/32=repo-security/<version>/<segment>`. The schema binds these packets to the user's identity and authorizes responses only from the local repo key. Applications retain control of per-group data schemas and should validate responses using the same root-to-site-to-repo rules.

The active root expires on December 31, 2026. Before expiry, distribute its replacement, add it to `ndnd_repo_anchors`, and renew site certificates before removing the old root. Root rollover is separate from automatic site/repo renewal.

## Development

For debugging and development, you can define `DEBUG=1` in your `.env` file. This will prevent the `dist` folder from auto-rendering and disable git polling. You can then use docker compose as usual to manage the containers.

Some helpful bash aliases are provided in `bash_aliases.sh` for executing ndn tools inside the running containers.

```bash
source bash_aliases.sh
echo -e "\nsource $(pwd)/bash_aliases.sh\n" >> ~/.bashrc  # make it permanent

# Now you can use nfdc or ndn-tools for debugging
nfdc status report
ndnpeek /ndn/edu/ucla/ping/test | ndndissect
```

The master service runs internal cron jobs for polling. You can trigger these manually during debugging (only when not in DEBUG mode).

```bash
# cron-master pulls the git repo and restarts containers if required
docker compose exec -e "SKIP_SLEEP=1" master bash /testbed/scripts/cron-master.sh

# cron-status regenerates status json
docker compose exec -e "SKIP_SLEEP=1" master bash /testbed/scripts/cron-status.sh
```

## Unattended Upgrades

Set up unattended upgrades on the host to automatically install security updates.

```bash
sudo apt-get update && sudo apt-get install -y unattended-upgrades
```

The following configuration is recommended:

```aptconf
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

```aptconf
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
