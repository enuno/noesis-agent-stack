# Tailscale official Helm chart (the operator)

The ONLY chart Tailscale publishes is the Kubernetes operator:

- Repo: `https://pkgs.tailscale.com/helmcharts` (chart `tailscale-operator`,
  e.g. 1.104.1). `https://tailscale.github.io/tailscale` also proxies it.
- Source: `github.com/tailscale/tailscale`, path
  `cmd/k8s-operator/deploy/chart`.
- Vendored in-repo at `charts/vendor/tailscale-operator` with a VENDOR.md
  recording version + upstream sha256 digest. Verify the index digest after
  every download, `helm lint` after every vendor update.

## Auth model (hard constraints)

- Deployment authentication is **OAuth-client-only**: values
  `oauth.clientId`/`oauth.clientSecret` rendered into a Secret named
  `<fullname>-oauth` (keys `client_id`/`client_secret`), or
  `oauthSecretVolume` pointing at a pre-created Secret with the same keys.
  There is **no authKey deployment path** — an auth-key-only environment
  cannot install this chart.
- Client secrets are shown **once** at OAuth-client creation in the Tailscale
  admin console; a lost secret means minting a new OAuth client. Store both
  values in the encrypted vault, never in helm values (staged values are
  world-readable on the target by design).
- Admin-console prerequisites: OAuth client with scopes `devices:core` +
  `devices:write` (suggested tags `tag:k8s-operator`); ACL `tagOwners`
  letting `tag:k8s-operator` own `tag:k8s`:
  ```json
  {"tagOwners": {"tag:k8s-operator": []},
   "acls": [{"action": "accept", "src": ["tag:k8s-operator"], "dst": ["*:*"]}]}
  ```

## Exposure model

- The operator watches **standard `networking.k8s.io/v1` Ingress** objects
  with `ingressClassName: tailscale` (chart installs that IngressClass). It
  does NOT define an `ingresses.tailscale.com` CRD — don't assert one.
- Hostname: the operator serves the Ingress at a bare hostname (e.g.
  `noesis-praxis`) under the tailnet domain with operator-provisioned TLS;
  set `rules[].host` explicitly to keep the MagicDNS name deterministic.
  Tailnet-only by construction; Funnel is never enabled.
- The proxy pod lands in the operator namespace (default `tailscale`). The
  backend sees the **proxy pod IP** (pod-to-pod, no node SNAT) — re-derive
  trusted proxy CIDRs after any Serve→Ingress pivot.
- One identity per tailnet name: remove a host-level tailscaled (logout →
  disable/stop → purge) before an in-cluster proxy claims the same MagicDNS
  name, or enrollment conflicts.
