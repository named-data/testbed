# NLSR Patch 7818 Integration Guide

## Overview

This guide documents the changes required to integrate NLSR Gerrit Change 7818 ("lsdb: recover lost LSA seqNo from network via sync") into the Named Data testbed.

**Change 7818:** https://gerrit.named-data.net/c/NLSR/+/7818

**Problem Solved (Issue #5386):** When an NLSR router's sequence number file is corrupted or lost, the router would restart with sequence number 0 and other routers would ignore its LSAs because they expected higher sequence numbers. Patch 7818 enables automatic recovery of the sequence number from the network via sync protocol.

---

## Changes Required

### 1. NLSR Dockerfile (`nlsr.Dockerfile`)

The Dockerfile builds NLSR with patch 7818 applied using Named Data's base images.

**Key changes:**

- Use `ghcr.io/named-data/ndn-cxx-build` and `ghcr.io/named-data/ndn-cxx-runtime` as base images (not Ubuntu) - this ensures proper library paths and dependencies
- Set `ENV HOME=/config` in the runtime stage - required for ndn-cxx to find the identity database (PIB)
- Build psync from source (not available in base images)
- Use patch revision 6 (latest): `refs/changes/18/7818/6`
- Configure NLSR with `--with-psync` to find psync
- Install `libboost-iostreams1.83.0` for runtime

```dockerfile
# Critical environment variable - ndn-cxx looks for PIB at $HOME/.ndn/
ENV HOME=/config
```

### 2. Docker Compose Override (`docker-compose.override.yml`)

Override to use the patched NLSR image:

```yaml
services:
  nlsr:
    image: ghcr.io/a-thieme/nlsr:patch-7818-v3
```

### 3. NLSR Config Template (`templates/nlsr/nlsr.conf.j2`)

**Critical fix:** The advertising section format changed in the patched NLSR.

**Old format (rejected by patch 7818):**
```jinja
advertising
{
  {% for prefix in advertised_prefixes %}
    prefix {{ prefix }}
  {% endfor %}
}
```

**New format (required by patch 7818):**
```jinja
advertising
{
  {% for prefix in advertised_prefixes %}
    {{ prefix }} 1
  {% endfor %}
}
```

The format changed from `prefix <name>` to `<name> <cost>` (key-value format).

---

## Building the Patched Image

```bash
# Build the image
docker build -t ghcr.io/<username>/nlsr:patch-7818 -f nlsr.Dockerfile .

# Push to registry
docker push ghcr.io/<username>/nlsr:patch-7818
```

## Deploying on Testbed Nodes

On each testbed node:

```bash
# Pull or update the image
docker-compose pull

# Restart NLSR
docker-compose up -d nlsr
```

---

## Verification

### Check NLSR Version
```bash
docker exec testbed-nlsr-1 nlsr -V
# Expected: 24.08+git.7e80068b (or similar with 7e80068 commit)
```

### Check Identity Loading
```bash
docker logs testbed-nlsr-1 2>&1 | grep identity
# Expected: Should show proper router identity, NOT "not found"
```

### Verify Sequence Recovery Works

1. Corrupt the sequence file:
```bash
docker stop testbed-nlsr-1
echo -e "AdjLsaSeqNo: 5\nNameLsaSeqNo: 5" > /path/to/state/nlsrSeqNo.txt
docker start testbed-nlsr-1
```

2. Check recovery:
```bash
docker logs testbed-nlsr-1 2>&1 | grep "Received sync update for own router"
# Or check sequence numbers:
docker exec testbed-nlsr-1 cat /config/state/nlsrSeqNo.txt
# Should show higher values than 5 (recovered from network)
```

### Check Neighbor Connectivity

From a neighbor node (e.g., Singapore):
```bash
docker exec testbed-nlsr-1 nlsrc lsdb | grep -A5 osaka
# Should show current sequence numbers (not stale)
```

---

## Troubleshooting

### "Router identity not found" / "NLSR is running without security"

**Cause:** The `HOME=/config` environment variable is missing.

**Fix:** Ensure the Dockerfile includes `ENV HOME=/config`

### "Invalid cost format; only integers are allowed"

**Cause:** Advertising section uses old format `prefix <name>` instead of `<name> <cost>`

**Fix:** Update `templates/nlsr/nlsr.conf.j2` to use `{{ prefix }} 1` format

### Sequence numbers stuck or not increasing

**Possible causes:**
1. Security not working (check identity logs)
2. Firewall blocking UDP port 6363
3. Network connectivity issues between nodes

---

## Image Tags

| Tag | Description |
|-----|-------------|
| `patch-7818-v1` | Initial build, wrong advertising format |
| `patch-7818-v2` | Fixed advertising format, missing HOME=/config |
| `patch-7818-v3` | **Current working version** - all fixes applied |

---

## Related Files

- `nlsr.Dockerfile` - Multi-stage build for patched NLSR
- `docker-compose.override.yml` - Override to use patched image
- `templates/nlsr/nlsr.conf.j2` - NLSR configuration template
