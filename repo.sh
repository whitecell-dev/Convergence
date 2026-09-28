#!/bin/bash
set -e
rm -rf demo
mkdir demo
cd demo
git init -q
pip install -q -e /home/so/projects/whitecell-dev/publicrepos/new/convergence

convergence init

# hand-written minimal
cat >.convergence/rules/api.user-id-format.json <<'JSON'
{"id":"api.user-id-format","version":1,"scope":{"paths":["src/api/"]},"claim":"User IDs are UUIDv7.","evidence_refs":[]}
JSON
cat >.convergence/transitions.jsonl <<'JSON'
{"event":"CANDIDATE","id":"api.user-id-format","version":1,"timestamp":"2026-05-13T00:00:00Z"}
{"event":"AUTHORIZED","id":"api.user-id-format","version":1,"approval_ref":"PR-1","timestamp":"2026-05-13T01:00:00Z"}
{"event":"ACTIVE","id":"api.user-id-format","version":1,"timestamp":"2026-05-13T01:01:00Z"}
JSON

convergence check
convergence status
echo "---"

convergence add --id ui.click-uses-data-attr --scope "src/ui/**" --claim "UI components must use data-click-id, not raw onClick html" --evidence-ref "git:HEAD:docs/click.md"
convergence authorize --id ui.click-uses-data-attr --version 1 --approval-ref "PR-2"
convergence activate --id ui.click-uses-data-attr --version 1
convergence status
echo "---"

convergence challenge --id api.user-id-format --version 1 --counterevidence-ref "git:abc123:prod/incident-42.md"
convergence status
echo "---"

convergence resolve --id api.user-id-format --version 1 --approval-ref "PR-3" --resolves "git:abc123:prod/incident-42.md"
convergence activate --id api.user-id-format --version 1
convergence status
echo "---"

# v2 handoff: CANDIDATE -> SUPERSEDE v1 -> AUTHORIZED v2 -> ACTIVE v2
# AUTHORIZED counts as holding authority, so the old version must be superseded first.
convergence add --id api.user-id-format --scope "src/api/**" --claim "User IDs are UUIDv7, encoded as lowercase string." --evidence-ref "git:HEAD:tests/test_user_ids.py"
convergence supersede --id api.user-id-format --version 1 --superseded-by 2 --approval-ref "PR-4"
convergence authorize --id api.user-id-format --version 2 --approval-ref "PR-4"
convergence activate --id api.user-id-format --version 2

convergence status
ls -R .convergence/rules
convergence check
