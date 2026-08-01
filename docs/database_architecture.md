# CareerShift Database Architecture

**Version:** 1.0  
**Project:** CareerShift – AI Career Intelligence Platform  
**Database:** PostgreSQL 17+  
**ORM:** SQLAlchemy 2.0 Async  
**Migration:** Alembic  
**Storage:** Supabase PostgreSQL + Supabase Storage

---

# 1. Purpose

This document defines the database architecture for CareerShift.

It serves as the single source of truth for database design, schema organization, relationships, indexing strategy, versioning, auditing, and storage conventions.

Objectives:

- Enterprise-grade database design
- High scalability
- Maintainability
- Performance
- AI-ready architecture
- Versioned career intelligence
- Clean SQLAlchemy integration

---

# 2. Database Philosophy

CareerShift is **not a CRUD application**.

It is an AI-powered Career Intelligence Platform.

The database is designed to:

- Preserve career history
- Store assessment evolution
- Version AI reports
- Track learning progress
- Maintain audit history
- Support future enterprise features

Historical data is never overwritten.

---

# 3. Database Technology

Database Engine

- PostgreSQL 17+

ORM

- SQLAlchemy 2.x Async

Migration

- Alembic

Driver

- asyncpg

Validation

- Pydantic v2

Primary Key

- UUID (gen_random_uuid())

---

# 4. Database Design Principles

- Domain Driven Design
- Normalized relational model
- JSONB for AI-generated data
- Immutable historical records
- Soft delete support
- Audit-first approach
- Version-controlled intelligence
- Async optimized
- Cloud ready

---

# 5. Database Schemas

CareerShift uses domain-based schemas instead of placing every table in the public schema.

Schemas:

auth

career

assessment

intelligence

learning

workshop

reporting

admin

system

Each schema owns its own business entities.

---

# 6. Domain Responsibilities

## auth

Authentication

Authorization

Users

Roles

Permissions

Sessions

Refresh Tokens

---

## career

Career Profiles

Experience

Skills

Career Goals

Education

Certifications

Languages

---

## assessment

Assessment Sessions

Competencies

Tasks

Answers

Task Reviews

Scores

---

## intelligence

Career Identity

AI Readiness

3B Analysis

Recommendations

Risk Analysis

Opportunity Analysis

---

## learning

Learning Roadmaps

Milestones

Progress

Learning Goals

Skill Tracking

---

## workshop

Workshops

Modules

Videos

Enrollments

Progress

Certificates

---

## reporting

Reports

Report Versions

Sections

PDF Exports

---

## admin

Feedback

Notifications

Audit Logs

Analytics

Support Tickets

---

## system

Application Settings

Feature Flags

Configurations

Master Data

---

# 7. Core Entities

Users

Career Profiles

Assessment Sessions

Competencies

Tasks

AI Readiness

3B Analysis

Career Reports

Learning Roadmaps

Workshop Enrollments

Notifications

Audit Logs

---

# 8. Entity Relationships

User

↓

Career Profile

↓

Assessment Session

↓

Competency Analysis

↓

Task Analysis

↓

3B Analysis

↓

AI Readiness

↓

Career Intelligence

↓

Learning Roadmap

↓

Workshop

---

# 9. Primary Key Strategy

Every table uses

UUID

Example

id UUID PRIMARY KEY

Advantages

- Secure
- Globally unique
- Distributed systems ready
- Better API exposure

---

# 10. Audit Fields

Every business table contains

id

created_at

updated_at

created_by

updated_by

deleted_at

version

This provides complete auditability.

---

# 11. Versioning Strategy

Versioned entities

Career Profile

Assessment

Career Report

Learning Roadmap

AI Snapshot

Historical records are immutable.

Updates create new versions.

---

# 12. Soft Delete Strategy

Business records are never permanently removed.

Instead

deleted_at

is populated.

Application queries always filter

deleted_at IS NULL

---

# 13. JSONB Strategy

JSONB is used only for dynamic AI-generated content.

Examples

Career Summary

AI Analysis

Recommendations

Market Insights

Prompt Output

Assessment Snapshot

Do not store relational data in JSON.

---

# 14. File Storage Strategy

Database stores only metadata.

Actual files are stored in Supabase Storage.

Examples

Resume

Avatar

Career Reports

Certificates

Workshop Assets

Database stores

file_url

file_size

mime_type

storage_provider

---

# 15. Assessment Data Flow

Career Profile

↓

Assessment

↓

Competencies

↓

Tasks

↓

AI Processing

↓

Recommendations

↓

Learning Roadmap

↓

Career Report

Everything is versioned.

---

# 16. AI Data Storage

Store

Career Identity

Recommendations

Confidence Score

Risk Analysis

Opportunity Analysis

Learning Plan

Do not store unnecessary prompt history.

Only persist structured outputs required for reproducibility.

---

# 17. AI Snapshot Strategy

Each completed assessment creates a snapshot.

Snapshot contains

Assessment Version

Prompt Version

Model Version

AI Provider

Generated Output

Confidence

Generation Time

This allows future comparisons.

---

# 18. Recommendation Architecture

Recommendations belong to

Assessment

Categories

Skills

Career

AI Tools

Learning

Risk

Opportunities

Priority

Low

Medium

High

Critical

---

# 19. Learning Architecture

Assessment

↓

Skill Gap

↓

Learning Goal

↓

Milestones

↓

Progress

↓

Completion

Roadmaps are regenerated after every reassessment.

---

# 20. Workshop Architecture

Workshop

↓

Modules

↓

Videos

↓

Enrollment

↓

Learning Progress

↓

Certificate

Future versions support quizzes and assignments.

---

# 21. Index Strategy

Indexes on

Email

Status

Foreign Keys

Assessment Date

Created Date

Report Version

Composite indexes

(user_id, created_at)

(user_id, status)

(assessment_id, version)

GIN indexes

JSONB

---

# 22. Constraints

Primary Keys

Foreign Keys

Unique Constraints

Check Constraints

Not Null Constraints

Examples

Email unique

Score between 0–100

AI confidence between 0–1

---

# 23. Performance Strategy

Connection Pooling

Async Queries

Pagination

Optimized Indexes

JSONB GIN Indexes

Lazy Loading

Batch Inserts

Background Processing

---

# 24. Security

Password Hashing

JWT

Refresh Tokens

RBAC

Audit Logs

Encrypted Secrets

HTTPS

Input Validation

Rate Limiting

Soft Delete

---

# 25. Scalability

Stateless Backend

Cloud Storage

Versioned Intelligence

Horizontal Scaling

Future Redis Cache

Future Message Queue

Future Microservices

---

# 26. Backup Strategy

Daily Database Backup

Point-in-Time Recovery

Storage Backup

Migration Version Control

Audit Preservation

---

# 27. Naming Convention

Tables

Plural

Snake Case

Columns

Snake Case

Primary Key

id

Foreign Key

entity_id

Indexes

idx_

Unique

uq_

Foreign Keys

fk_

Check Constraints

chk_

---

# 28. Future Database Features

Multi-Tenant Architecture

Organization Accounts

HR Portal

Enterprise Analytics

Salary Benchmark Dataset

Market Trend Dataset

AI Fine-Tuning Dataset

Event Store

Data Warehouse

---

# 29. Database Lifecycle

Create Profile

↓

Assessment

↓

AI Analysis

↓

Report Generation

↓

Learning Roadmap

↓

Workshop

↓

Reassessment

↓

Version Comparison

↓

Continuous Career Growth

---

# 30. Summary

The CareerShift database is designed as a production-ready, domain-driven PostgreSQL architecture focused on career intelligence rather than simple data storage.

The architecture emphasizes immutable historical records, AI-generated insights, structured relational modeling, JSONB for dynamic intelligence, auditability, scalability, and enterprise readiness.

This design serves as the foundation for SQLAlchemy models, Alembic migrations, REST APIs, AI services, and future enterprise modules while ensuring long-term maintainability and performance.