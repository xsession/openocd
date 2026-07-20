# Documentation Style Guide

This document defines the current documentation standard for the repository.

## Goals

- explain subsystem purpose before low-level details
- make constraints and boundaries explicit
- keep machine-readable artifacts and prose aligned
- document what is implemented, what is inferred, and what remains unresolved

## Preferred Structure

For technical reference documents, prefer this order:

1. purpose or scope
2. architecture or topology
3. concrete interfaces, workflows, or data shapes
4. operational limits and current gaps
5. links to adjacent documents or artifacts

## Diagrams

- Use Mermaid for architecture, topology, and flow diagrams where it materially improves comprehension.
- Keep diagrams focused on one concept at a time.

## Clean-room Language

- Do not describe the Zephyr or recovery work as restored source code.
- Prefer terms such as `observed`, `clean-room`, `compatibility`, `recovery project`, and `behavioral reconstruction`.
- Be explicit when a conclusion is an inference rather than a confirmed fact.

## Operational Language

- Use concrete commands where a workflow is executable.
- Call out unresolved blockers directly.
- Keep references to physical hardware constraints visible in relevant docs.