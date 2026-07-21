# Lab 22: Backend Batch Triage

## Objective

Plan a full backend integration batch without breaking unrelated targets.

## Safety

No code import is required. This is a planning and review lab.

## Tasks

1. Read `docs/development/vendor-audit-phase10-backend-hardware-queue.md`.
2. Choose one deferred backend family.
3. Identify required C files, Tcl files, build registrations, and tests.
4. Write acceptance gates for build, config-load, hardware, and documentation.
5. Explain why the batch cannot be split into Tcl-only imports.

## Checkpoints

- You can name the missing backend dependency.
- You can propose a minimal but complete first batch.

## Deliverables

- Backend gate report
- Proposed Phase 11 implementation plan

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Introduce backend batches as coupled C/Tcl/test/documentation work. |
| 5-10 min | Students choose one deferred backend family from Phase 10. |
| 10-18 min | Identify required C files, Tcl files, build registrations, and tests. |
| 18-23 min | Write acceptance gates and no-go conditions. |
| 23-27 min | Compare plans and remove unsafe Tcl-only shortcuts. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- What is the smallest complete backend batch?
- What makes the batch risky for unrelated targets?
- What hardware or simulator evidence is enough?

## Exit Ticket

State the missing backend dependency that blocks your chosen family.
