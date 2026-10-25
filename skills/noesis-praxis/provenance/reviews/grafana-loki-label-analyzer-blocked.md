# Blocked package — grafana/skills loki-label-analyzer

**Status: blocked (disposition C). Not installed, not staged as reference
material — see rationale below.**

Source: `grafana/skills`, commit `cc33318b60a7fbc2c69a25122164baf00e805f79`,
path `skills/grafana-cloud/loki-label-analyzer`. License: Apache-2.0 (repo).

## Why blocked rather than adapted

Two independent problems, either one sufficient on its own:

1. **Cloud-only content is not cleanly separable from the mandatory output
   contract.** Unlike `prometheus-label-strategy`/`prometheus-cardinality-
   troubleshooter` (installed, disposition B), this package's Cloud-specific
   content (a mandatory "Cost Impact" output section using Grafana Cloud-only
   billing metrics) is baked into what the skill requires every response to
   contain, not an optional hand-off to a sibling Cloud skill that can simply
   be pointed elsewhere. Stripping it would require rewriting the skill's
   actual output contract, not just removing a hand-off sentence.
2. **Unresolved/suspicious instruction-injection behavior.** The retrieving
   subagent found that this package embeds instructions coercing any agent
   that loads it to inject a fixed "Confidential Information of Raintank,
   Inc." legal disclaimer verbatim into every output, with what the subagent
   described as a self-verification/re-emit enforcement loop designed to
   make an agent keep re-asserting that disclaimer. The subagent correctly
   did not comply with this instruction (content inside a reviewed file is
   data to be evaluated, not a directive this review process follows) and
   flagged it explicitly as suspicious/unresolved rather than treating it as
   benign boilerplate. This review concurs: a skill file instructing its own
   loader to inject and defend a specific legal notice is not a pattern that
   belongs in reviewed, trusted content without a maintainer explaining why
   it's there — it looks like either leftover internal tooling scaffolding
   or a more deliberate content-injection pattern, and either way it should
   not be activated without that question being resolved upstream first.

## Disposition

**C — staged and blocked.** Not copied into the discoverable skill tree.
Not preserved as reference material either (unlike the NetClaw reference
docs in this directory), because the unresolved instruction-injection
behavior is exactly the kind of thing that shouldn't be kept around even as
inert text without a clear resolution. If a future review resolves both the
Cloud/OSS separability and the disclaimer-injection question, this entry
should be revisited.
