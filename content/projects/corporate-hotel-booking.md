---
id: "proj-booking-backend"
kind: "projects"
title: "Corporate hotel booking backend"
org: "Majara"
period: "2026"
tools: ["python", "fastapi", "sqlalchemy", "postgres", "redis", "celery", "docker", "rest-apis", "pytest"]
summary: "A FastAPI service that turns bulk employee trip requests into booked hotels — Amadeus search, bulk booking through Celery workers, and confirmation emails. I built the core flows solo: multi-tenant, idempotent, with retry and backoff around a rate-limited external API. Shelved before launch when industry regulations changed."
---

## What the work actually involved

This was a FastAPI backend for a corporate travel workflow: a company
submits a bulk trip request for a group of employees, and the system
has to turn that into actual booked hotel rooms. I built the core
flows solo.

The shape of the problem was mostly about talking to an external,
rate-limited API (Amadeus) reliably at scale. Search and booking calls
ran through Celery workers rather than inline in the request/response
cycle, both to keep the API responsive and to get retry and
exponential backoff around calls that would otherwise fail under
normal Amadeus rate limits. Idempotency was a hard requirement —
retrying a failed booking call must never double-book a room or double-
charge a client, so every booking operation carried an idempotency key
and the write path was built to be safely repeatable.

The service was multi-tenant from the start: each corporate client's
requests, bookings, and traveler data needed to stay isolated from
every other client sharing the same deployment. Postgres (via
SQLAlchemy) held the booking and tenant state, Redis backed the Celery
queue, and confirmation emails went out once a booking cleared.

The project was shelved before launch when industry regulations
changed in a way that affected the booking model it was built around —
not a technical failure, but the kind of external shift that can kill
a project regardless of how solid the implementation is.
