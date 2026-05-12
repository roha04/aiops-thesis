# syntax=docker/dockerfile:1.6
# ─────────────────────────────────────────────────────────────────────────────
# Local Jenkins image preloaded with:
#   - Plugins listed in plugins.txt (installed at image build time)
#   - Configuration-as-Code (loaded from /var/jenkins_config/casc.yaml)
#   - Four ready-to-run pipeline jobs that POST to the AIOps webhook
#
# Built automatically by docker-compose (`build: ./jenkins`).
# ─────────────────────────────────────────────────────────────────────────────
FROM jenkins/jenkins:lts-jdk17

# Skip the setup wizard; admin user is created via JCasC
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false -Dpermissive-script-security.enabled=true" \
    CASC_JENKINS_CONFIG=/var/jenkins_config/casc.yaml

USER root

# Make sure curl + bash are present so the pipelines can POST to the backend
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ── Plugins ──────────────────────────────────────────────────────────────────
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# ── Configuration as Code ────────────────────────────────────────────────────
COPY casc.yaml /var/jenkins_config/casc.yaml

# ── Seed jobs (config.xml files) ─────────────────────────────────────────────
# Jenkins copies anything under /usr/share/jenkins/ref/jobs/<name>/config.xml
# into $JENKINS_HOME on first start, so jobs come up ready to run.
COPY jobs/ /usr/share/jenkins/ref/jobs/

USER jenkins
