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
