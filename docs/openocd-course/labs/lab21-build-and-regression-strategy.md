# Lab 21: Build And Regression Strategy

## Objective

Design a test matrix for OpenOCD changes.

## Safety

Builds and config-load tests are safe. Hardware tests require approval.

## Tasks

1. Identify which files changed in a hypothetical support patch.
2. Decide whether a native build is required.
3. Decide whether a Windows package build is required.
4. List config-load tests for each new Tcl file.
5. Add hardware tests only where hardware is available and recoverable.

## Checkpoints

- C backend changes require build coverage.
- Tcl-only changes still require config-load tests.
- Flash changes require destructive-test gates.

## Deliverables

- Build/test matrix
- Regression risk note

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Review why different change types need different validation. |
| 5-11 min | Students classify a hypothetical patch: docs, Tcl, C backend, packaging. |
| 11-18 min | Build a matrix of native build, package build, config-load, and hardware tests. |
| 18-23 min | Add regression checks for unrelated boards or adapters. |
| 23-27 min | Discuss what can be accepted without hardware and what cannot. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Which changes require compilation?
- Which changes require package validation?
- How do you avoid over-testing a small docs-only change?

## Exit Ticket

Choose one change type and list the minimum validation it needs.
