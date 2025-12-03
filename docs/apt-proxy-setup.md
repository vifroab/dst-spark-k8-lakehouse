# APT Proxy Configuration for Air-Gapped Environments

## Overview

In air-gapped environments, Docker builds cannot access internet-based APT repositories. This guide explains how to configure APT to use your Nexus APT proxy.

## Required Packages

The Docker build needs these Ubuntu packages (from `docker/spark-base/Dockerfile`):

### Build Tools
- `build-essential` - GCC, G++, make, etc.
- `make`
- `curl`
- `wget`
- `git`

### Python Build Dependencies
- `libssl-dev` - SSL/TLS support
- `zlib1g-dev` - Compression support
- `libbz2-dev` - Bzip2 compression
- `libreadline-dev` - Interactive shell support
- `libsqlite3-dev` - SQLite database support
- `libncurses5-dev`, `libncursesw5-dev` - Terminal UI support
- `libffi-dev` - Foreign function interface
- `liblzma-dev` - LZMA compression
- `tk-dev` - Tkinter GUI support
- `llvm` - LLVM compiler
- `xz-utils` - XZ compression

### Runtime Dependencies
- `ca-certificates` - SSL certificates
- `bash` - Shell
- `tini` - Init system for containers

## Setup Instructions

### Step 1: Nexus Configuration (IT Team)

Your Nexus administrator needs to create **APT proxy repositories** that mirror Ubuntu repositories:

#### Repository 1: Ubuntu Main (apt-ubuntu)
- **Type:** APT (proxy)
- **Remote URL:** `http://archive.ubuntu.com/ubuntu/`
- **Distribution:** `jammy` (Ubuntu 22.04)
- **Components:** `main restricted universe multiverse`

#### Repository 2: Ubuntu Security (apt-ubuntu-security)
- **Type:** APT (proxy)
- **Remote URL:** `http://security.ubuntu.com/ubuntu/`
- **Distribution:** `jammy-security`
- **Components:** `main restricted universe multiverse`

**Example Nexus URLs:**
```
http://srvnexus1.dst.dk:8081/repository/apt-ubuntu
http://srvnexus1.dst.dk:8081/repository/apt-ubuntu-security
```

### Step 2: Update sources.list File

Edit `docker/spark-base/sources.list.nexus` with your actual Nexus URLs:

```bash
# Replace srvnexus1.dst.dk:8081 with your Nexus host and port
# Replace repository names (apt-ubuntu, apt-ubuntu-security) with your actual repo names

deb http://YOUR-NEXUS-HOST:PORT/repository/apt-ubuntu jammy main restricted universe multiverse
deb http://YOUR-NEXUS-HOST:PORT/repository/apt-ubuntu jammy-updates main restricted universe multiverse
deb http://YOUR-NEXUS-HOST:PORT/repository/apt-ubuntu jammy-backports main restricted universe multiverse
deb http://YOUR-NEXUS-HOST:PORT/repository/apt-ubuntu-security jammy-security main restricted universe multiverse
```

### Step 3: Enable in Dockerfile

Uncomment this line in `docker/spark-base/Dockerfile` (around line 22):

```dockerfile
# Before (commented out):
# COPY sources.list.nexus /etc/apt/sources.list

# After (uncommented):
COPY sources.list.nexus /etc/apt/sources.list
```

### Step 4: Build the Image

```bash
# Build with Nexus base image and APT proxy
docker build \
  --build-arg BASE_IMAGE=srvnexus1.dst.dk:18079/eclipse-temurin:11-jdk-jammy \
  -t statkube/spark-base:spark3.5.3-py3.12-1 \
  -f docker/spark-base/Dockerfile \
  docker/spark-base
```

## Testing APT Configuration

### Test 1: Verify Nexus APT Proxy Works

```bash
# From a machine with access to Nexus
curl -I http://srvnexus1.dst.dk:8081/repository/apt-ubuntu/dists/jammy/Release
```

Expected: HTTP 200 OK

### Test 2: Build Docker Image

```bash
docker build --no-cache -t test-apt -f docker/spark-base/Dockerfile docker/spark-base
```

If APT proxy is working, you should see:
```
Step X/Y : RUN apt-get update
---> Running in xxxxx
Get:1 http://srvnexus1.dst.dk:8081/repository/apt-ubuntu jammy InRelease [...]
Get:2 http://srvnexus1.dst.dk:8081/repository/apt-ubuntu jammy-updates InRelease [...]
...
Reading package lists... Done
```

## Troubleshooting

### Error: "Could not resolve host"
**Problem:** DNS not configured or Nexus hostname is wrong

**Solution:** 
- Verify Nexus hostname: `ping srvnexus1.dst.dk`
- Check sources.list for typos

### Error: "404 Not Found"
**Problem:** Repository name or URL is incorrect

**Solution:**
- Verify Nexus repository names in web UI
- Ensure repositories are published and online
- Check URL format matches your Nexus configuration

### Error: "Failed to fetch"
**Problem:** Nexus APT proxy hasn't cached packages yet

**Solution:**
- Nexus proxies cache on first request
- First build may be slower as packages are cached
- Retry the build

### Error: "Certificate verification failed"
**Problem:** SSL certificate issues

**Solution:**
- Use HTTP instead of HTTPS in sources.list (if on private network)
- Or configure CA certificates in Docker build

## Online vs On-Prem Modes

### Online Mode (Internet Access)
Leave `sources.list.nexus` line **commented** in Dockerfile:
```dockerfile
# COPY sources.list.nexus /etc/apt/sources.list
```

Ubuntu will use default internet repositories.

### On-Prem Mode (Air-Gapped)
**Uncomment** the line in Dockerfile:
```dockerfile
COPY sources.list.nexus /etc/apt/sources.list
```

APT will use your Nexus proxy.

## Summary Checklist

For your IT team to enable Docker builds in air-gapped environment:

- [ ] Nexus APT proxy repository for Ubuntu main (jammy)
- [ ] Nexus APT proxy repository for Ubuntu security (jammy-security)
- [ ] Update `sources.list.nexus` with correct Nexus URLs
- [ ] Uncomment COPY line in Dockerfile
- [ ] Test: `curl` Nexus APT URLs to verify they work
- [ ] Test: Build Docker image and verify packages install
- [ ] Document: Save Nexus repository URLs for team reference

## Reference Links

- Nexus APT Repository Documentation: https://help.sonatype.com/repomanager3/nexus-repository-administration/formats/apt-repositories
- Ubuntu Package Search: https://packages.ubuntu.com/
- Docker Dockerfile Reference: https://docs.docker.com/engine/reference/builder/

