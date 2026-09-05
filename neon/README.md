# Neon for anticaptrad

Neon is 1:1 with the GitHub org (`org-anticaptrad` planned). `neon/anticaptrad-prod/terraform/` declares the
project, branches, roles and the two databases (`canonical`, `auth`) with the Neon Terraform provider; the
`neon-preview.yml` workflow creates a `preview/pr-<n>` branch per PR and runs `dpm plan` only (apply is human-gated).
Neon never ingests schema from git — migrations come from `act-orm-core` via dpm.
