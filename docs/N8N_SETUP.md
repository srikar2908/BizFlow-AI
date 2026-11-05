# n8n Webhook Setup

## Status

The repository contains a backend webhook client but no n8n workflow export. The user reports that the existing n8n workflow and Google Sheets row creation are working, including a recent filename mapping correction. This repository update did not connect to the user's n8n instance or independently verify that configuration. The interface and mappings below document the backend payload contract.

## Backend configuration

Set these in the API process environment or managed secret store:

| Variable | Purpose |
| --- | --- |
| `N8N_WORKFLOW_WEBHOOK_URL` | Production/test webhook URL, private to the backend |
| `N8N_WEBHOOK_SECRET` | Shared secret sent in `X-BizFlow-Webhook-Secret` |
| `N8N_REQUEST_TIMEOUT_SECONDS` | HTTP timeout; default 30, must be greater than 0 and at most 300 seconds |

Keep these values out of frontend variables, source control and logs. Do not put real credentials in an exported workflow. Configure `0002_workflow_execution_metadata.sql` and verify the deployed schema before enabling workflow API execution.

## Required workflow behavior

1. Use an n8n Webhook trigger with `POST` and a non-guessable path. Require TLS.
2. Before processing, compare `X-BizFlow-Webhook-Secret` against an n8n credential/secret store value. Reject unauthorized requests before any side effect. Do not echo the secret.
3. Validate the JSON fields and ensure `approved_by_user` is exactly `true`; the API remains responsible for verifying the persisted owner approval.
4. Persistently deduplicate `idempotency_key` before side effects. A repeated key must return the original outcome and must not append another row or send another message. In-memory workflow state is insufficient.
5. Complete the approved action and append the workflow log row using the mappings in `WORKFLOW_EXECUTION.md`. Keep the idempotency key in the sheet and preferably a durable n8n-side dedupe store.
6. Respond synchronously with a JSON completion object only after all required actions succeed:

```json
{
  "workflow_id": "<same workflow_id from request>",
  "status": "completed",
  "execution_id": "<n8n execution identifier>",
  "result": {"recorded": true}
}
```

If n8n cannot establish whether an action completed, it must not return a misleading `completed`. The backend treats non-2xx responses, timeouts and malformed responses as unknown and will not retry automatically. The current API does not implement asynchronous `accepted` responses, polling or callbacks.

## Request fields

The API posts `workflow_id`, `workflow_type`, `document_id` (nullable), `input_payload`, `output_payload`, `approved_by_user`, and `idempotency_key`. It sends the key both as a JSON field and `Idempotency-Key` header. The secret is sent only in `X-BizFlow-Webhook-Secret`.

For the complete placeholder payload and response schema, see [WORKFLOW_EXECUTION.md](WORKFLOW_EXECUTION.md).

## Safe test procedure

1. Configure a dedicated non-production n8n instance and a test-only secret.
2. Use synthetic workflow/document payloads and a disposable test sheet.
3. Verify invalid secret and missing approval are rejected before side effects.
4. Send the same idempotency key more than once and verify only one durable side effect occurs and the same result is returned.
5. Simulate a delayed response and confirm BizFlow displays `unknown` and does not automatically resend.
6. Verify the matching workflow ID, `completed` status, result object and optional execution ID in the response.
7. Test the end-to-end path only after migration `0002` is reviewed/applied in the test Supabase project.

Do not perform real email sends during automated or initial integration tests. An email action needs its own explicit user authorization and validated recipient/draft flow.

## Production configuration and operations

- Use TLS, restrict webhook reachability where practical, rotate the shared secret, and keep the URL/secret in managed backend/n8n secret stores.
- Configure persistent n8n storage and backups according to the n8n deployment; persist dedupe records for at least the maximum retry/replay window.
- Ensure workflow error paths do not return a false success response. Preserve an operator-visible execution record for reconciliation.
- Confirm column mapping, retention/access permissions, dedupe key storage, and recovery behavior in the user's n8n instance before production changes. This repository does not provide an export of that workflow.
- Reconcile stale `running` and `unknown` workflow rows against n8n execution history before any manual retry.

## Common failure interpretation

| Backend result | Meaning | Action |
| --- | --- | --- |
| `failed`, `definite_failure` | No webhook connection was established or local prerequisite failed | Correct configuration and explicitly retry; same stored key is reused |
| `unknown` | Request may have reached n8n, or response could not be validated | Check n8n and all side effects; do not retry until reconciled |
| `running` for an unusually long time | Process may have stopped after claiming or while n8n ran | Reconcile manually; the API has no lease/reaper |
| Database schema compatibility error | Required workflow metadata columns are absent/incompatible | Review migration history/schema; apply reviewed `0002` before deployment |

An importable workflow JSON is not included because the user's existing Sheets flow, credentials, n8n version and dedupe implementation cannot be exported or verified from this repository. No credentials should be embedded in an exported workflow.
