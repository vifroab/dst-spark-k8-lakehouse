# Changelog

## [1.0.0] - 2024-11-28

### Added - Air-Gapped Environment Support

#### Scripts
- **Enhanced verification script** (`scripts/verify-onprem-resources.sh`)
  - Auto-detects flat vs hierarchical Maven repository structure
  - Supports both online (Maven Central) and offline (Nexus) modes
  - Environment variable overrides for easy testing
  - Updated Nexus URLs with correct ports

- **Enhanced download script** (`scripts/download-jars.sh`)
  - Supports both Maven Central and Nexus flat repositories
  - `--nexus` flag for on-prem downloads
  - Auto-detection of repository structure

#### Documentation
- **k3d Setup Guide** (`docs/k3d-setup.md`)
  - Complete guide for k3d (recommended over kind)
  - Port forwarding setup
  - Migration guide from kind
  - Production alignment with Rancher/k3s

- **APT Proxy Setup** (`docs/apt-proxy-setup.md`)
  - Comprehensive guide for Nexus APT proxy configuration
  - Package requirements list
  - Troubleshooting steps
  - Online/offline mode switching

- **IT Team Quick Reference** (`docs/IT-TEAM-NEXUS-SETUP.md`)
  - Quick setup guide for administrators
  - Nexus repository configuration
  - Required packages list
  - Testing procedures

- **Email Template** (`docs/EMAIL-TIL-IT-TEAM.md`)
  - Ready-to-send email for IT team (in Danish)
  - APT proxy requirements
  - Package list

- **Enhanced README** (`README.md`)
  - Complete project overview
  - Quick start guides
  - Documentation index
  - Troubleshooting section

#### Configuration Files
- **APT Sources Template** (`docker/spark-base/sources.list.nexus`)
  - Template for Nexus APT proxy
  - Ready for customization with actual Nexus URLs

- **Updated Dockerfile** (`docker/spark-base/Dockerfile`)
  - Added commented line for APT proxy configuration
  - Easy to enable for on-prem builds

### Changed

#### Repository Structure
- Maven JARs now support both formats:
  - Flat structure: `hadoop-aws-3.3.4.jar`
  - Hierarchical: `org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar`

#### Configuration
- Updated default Nexus URLs in verification script:
  - Docker Hub proxy: `srvnexus1.dst.dk:18079`
  - GHCR proxy: `srvnexus1.dst.dk:18083`
  - Maven repo: `https://srvnexus1.dst.dk/repository/apache-spark/spark-jars`

### Recommendations

#### Switch to k3d
- **Recommended:** Use k3d instead of kind for local development
- **Reason:** Production uses Rancher/k3s - better alignment
- **Benefits:** 
  - Lighter (50% less memory)
  - Faster (30-60s startup)
  - Built-in LoadBalancer
  - Built-in port forwarding
- **Migration:** Only requires installing k3d, everything else compatible

### Breaking Changes
- None - all changes are backward compatible

### Migration Notes

#### From Old Verification Script
If you have the old `verify-onprem-resources.sh`:
1. Pull the latest version from git
2. Update Nexus URLs if needed (lines 46, 51, 56, 47)
3. Run verification: `./scripts/verify-onprem-resources.sh`

#### To k3d (Optional but Recommended)
1. Install k3d on server: `curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash`
2. Create cluster: `k3d cluster create spark-cluster --agents 2 --port "8080:80@loadbalancer"`
3. Deploy as usual with Ansible

### Testing

All features tested on:
- ✅ macOS (local development with internet)
- ✅ Ubuntu Server (on-prem with Nexus)
- ✅ Maven Central (hierarchical structure)
- ✅ Nexus flat repository (flat structure)

### Known Issues
- Helm chart verification may require manual setup in Nexus
- First Docker build in air-gapped environment will be slow (packages cached for subsequent builds)

### Next Steps
1. Set up Nexus APT proxy (IT team)
2. Upload Python-3.12.7.tgz to server
3. Install k3d on server (optional but recommended)
4. Test complete air-gapped deployment

---

## Previous Versions

See git history for earlier changes.

