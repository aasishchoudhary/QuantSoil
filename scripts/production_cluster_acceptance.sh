#!/usr/bin/env bash
set -euo pipefail

# Target-cluster acceptance smoke test. This script produces evidence; it does
# not deploy, mutate, or claim readiness for an unverified cluster.
namespace="${NAMESPACE:-gods-eye}"
kubectl get namespace "$namespace" -o jsonpath='{.metadata.labels.pod-security.kubernetes.io/enforce}{"\n"}'
[[ "$(kubectl get namespace "$namespace" -o jsonpath='{.metadata.labels.pod-security.kubernetes.io/enforce}')" == "restricted" ]]

kubectl apply --dry-run=server -f k8s/namespace.yaml >/dev/null
kubectl apply --dry-run=server -f k8s/network-policy.yaml >/dev/null
kubectl apply --dry-run=server -f k8s/runtime.yaml >/dev/null
kubectl apply --dry-run=server -f k8s/web.yaml >/dev/null
kubectl apply --dry-run=server -f k8s/pdb.yaml >/dev/null

kubectl -n "$namespace" rollout status deployment/world-intelligence-runtime --timeout="${ROLLOUT_TIMEOUT:-180s}"
kubectl -n "$namespace" rollout status deployment/gods-eye-web --timeout="${ROLLOUT_TIMEOUT:-180s}"

kubectl -n "$namespace" get networkpolicy -o wide
kubectl -n "$namespace" get poddisruptionbudget -o wide
kubectl -n "$namespace" get pods -o wide

echo "PASS: target cluster manifest admission and rollout checks"
echo "DEFERRED: external TLS/OIDC gateway, backup/PITR, S3 retention/workload identity, load testing, outage drills"
