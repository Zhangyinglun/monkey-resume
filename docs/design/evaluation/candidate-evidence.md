# Synthetic candidate evidence

This entire case is invented for evaluation. It describes one candidate and is
not derived from an actual person's employment, contact information, or resume.

## Profile

- P1: An earlier source used the display name **Alex**.
- P2: The candidate later explicitly corrected it to **Alex Chen**, saying,
  "Use Alex Chen on my resume." P2 supersedes P1 for current display.
- P3: The supplied contact string is `alex.chen@example.org`.
- P4: Bachelor's degree in Computer Science, Example University, 2018.

## Employment N: Northstar Cloud — Software Engineer, 2022–Present

The original source explicitly nests all the following projects under this
employment. That source relationship is evidence, not a conclusion based on
project-name similarity.

- N1 / Queue project: Developed **PulseBus**, a high-throughput message queue
  backend carrying authentication events, based on Azure Event Hubs. Improved
  queue architecture and implemented restart-based mitigation for blocked
  queues. Within the candidate's supported incident scope, **90%** of incidents
  were automatically mitigated within **30 minutes of detection**. This excludes
  subsequent human handling. Failed mitigations generated logs and context for
  escalation. The metric belongs to this queue-recovery system.
- N2 / Authentication project: Built C#/ASP.NET Core services with token
  validation, tenant isolation, and endpoint authorization for a platform
  supporting **two million enterprise tenants**. Operated stateless Docker
  services on AKS across Availability Zones, using health checks, canary releases,
  and rollback. The **overall authentication service SLA is 99.99%**; the source
  does not give PulseBus its own SLA or measured uptime.
- N3 / Operational diagnostics: Integrated Kusto/KQL telemetry, operational logs,
  and Copilot diagnostics. Reduced **fault-localization time by 80%**. This is
  diagnosis time, not end-to-end incident recovery time. Participated in on-call
  and production readiness reviews.
- N4 / Cooling project: Technically led a **five-person** team building
  data-center cooling observability and diagnostic workflows in C#/.NET. Work
  included telemetry pipelines, multi-signal risk triggers, and alert deduplication
  and cooldowns. Production GPU-throttling incident frequency decreased
  **approximately 10% versus the historical baseline**. The system monitored,
  diagnosed, and reported; engineers made remediation decisions. It did not
  autonomously resolve cooling failures. N1's 90%/30-minute metric is not N4's.
- N5 / Internal support assistant: Built Python ingestion and retrieval-augmented
  generation for an authentication-support assistant, reducing manual handling
  time by **85%**. Owned data ingestion, retrieval, model evaluation, and
  deployment. A colleague performed fine-tuning. This is not the cooling workflow
  or the queue-recovery system.
- N6 / Engineering practice: Used GitHub Copilot and Claude Code for tests,
  refactoring, and security fixes. Engineers validated changes through human
  review, CI, and staged releases.

## Employment H: Harbor Ads — Software Engineer, 2018–2022

- H1: Developed Go services and integrated Kafka events, MySQL storage, and Redis
  caching. Kafka work was application integration, not broker administration.
- H2: Deployed Docker/Kubernetes services across two cloud environments with
  canary releases and rolling deployments.
- H3: Built React advertising screens. No infra-specific result is given.

## Explicit gaps and constraints

- G1: Candidate reported **no Terraform, Helm, or Kafka broker-administration
  experience**. Kubernetes use does not establish any of these capabilities.
- G2: AI tooling alone does not establish model-training ownership. N5 expressly
  distinguishes model evaluation/deployment from a colleague's fine-tuning.
- G3: Some material should be abbreviated or omitted to support a readable page.
  The source does not demand that every atomic fact appear. The source supplies
  no rendered DOCX or PDF, so actual page count and readability are unverified.
