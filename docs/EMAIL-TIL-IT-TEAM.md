# Email til IT-teamet vedr. Nexus APT Proxy

---

**Emne:** APT proxy til Docker builds

Hej,

Vi skal bruge to APT proxy repositories i Nexus til vores Docker builds:

**1. Ubuntu Main:**
- Remote URL: `http://archive.ubuntu.com/ubuntu/`
- Distribution: `jammy`

**2. Ubuntu Security:**
- Remote URL: `http://security.ubuntu.com/ubuntu/`
- Distribution: `jammy-security`

**Pakker vi skal installere (21 stk.):**
```
curl, wget, ca-certificates, git, make, build-essential,
libssl-dev, zlib1g-dev, libbz2-dev, libreadline-dev, libsqlite3-dev,
llvm, libncurses5-dev, libncursesw5-dev, xz-utils, tk-dev,
libffi-dev, liblzma-dev, bash, tini
```

Når I har oprettet repositories, send mig bare URL'erne.

Dokumentation ligger i `stat-kube-zero` repo under `docs/IT-TEAM-NEXUS-SETUP.md`.

Tak! 🙂

Mvh,  
[Dit navn]

