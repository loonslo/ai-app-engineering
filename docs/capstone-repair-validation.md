# Capstone and course repair validation

Validation date: 2026-11-02  
Environment: Windows 10 x64, Python 3.14, isolated environment `.tmp/repair-venv` built from `requirements-dev.txt`. No model credentials or external services were used.

## Changes covered

- Pinned the root, course, and development direct dependencies; added `requirements-capstone.txt` to separate the production image's runtime dependencies from development and course frameworks. The Dockerfile now installs the capstone set and includes only the public sample corpus under `/var/lib/capstone/docs`.
- Moved the default sample knowledge document to `capstone/data/docs/`; the default knowledge-base directory is `CAPSTONE_DATA_DIR/docs`. Incremented the source and Chroma collection versions so old indexes containing engineering documentation are not reused. Tests assert that ADR, portfolio, and runbook material is excluded from the default corpus.
- Unified evaluation refusal classification with the knowledge-base refusal rule. Tests distinguish canonical refusals from prefatory factual answers that merely mention missing information.
- Fixed the fake load-test fixture to copy the public sample corpus into its isolated data directory. The first smoke attempt before this correction failed readiness because its temporary corpus was empty; a subsequent attempt exposed and corrected a missing `subprocess` import introduced in the fixture edit.
- Expanded offline CI to check both course maps, Markdown links, and Ruff; aligned course runtime descriptions and current Pydantic AI version/advisory language. Replaced the stale follow-up index and corrected task, production-readiness, and project-status records.

## Validation performed

All commands below ran in the isolated Python 3.14 environment unless otherwise stated.

| Check | Result |
|---|---|
| `pip install --dry-run --ignore-installed -r requirements-capstone.txt` | Passed; production direct requirements resolved. |
| `pip install --dry-run --ignore-installed -r requirements-dev.txt` | Passed; development requirements resolved. |
| `pip install --dry-run --ignore-installed -r requirements-course.txt` | Passed; course requirements resolved with direct pins. |
| `python -m pip check` | Passed: no broken requirements. |
| `python -m pytest capstone/test_production.py -q` | 47 passed; one Chroma deprecation warning. |
| `python -m pytest tools chapters/test_new_lessons.py chapters/test_v3_lessons.py -q` | 108 passed; one Chroma deprecation warning. Windows child processes use UTF-8 mode. |
| `python -m pytest -c flagship-project/m1-rag-mvp/step1/pyproject.toml flagship-project/m1-rag-mvp/step1/tests -q` | 9 passed; one upstream `langchain-community` sunset deprecation warning. The flagship snapshot itself was not modified. |
| `python -m capstone.project_baseline --json` | Exit 0; all 15 baseline checks passed. |
| `python -m capstone.milestones --strict-evidence` | Exit 0; evidence-file presence audit passed. This is not a runtime acceptance test. |
| `python tools/apply_v2_map.py --check` / `python tools/apply_v3_map.py --check` | Passed; 111 and 119 entries unchanged. |
| `python tools/check_course_links.py` | Passed; 488 Markdown files, 0 broken links. |
| `ruff check --target-version py311 capstone tools chapters/test_v3_lessons.py` | Passed. |
| `SLO_P95_MS=2000 SLO_ERROR_PCT=1 SLO_MIN_RPS=1 python -m capstone.load_test --fake --users 2 --spawn-rate 2 --time 5s --upstream-ms 50` | Passed: 32 requests, 0 failures, 7.057 RPS, chat p95 69 ms; local fake SLO PASS. The command wrote `reports/loadtest_20261102_165912.json`. This is a local fake smoke, not production capacity evidence. |

`docker --version` was unavailable (`docker` command not found), so no image build was run. CI was not run remotely.

## Remaining blockers and acceptance status

- L2.12 remains **below threshold**: the recorded Hybrid refusal accuracy is 71.88% against a 90% requirement (`docs/gate-v3-2-validation.md`). This repair did not alter the evaluation threshold or claim a pass. It needs a representative evaluation and real reranker/model evidence.
- Production remains **NO-GO** for real enterprise data. External identity provider and moderation, staging, target-environment capacity, OTLP backend, and recovery/RPO/RTO drills are not evidenced. The local fake load test does not satisfy those requirements.
- Real learning and teaching outcomes remain unverified. Passing course gates do not establish that a learner completed them independently.
- 用户决定暂时保留 `面试题/` 的 98 道转载题目及答案；复用许可仍未确认，不得公开分发，公开前需核实许可或移除复制内容。
- No real model/API call, external deployment, Docker build, remote CI, or third-party license determination was performed.
