# Anticaptrad deployment manifests

Apply the YouTube control-plane resources in this order:

1. `act-api-server.externalsecret.yaml`
2. `act-api-server.yaml`

The ExternalSecret must become Ready before the Deployment can create pods because the generated `act-api-server-secrets` reference is intentionally non-optional.

See `../docs/youtube-control-plane.md` for provisioning, verification, rotation, and rollback procedures.
