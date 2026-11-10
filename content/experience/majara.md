---
id: "exp-majara"
kind: "experience"
title: "Product Engineer Intern"
org: "Majara — Riyadh, hybrid"
period: "Dec 2025 — Present"
tools: ["python", "javascript", "django", "react", "typescript", "playwright", "rest-apis", "full-stack", "systems-analysis", "agile", "sdlc", "b2b"]
summary: "Product engineer intern on Wakil, Majara's property management platform, working in a multi-person engineering team. I took Customer 360 end to end, from product definition to shipped code, and work across the full stack in Django REST Framework and React with TypeScript."
title_ar: "متدرب مهندس منتجات"
org_ar: "مجرة — الرياض، عمل هجين"
period_ar: "ديسمبر 2025 — الآن"
summary_ar: "متدرب مهندس منتجات على منصة وكيل لإدارة العقارات التابعة لمجرة، ضمن فريق هندسي من عدة مهندسين. تولّيت ميزة Customer 360 من تعريف المنتج حتى الشيفرة المنشورة، وأعمل على المنصة بكامل مكوّناتها (Full-stack) باستخدام Django REST Framework وReact مع TypeScript."
---

## Majara and Wakil

Majara is a Riyadh startup builder, a venture studio. I joined as a Product Engineer Intern, working hybrid out of Riyadh. My work there is on Wakil, a property management and real-estate platform in Majara's portfolio, turning problems into products and shipping them to production. Wakil is multi-tenant SaaS: a CRM with contacts and deals, properties, projects, leases, automations, a website builder, and an Arabic and English interface.

I work on Wakil as part of a multi-person engineering team, with code review on every PR and work tracked in sprints. The stack I worked in on Wakil is a Django REST Framework and PostgreSQL backend, a React and TypeScript frontend, Celery for the automations engine, Playwright for end-to-end tests, and an Arabic and English interface that switches between right-to-left and left-to-right layouts.

## Customer 360: product definition

At Majara I owned the product side of Customer 360 on Wakil: bringing everything about a client into one place, to match leading CRMs. I authored the product brief, 10 user journeys, benchmarking, 24 user stories with acceptance criteria, and the success metric.

The definition work covered framing the problem and the users, mapping the current journey with click counts, and a market scan of what three CRMs put on the contact card. I then defined the primary user, the scenarios, the v1 scope and the non-goals. I took a one-page brief to a supervisor checkpoint, then wrote a to-be journey and wireframe and a rollout plan.

## Customer 360: building it

I then built and shipped Customer 360 on Wakil end to end, in Django REST and React with TypeScript, adding five sections to the contact dialog. In key journeys it cut clicks by 72% on average, reduced typing steps to zero, and removed jumping between pages.

Two of the merged pieces I can describe in detail:

- **A Deals tab on the contact.** It has filter chips (All, Open, Won, Lost, Other closed). A deal opens inside the contact window with a Contact > Deal breadcrumb that works with the browser's Back and Forward buttons and survives a reload. A user can add a deal from the contact with the customer pre-filled and locked, and the tab updates live when a deal changes stage. It has loading, error, empty and no-permission states.
- **A Properties & projects tab.** It switches between the contact's properties and projects. A user can link or unlink a property's owner, projects are view-only, and property and project dialogs have breadcrumbs.

Both were specified and mocked up before any code, then QA'd manually in Arabic and English, in light and dark mode.

## The Tasks module

On Wakil I redesigned and rebuilt the Tasks module. I authored the product brief, user journeys, benchmarking, acceptance criteria and success metrics, then fixed 10 gaps and added 17 features, including subtasks, recurring tasks and a calendar view. Tasks now link across five modules instead of one.

## Bug fixing, QA and security

I helped the engineering team on Wakil clear its bug backlog: I fixed 13 bugs, including 2 security flaws that exposed data between companies, and designed a workflow that stress-tests bug reports and ranks them by severity. The security fixes were multi-tenant data-isolation bugs, where data could leak between companies, in the automations engine.

Other fixes were smaller: API input validation that returns a clear 400 instead of a 500 or silently wiping data, Arabic UI text, form error states, and keyboard accessibility in the sidebar.

I also ran a QA pass on the automations engine, which runs rules in a When > If > Then shape. I wrote a test plan, then did fault injection with real Celery workers, concurrency and load tests, Playwright end-to-end specs, and exploratory testing, and reported the findings ranked by severity.

The severity workflow became a Claude Code skill called verify-severity. It checks a bug claim against the code, reproduces it, and re-rates the severity with evidence.

## AI tooling for the engineering team

I wrote the rule set that every engineer's AI assistant follows to write PR descriptions, which made them 40% shorter and standardized. It shipped as a shared Claude Code skill plus a GitHub PR template.

I also built an AI skill that turns any module of the codebase into a visual walkthrough for onboarding. Two new interns have used it.

## Working with stakeholders

A significant part of the role is working with stakeholders to turn business needs into something an engineering team can build: understanding the problem, clarifying workflows, challenging ambiguous requirements, and turning that into MVP definitions, functional requirements, user roles and acceptance criteria. My previous experience in business development at SEET helped here. I'm already comfortable asking questions to uncover the underlying need, and at Majara I apply that from the engineering side.

Because the products are B2B, the software has to fit into an existing company's processes. Multi-tenancy, access boundaries, predictable behavior and data integrity are part of the design from the beginning.

## Keyraa at Majara

My other Majara work was Keyraa, a corporate hotel booking platform whose FastAPI booking backend I built. It is covered in its own project entry, which is where the FastAPI, SQLAlchemy, Redis and Celery details belong.

## Learning AI engineering

Outside of my direct product work with Majara, I've also been deliberately developing my knowledge of AI engineering and LLM-based systems through personal projects and experimentation. That has included exploring tools such as LangChain and LangGraph and learning how retrieval, agent orchestration, and LLMs can be incorporated into software systems. These are currently areas I'm building toward rather than claiming as production AI experience.
