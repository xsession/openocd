# Lab 19: Vendor Fork Audit

## Objective

Audit an external source without copying it wholesale.

## Safety

Do not import source files in this lab. Classify first.

## Tasks

1. Read `docs/development/openocd-vendor-fork-audit.md`.
2. Choose one ecosystem from the audit.
3. Classify candidate files as config-only, backend batch, duplicate,
   obsolete, blocked, or delegated.
4. Record source URL, commit/tag, license, and expected validation commands.
5. Reject at least one unsafe Tcl-only import and explain why.

## Checkpoints

- You can explain why target scripts that reference missing C backends are not
  useful imports.
- You can distinguish an OpenOCD fork from an external programmer tool.

## Deliverables

- Audit triage table
- Import recommendation

## 30-Minute Session Plan

| Time | Activity |
| ---: | --- |
| 0-5 min | Review the rule: audit first, import later. |
| 5-10 min | Students choose one ecosystem and record source/provenance. |
| 10-18 min | Classify candidate files into config-only, backend, duplicate, blocked, or deferred. |
| 18-23 min | Identify one unsafe import and explain the missing dependency. |
| 23-27 min | Write a recommendation with validation commands. |
| 27-30 min | Exit ticket. |

## Instructor Prompts

- Why are whole-fork imports risky?
- What makes a Tcl file unusable without a C backend?
- How does license/provenance affect import decisions?

## Exit Ticket

Name one file you would import and one file you would defer, with reasons.
