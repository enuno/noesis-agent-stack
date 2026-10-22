# Container image and chart pinning

Use this when an Ansible/Helm workload must track the newest stable upstream
release without deploying a mutable tag.

## Procedure

1. Identify the authoritative source release feed (normally the upstream
   GitHub `releases/latest` endpoint or signed release page) and record the
   release tag and publication time.
2. Enumerate the container registry's full tag set. Docker Registry HTTP API
   tag responses may be capped (often 100 entries); request pages with `n` and
   continue with `last=<last-tag>` until the response is empty or the last tag
   stops changing. Never sort only the first page and call its maximum current.
3. Parse versioned stable tags semantically. Exclude `main`, `latest`,
   architecture suffixes, and prerelease labels unless the operator explicitly
   selected them. Cross-check the resulting newest stable tag with the source
   release feed; stop on disagreement rather than choosing one silently.
4. Fetch the selected tag's manifest using an OCI-index / Docker-manifest-list
   Accept header. Record the `Docker-Content-Digest` of the multi-architecture
   index and the child digests for every supported platform.
5. Put the immutable index digest in the intended inventory/example values.
   Set the repository-owned chart's `appVersion` to the verified release and
   keep the chart's own semantic version separate; an application release does
   not automatically imply an official Helm chart release.
6. Render and assert all pin surfaces agree: Chart.yaml appVersion, role
   defaults, example inventory, rendered Deployment image, provenance table,
   and tests. Reject `latest` and `main` in production examples.
7. Preserve query URLs/commands, release tag, publication time, index digest,
   and architecture matrix in the runbook or provenance artifact. Re-check at
   implementation time when the operator asks for the current version; do not
   reuse an old remembered pin.

## Chart selection

Verify chart availability from the application's official documentation and
source tree. If upstream explicitly ships Kubernetes manifests but no Helm
chart, label any repository-owned chart as maintained by this repository, not
as an official or upstream chart. Define “current chart” as the repository
chart version whose `appVersion`, immutable image digest, and copied manifest
semantics match the newest verified application release.