# Anticaptrad YouTube control-plane deployment

This deployment connects `anticaptrad/act-api-server.rs` to the Anticaptrad Google Apps Script web app while preserving two independent authentication boundaries:

1. `ADMIN_API_KEY` authenticates callers to the Rust administrative API.
2. `YOUTUBE_GAS_API_KEY` authenticates the Rust service to the Apps Script HTTP API.

Never reuse either value for the other boundary. Neither value belongs in Git, Linear, container images, command-line arguments, or logs.

## Fiducia keys

Provision these values through an approved Fiducia writer under the cluster application keyspace:

- `k8s/default/act-api-server/ADMIN_API_KEY`
- `k8s/default/act-api-server/YOUTUBE_GAS_API_KEY`

Each value must contain at least 32 characters. Generate them independently with a cryptographically secure generator. Enter them through protected input, with shell tracing disabled, and clear temporary environment variables after use.

`deployments/act-api-server.externalsecret.yaml` projects those two values through `ClusterSecretStore/dd-fiducia-kv` into `Secret/act-api-server-secrets`. The Deployment requires that Secret; it is not optional. Stakater Reloader rolls pods after External Secrets Operator rotates the generated Secret.

## Non-secret configuration

`deployments/act-api-server.yaml` pins:

- the deployed `/macros/s/.../exec` Apps Script URL;
- `YOUTUBE_EXPECTED_CHANNEL_HANDLE=@anticaptrad`;
- bounded request time and response size;
- `YOUTUBE_ALLOW_PUBLIC_ACTIONS=false`;
- the versioned `anticaptrad/act-api-server:0.2.0` image.

Do not enable public or unlisted actions until DEN-402's private upload rehearsal has confirmed idempotency, Drive backup, audit correlation, and channel identity.

## Pre-rollout checks

1. Confirm `ExternalSecret/act-api-server-secrets` reports `Ready=True`.
2. Confirm the generated Secret contains exactly `ADMIN_API_KEY` and `YOUTUBE_GAS_API_KEY`.
3. Confirm the two values differ and each meets the minimum length.
4. Confirm the Apps Script deployment is using the hardened `http-api` profile.
5. Confirm the published container image digest corresponds to the reviewed Rust PR.

## Runtime verification

Keep credentials out of shell history. Load the Rust administrative key through protected input and use the internal service URL:

```bash
set +x
read -r -s -p 'Rust admin key: ' ADMIN_API_KEY; printf '\n'

curl --fail-with-body --silent --show-error \
  http://act-api-server/health | jq .

curl --fail-with-body --silent --show-error \
  http://act-api-server/ready | jq -e '
    .ready == true and
    .youtube_configured == true and
    .admin_auth_configured == true
  '

curl --fail-with-body --silent --show-error \
  http://act-api-server/v1/youtube/health | jq -e '
    .ok == true and
    .data.app == "Anticaptrad YouTube Control Center"
  '

curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer ${ADMIN_API_KEY}" \
  http://act-api-server/v1/youtube/status | jq -e '
    .ok == true and
    .data.expectedChannelHandle == "@anticaptrad" and
    .data.publicActionsEnabled == false and
    .data.appsScriptApiKeyExposed == false
  '

unset ADMIN_API_KEY
```

Before any upload, perform a keyed read-only `channel` action and verify the returned channel identity corresponds to `@anticaptrad`.

## Rotation

1. Write the replacement value to the same Fiducia key.
2. Wait for the ExternalSecret refresh and Reloader rollout.
3. Verify `/ready`, `/v1/youtube/health`, and authenticated `/v1/youtube/status`.
4. Revoke the previous credential at its owning boundary when applicable.

Rotate one boundary at a time. A failed GAS-key rotation must not require changing the Rust administrative key, and vice versa.

## Rollback

- Keep `YOUTUBE_ALLOW_PUBLIC_ACTIONS=false` throughout rollback.
- Roll back to the previous reviewed image digest, not an unpinned `latest` tag.
- With `deletionPolicy: Retain`, the last synchronized Kubernetes Secret remains if Fiducia retrieval is temporarily unavailable; investigate the ExternalSecret condition before changing credentials.
- If the GAS integration is unhealthy, stop YouTube mutations and retain private jobs for reconciliation. Do not bypass authentication or publish directly through browser automation.
