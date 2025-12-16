# Quick Reference: Nexus Setup for IT Team

## What We Need in Nexus

To build Docker images in the air-gapped environment, we need access to Ubuntu APT packages through Nexus.

## Nexus APT Proxy Configuration

### Repository 1: Ubuntu Main Repository

**Repository Name:** `apt-ubuntu` (or your choice)  
**Repository Type:** APT (proxy)  
**Remote Storage Location:** `http://archive.ubuntu.com/ubuntu/`  
**Distribution:** `jammy`  
**Flat:** No (hierarchical)

**Purpose:** Provides main Ubuntu packages (build-essential, curl, wget, etc.)

### Repository 2: Ubuntu Security Repository

**Repository Name:** `apt-ubuntu-security` (or your choice)  
**Repository Type:** APT (proxy)  
**Remote Storage Location:** `http://security.ubuntu.com/ubuntu/`  
**Distribution:** `jammy-security`  
**Flat:** No (hierarchical)

**Purpose:** Provides security updates for Ubuntu packages

## Example Nexus Configuration (Web UI)

```
Repository Manager → Repositories → Create repository → apt (proxy)

Name: apt-ubuntu
Format: apt
Online: Yes
Remote Storage: http://archive.ubuntu.com/ubuntu/
Distribution: jammy
Flat: No
```

## Exposed URLs

After creation, repositories will be accessible at:

```
http://srvnexus1.dst.dk:8081/repository/apt-ubuntu
http://srvnexus1.dst.dk:8081/repository/apt-ubuntu-security
```

**Note:** Replace `srvnexus1.dst.dk:8081` with your actual Nexus host and port.

## Testing the Setup

Once configured, test from any machine with Nexus access:

```bash
# Test main repository
curl -I http://srvnexus1.dst.dk:8081/repository/apt-ubuntu/dists/jammy/Release

# Test security repository  
curl -I http://srvnexus1.dst.dk:8081/repository/apt-ubuntu-security/dists/jammy-security/Release
```

Both should return **HTTP 200 OK**.

## What Happens After Setup

1. First Docker build will be **slow** (packages are downloaded and cached)
2. Subsequent builds will be **fast** (packages served from Nexus cache)
3. No internet access needed during Docker builds

## Required Packages List

The Docker build needs these packages (all available in Ubuntu 22.04):

**Build Tools:**
- build-essential
- make
- curl
- wget
- git

**Python Build Dependencies:**
- libssl-dev
- zlib1g-dev
- libbz2-dev
- libreadline-dev
- libsqlite3-dev
- libncurses5-dev
- libncursesw5-dev
- libffi-dev
- liblzma-dev
- tk-dev
- llvm
- xz-utils

**Runtime:**
- ca-certificates
- bash
- tini

Total size: ~500MB (with dependencies)

## Alternative: Pre-cache Packages

If you want to ensure packages are cached before we build:

```bash
# Install apt-transport-https on a test Ubuntu 22.04 machine
apt-get update
apt-get install -y build-essential curl wget git \
  libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
  libsqlite3-dev llvm libncurses5-dev libncursesw5-dev \
  xz-utils tk-dev libffi-dev liblzma-dev bash tini ca-certificates
```

This will populate the Nexus cache.

## Questions?

Contact: [Your contact info]

## See Also

- Full documentation: `docs/apt-proxy-setup.md`
- Nexus APT docs: https://help.sonatype.com/repomanager3/nexus-repository-administration/formats/apt-repositories

