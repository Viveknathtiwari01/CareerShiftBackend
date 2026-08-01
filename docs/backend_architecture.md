# CareerShift Backend Architecture

**Version:** 1.0  
**Project:** CareerShift – AI Powered Career Intelligence Platform  
**Framework:** FastAPI  
**Language:** Python 3.13+  
**Architecture:** Clean Architecture + Domain Driven Design (DDD)  
**Database:** PostgreSQL (Supabase)  
**ORM:** SQLAlchemy 2.0 Async  
**Migration:** Alembic

---

# 1. Purpose

This document defines the backend architecture for CareerShift.

It establishes the project structure, design principles, service boundaries, coding standards, dependency flow, and implementation strategy.

The objective is to create a backend that is:

- Modular
- Scalable
- Testable
- Maintainable
- AI-ready
- Enterprise-grade

---

# 2. Architecture Philosophy

CareerShift follows **Clean Architecture** combined with **Domain Driven Design (DDD)**.

Business logic is independent of:

- Database
- API
- AI Providers
- Storage
- Third-party services

Dependencies always point inward.

```
API
↓

Services
↓

Repositories
↓

Database
```

---

# 3. Backend Technology Stack

Language

- Python 3.13+

Framework

- FastAPI

Validation

- Pydantic v2

ORM

- SQLAlchemy Async

Migration

- Alembic

Database

- PostgreSQL

Authentication

- JWT

Password Hashing

- Argon2id / bcrypt

Storage

- Supabase Storage

Caching (Phase 2)

- Redis

Background Jobs (Phase 2)

- Celery / Dramatiq

Documentation

- OpenAPI / Swagger

---

# 4. Project Structure

```
backend/

app/

    api/
        v1/
            auth/
            users/
            career/
            assessment/
            intelligence/
            learning/
            workshop/
            reports/
            admin/

    core/
        config.py
        security.py
        jwt.py
        permissions.py

    database/
        base.py
        session.py
        migrations/

    models/

    schemas/

    repositories/

    services/

    ai/

    background/

    integrations/

    storage/

    utils/

    middleware/

    exceptions/

    tests/

main.py
```

---

# 5. Layer Responsibilities

## API Layer

Responsible for

- Request Validation
- Response Formatting
- Authentication
- Authorization
- Calling Services

No business logic.

---

## Service Layer

Responsible for

- Business Rules
- Workflow
- Validation
- AI Orchestration
- Report Generation

This is the heart of the backend.

---

## Repository Layer

Responsible for

- Database Queries
- CRUD
- Transactions

Repositories never contain business logic.

---

## Database Layer

Responsible for

- Models
- Relationships
- Constraints
- Sessions

---

## AI Layer

Responsible for

- Prompt Templates
- AI Providers
- Prompt Versioning
- AI Analysis
- Recommendation Generation

---

# 6. Domain Modules

Auth

Career

Assessment

Intelligence

Learning

Workshop

Reporting

Admin

System

Every module contains

API

Schemas

Repository

Service

Models

---

# 7. API Design

RESTful APIs

Example

/api/v1/auth

/api/v1/users

/api/v1/career

/api/v1/assessment

/api/v1/intelligence

/api/v1/workshops

/api/v1/reports

---

# 8. Authentication Flow

Register

↓

Verify Email

↓

Login

↓

Generate JWT

↓

Generate Refresh Token

↓

Access Protected APIs

↓

Refresh Token

↓

Logout

---

# 9. Authorization

Role Based Access Control (RBAC)

Roles

Guest

User

Premium User

Admin

Super Admin

Permissions are checked before every protected endpoint.

---

# 10. Dependency Injection

FastAPI Depends()

Used for

Database Session

Current User

Permissions

Repositories

Services

Settings

---

# 11. Validation Strategy

All requests validated using

Pydantic v2

Validation occurs

Request

↓

Schema Validation

↓

Business Validation

↓

Database Validation

---

# 12. Error Handling

Global Exception Handler

Standard Response

```
{
    "success": false,
    "message": "...",
    "errors": [],
    "timestamp": "...",
    "request_id": "..."
}
```

---

# 13. Logging

Application Logs

API Logs

Authentication Logs

AI Logs

Database Logs

Audit Logs

Error Logs

Structured JSON logging.

---

# 14. AI Architecture

AI Service

↓

Prompt Builder

↓

Prompt Version

↓

AI Provider

↓

Structured Response

↓

Parser

↓

Career Intelligence

↓

Database

---

# 15. AI Providers

Supported

OpenAI

Claude

Gemini

Future

Groq

Azure OpenAI

Local Models

Providers are interchangeable through an adapter layer.

---

# 16. Repository Pattern

Each domain has its own repository.

Examples

CareerRepository

AssessmentRepository

LearningRepository

WorkshopRepository

Repositories expose database operations only.

---

# 17. Service Layer

Examples

CareerService

AssessmentService

AIService

LearningService

WorkshopService

ReportService

NotificationService

Services coordinate repositories and AI modules.

---

# 18. Background Jobs

Future implementation

Generate PDF

Email Notifications

AI Analysis

Workshop Emails

Learning Reminders

Scheduled Reports

---

# 19. File Storage

Stored in Supabase Storage

Resume

Reports

Profile Pictures

Workshop Assets

Database stores metadata only.

---

# 20. Security

JWT

RBAC

Password Hashing

HTTPS

Input Validation

Rate Limiting

CORS

Secure Headers

Audit Logs

---

# 21. API Versioning

Current

/api/v1/

Future

/api/v2/

Older versions remain supported during migration.

---

# 22. Database Session

Async SQLAlchemy Session

One session per request.

Automatic rollback on failure.

---

# 23. Transactions

Business operations use transactions.

Example

Create Assessment

↓

Generate AI Analysis

↓

Store Results

↓

Commit

Rollback on failure.

---

# 24. Performance

Async Endpoints

Pagination

Database Indexes

Selective Loading

Connection Pooling

Caching (Future)

Background Processing

---

# 25. Caching Strategy

Phase 2

Redis

Cache

Master Data

Skills

Industries

Domains

AI Prompt Templates

Frequently accessed reports

---

# 26. Testing Strategy

Pytest

Unit Tests

Integration Tests

API Tests

Repository Tests

AI Mock Tests

Coverage Target

>90%

---

# 27. Monitoring

Health Check

Metrics

Slow Queries

API Latency

AI Response Time

Database Connections

Error Rate

---

# 28. CI/CD

GitHub

↓

Tests

↓

Lint

↓

Build Docker

↓

Deploy

↓

Run Migrations

↓

Health Check

---

# 29. Coding Standards

PEP-8

Type Hints

Docstrings

Async First

Small Services

Single Responsibility

No Business Logic in Controllers

Repository Pattern

Consistent Naming

---

# 30. Future Enhancements

Redis

Celery

Kafka

Vector Database

RAG

AI Memory

Organization Accounts

Enterprise Dashboard

Microservices

WebSockets

Event Bus

---

# 31. Backend Request Flow

Client

↓

FastAPI Router

↓

Authentication

↓

Validation

↓

Service Layer

↓

Repository

↓

Database

↓

Service

↓

Response Formatter

↓

Client

---

# 32. AI Assessment Flow

Career Profile

↓

Assessment

↓

AI Prompt

↓

LLM

↓

Response Parser

↓

3B Analysis

↓

AI Readiness

↓

Recommendations

↓

Learning Roadmap

↓

Career Report

---

# 33. Architecture Summary

The CareerShift backend is designed as a modular, domain-driven, AI-native system built on FastAPI and SQLAlchemy Async.

The architecture separates presentation, business logic, persistence, and AI orchestration into independent layers, enabling maintainability, scalability, and future expansion.

This design supports enterprise-grade development while remaining flexible enough to integrate new AI providers, advanced analytics, background processing, and future microservices without requiring major architectural changes.