---
id: "proj-keyraa"
kind: "projects"
title: "Keyraa"
org: "Majara"
period: "2026"
tools: ["python", "fastapi", "sqlalchemy", "postgres", "redis", "celery", "docker", "rest-apis", "pytest"]
summary: "Keyraa, a corporate hotel booking platform: a FastAPI backend that turns bulk employee trip requests into booked hotels — Amadeus search, bulk booking through Celery workers, and confirmation emails. I built the core flows solo: multi-tenant, idempotent, with retry and backoff around a rate-limited external API. Shelved before launch when industry regulations changed."
---

## What the work actually involved

Keyraa is a corporate hotel booking platform, and what I built was its backend. It began as a proof of concept for a B2B corporate housing product designed to solve a largely operational problem: companies often need to arrange accommodation for groups of employees, but the process can end up being handled manually by HR teams, project managers, or relocation staff. They may need to find suitable properties, negotiate with multiple suppliers, coordinate individual employee stays, track availability and costs, handle changes in headcount, and reconcile multiple bookings and invoices. As the number of employees grows, this becomes a time-consuming administrative job rather than something the company should have to manage manually.

The product was designed to centralize that process. Instead of a project manager coordinating dozens of accommodation arrangements separately, a company could manage its housing requirements through one platform, with bulk booking workflows, centralized booking information, and a single view of occupancy and accommodation costs. The broader business model was aimed at organizations such as consulting and contracting companies housing project teams, large HR departments managing relocation and housing, and recruitment companies arranging accommodation for incoming employees.

The backend I built was responsible for turning that product workflow into an actual system. I worked independently on the core FastAPI services, including REST APIs for hotel search, booking workflows, bulk operations, and related application logic. PostgreSQL stored tenant, traveler, and booking state, with SQLAlchemy providing the database layer and Alembic handling schema migrations.

A major part of the problem was connecting the platform to Amadeus for hotel availability and booking. The purpose of the integration was not simply to expose another API to users; it was to automate work that would otherwise require a person to search for and coordinate accommodation. That meant the integration had to be reliable enough to operate as part of a larger workflow.

Amadeus introduced constraints that shaped the architecture. Requests could be slow, rate-limited, or fail temporarily, and the application couldn't control those conditions. I therefore used Celery workers backed by Redis to process search and booking operations asynchronously where appropriate, keeping long-running external API work out of the main request/response cycle. The worker layer also provided a place to implement retries and exponential backoff rather than immediately failing a workflow when an external service experienced a transient problem.

Booking required an additional reliability guarantee: **retrying an operation could never accidentally create a duplicate booking**. For example, a request might time out after the external provider had actually processed it. Retrying blindly could then result in two reservations for the same traveler. I treated idempotency as a core requirement, using idempotency keys and designing the application-side write path so that repeating the same operation would not create duplicate bookings or duplicate state.

The system was also designed for multiple corporate customers sharing the same platform. Each company needed its travelers, requests, and bookings isolated from every other company, so tenant context was incorporated into the application and used to scope the relevant data. This allowed the platform to support a B2B SaaS-style model without requiring a separate deployment for every customer.

Bulk operations were particularly important because they mapped directly to the underlying business pain. The goal wasn't simply to make it easier to book one hotel room. It was to reduce the amount of repetitive coordination required when a company needed accommodation for an entire project team. That meant the system had to account for multiple operations happening together, including partial failures, retries, changes in employee requirements, and the possibility that some bookings succeeded while others did not.

The workflow could also trigger confirmation emails once bookings cleared the relevant process, keeping communication downstream from the booking operation rather than making email delivery part of the critical transaction.

The project ultimately did not reach production. It was shelved after changes in industry regulations affected the booking model the product was built around. That was a business and regulatory change rather than a technical failure.

What made the project valuable from an engineering perspective was the connection between the **business problem and the architecture**. The system wasn't complex simply because it used FastAPI, Celery, Redis, or PostgreSQL. Each major technical decision existed because of a real constraint: bulk workflows addressed the repetitive work handled by HR and project managers; asynchronous processing addressed slow and rate-limited external APIs; idempotency protected against duplicate bookings; and tenant isolation supported multiple corporate customers on the same platform.

The project gave me experience going beyond implementing isolated API endpoints and instead thinking about how a real business workflow should behave when it encounters unreliable dependencies, multiple users, changing requirements, and failure.
