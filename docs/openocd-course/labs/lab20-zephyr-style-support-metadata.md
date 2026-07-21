# Lab 20: Zephyr-Style Support Metadata

## Objective

Create support metadata for a board, SoC, programmer, or module.

## Safety

Metadata should describe status honestly. Do not mark untested hardware as
fully supported.

## Tasks

1. Read `docs/development/zephyr-style-support-organization.md`.
2. Inspect entries under `support/boards`, `support/soc`,
   `support/programmers`, and `support/modules`.
3. Draft one new metadata entry for a chosen support lane.
4. Include runtime paths, docs, status, validation, and known gates.
5. Check that all referenced files exist.

## Checkpoints

- Metadata does not replace OpenOCD runtime paths.
- Status words such as `integrated`, `delegated`, `deferred`, and `blocked`
  are used consistently.

## Deliverables

- One metadata entry
- Path-reference validation notes

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Explain the Zephyr-style metadata layer and why runtime paths stay unchanged. |
| 5-11 min | Students inspect one board, SoC, programmer, and module entry. |
| 11-18 min | Draft a metadata entry for a chosen support lane. |
| 18-23 min | Add status, docs, validation, and known gates. |
| 23-27 min | Check referenced paths and revise inaccurate status. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why does metadata not replace `tcl/` files?
- What is the difference between `delegated` and `integrated`?
- What status should hardware-gated support use?

## Exit Ticket

Submit one metadata field that points to runtime code and one that records
validation status.
