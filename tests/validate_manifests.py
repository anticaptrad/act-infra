#!/usr/bin/env python3
"""Validate security and deployment invariants for Anticaptrad manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENTS = ROOT / "deployments"
EXPECTED_GAS_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbwXNUnFogkqg_aeobBMLCas21CHJ8eIR8W1AnmEBNx7pPgfio8eARW5J4A-lu_V5gY/exec"
)


def load_documents(path: Path) -> list[dict[str, Any]]:
    documents = []
    for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
        if document is not None:
            if not isinstance(document, dict):
                raise AssertionError(f"{path}: each YAML document must be a mapping")
            documents.append(document)
    return documents


def find_kind(documents: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    for document in documents:
        if document.get("kind") == kind and document.get("metadata", {}).get("name") == name:
            return document
    raise AssertionError(f"missing {kind}/{name}")


def main() -> None:
    all_documents: list[dict[str, Any]] = []
    for path in sorted(DEPLOYMENTS.glob("*.yaml")):
        all_documents.extend(load_documents(path))

    assert all(document.get("kind") != "Secret" for document in all_documents), (
        "plaintext Kubernetes Secret manifests are forbidden"
    )

    api_documents = load_documents(DEPLOYMENTS / "act-api-server.yaml")
    config_map = find_kind(api_documents, "ConfigMap", "act-api-server-config")
    deployment = find_kind(api_documents, "Deployment", "act-api-server")

    config = config_map["data"]
    assert config["YOUTUBE_GAS_URL"] == EXPECTED_GAS_URL
    assert config["YOUTUBE_EXPECTED_CHANNEL_HANDLE"] == "@anticaptrad"
    assert config["YOUTUBE_ALLOW_PUBLIC_ACTIONS"] == "false"
    assert config["YOUTUBE_GAS_TIMEOUT_SECS"] == "30"
    assert config["YOUTUBE_GAS_MAX_RESPONSE_BYTES"] == "4194304"
    assert "ADMIN_API_KEY" not in config
    assert "YOUTUBE_GAS_API_KEY" not in config

    pod_template = deployment["spec"]["template"]
    annotations = pod_template["metadata"].get("annotations", {})
    assert annotations.get("secret.reloader.stakater.com/reload") == "act-api-server-secrets"

    container = pod_template["spec"]["containers"][0]
    assert container["image"] == "anticaptrad/act-api-server:0.2.0"
    assert not container["image"].endswith(":latest")
    env_from = container["envFrom"]
    secret_refs = [item["secretRef"] for item in env_from if "secretRef" in item]
    assert secret_refs == [{"name": "act-api-server-secrets"}], (
        "act-api-server must require exactly one non-optional generated Secret"
    )
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert "ALL" in container["securityContext"]["capabilities"]["drop"]

    secret_documents = load_documents(DEPLOYMENTS / "act-api-server.externalsecret.yaml")
    external_secret = find_kind(secret_documents, "ExternalSecret", "act-api-server-secrets")
    assert external_secret["apiVersion"] == "external-secrets.io/v1"
    spec = external_secret["spec"]
    assert spec["secretStoreRef"] == {
        "kind": "ClusterSecretStore",
        "name": "dd-fiducia-kv",
    }
    assert spec["target"] == {
        "name": "act-api-server-secrets",
        "creationPolicy": "Owner",
        "deletionPolicy": "Retain",
    }
    projected = {
        entry["secretKey"]: entry["remoteRef"]["key"]
        for entry in spec["data"]
    }
    assert projected == {
        "ADMIN_API_KEY": "k8s/default/act-api-server/ADMIN_API_KEY",
        "YOUTUBE_GAS_API_KEY": "k8s/default/act-api-server/YOUTUBE_GAS_API_KEY",
    }

    # Compose signatures so the validator does not flag its own source text.
    forbidden_signatures = {
        "Fiducia live credential": "fdc" + "_live_",
        "Google API key": "AI" + "za",
    }
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, signature in forbidden_signatures.items():
                assert signature not in text, f"possible {label} in {path}"

    print(f"validated {len(all_documents)} Kubernetes documents")
    print("YouTube control-plane deployment invariants verified")


if __name__ == "__main__":
    main()
