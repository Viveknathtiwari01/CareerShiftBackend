# CareerShift - System Architecture

**Version:** 1.0  
**Project:** CareerShift – AI Powered Career Intelligence Platform  
**Architecture Style:** Clean Architecture + Domain Driven Design (DDD)  
**Backend:** FastAPI + SQLAlchemy Async + PostgreSQL  
**Frontend:** React + TypeScript + Vite + TailwindCSS + shadcn/ui  
**Database:** PostgreSQL (Supabase)  
**Storage:** Supabase Storage  
**Author:** Vivek Nath Tiwari

---

# 1. Overview

CareerShift is an AI-powered SaaS platform that helps professionals understand their current career position, evaluate AI readiness, identify skill gaps, generate personalized learning roadmaps, and prepare for future job markets.

The platform focuses on reducing AI fear by helping users collaborate with AI instead of competing against it.

---

# 2. Objectives

- Build AI confidence
- Identify career strengths
- Detect skill gaps
- Measure AI readiness
- Generate career intelligence
- Recommend learning paths
- Track career growth
- Provide AI workshops
- Help users future-proof their careers

---

# 3. Core Product Modules

## User

- Dashboard
- My Career
- AI Assessment
- Career Intelligence Report
- Learning Roadmap
- Workshop
- Profile
- Settings

## Admin

- Dashboard
- User Management
- Assessment Analytics
- Workshop Management
- AI Prompt Management
- Feedback
- Notifications
- Reports
- Settings

---

# 4. High Level Architecture

Frontend

↓

FastAPI REST APIs

↓

Business Services

↓

AI Intelligence Engine

↓

Repository Layer

↓

PostgreSQL

↓

Supabase Storage

↓

OpenAI / Claude / Gemini

---

# 5. Technology Stack

Frontend

- React
- TypeScript
- Vite
- TailwindCSS
- shadcn/ui
- React Query
- React Hook Form
- Zod

Backend

- FastAPI
- SQLAlchemy Async
- Alembic
- Pydantic v2
- JWT Authentication

Database

- PostgreSQL
- Supabase

Storage

- Supabase Storage

Deployment

- Docker
- Nginx
- GitHub Actions

---

# 6. Design Principles

- Clean Architecture
- Domain Driven Design
- SOLID Principles
- Repository Pattern
- Service Layer
- Async First
- API First
- Versioned Data
- Secure by Default

---

# 7. Application Layers

Presentation Layer

↓

API Layer

↓

Business Layer

↓

AI Layer

↓

Repository Layer

↓

Database

---

# 8. Domain Architecture

Auth

Career

Assessment

Intelligence

Learning

Workshop

Reporting

Admin

System

Each domain owns its models, services, repositories and APIs.

---

# 9. User Journey

Landing

↓

Register

↓

Login

↓

Dashboard

↓

My Career

↓

Assessment

↓

AI Analysis

↓

Career Intelligence Report

↓

Learning Roadmap

↓

Workshop

↓

Reassessment

---

# 10. My Career Module

Purpose

Collect professional information that becomes the foundation for AI analysis.

Contains

- Career Identity
- Professional Background
- Skills Intelligence
- Work Profile
- AI Readiness

Output

Career Profile Version

---

# 11. Assessment Module

Assessment is the intelligence engine of CareerShift.

Workflow

Career Profile

↓

Competency Mapping

↓

Task Analysis

↓

3B Analysis

↓

AI Readiness

↓

Career Identity

↓

Recommendations

↓

Learning Roadmap

↓

Final Report

---

# 12. AI Intelligence Engine

Responsible for

- Career Identity
- Competency Mapping
- Skill Gap Detection
- AI Readiness
- Market Analysis
- Recommendation Engine
- Learning Generator
- Career Risk Analysis

---

# 13. 3B Framework

BUILD

Human strengths that cannot easily be replaced by AI.

BOT

Tasks that AI can automate.

BLEND

Tasks where human + AI collaboration creates maximum value.

---

# 14. AI Readiness Engine

Measures

- AI Awareness
- AI Adoption
- Tool Usage
- AI Confidence
- AI Productivity
- Learning Readiness

Output

AI Readiness Score (0-100)

---

# 15. Career Intelligence Report

Tabs

- Overview
- Competencies
- Tasks
- 3B Analysis
- AI Readiness
- Career Identity
- Learning Roadmap
- AI Tools
- Action Plan

---

# 16. Workshop Platform

Features

- Workshop Catalog
- Demo Videos
- Enrollment
- Learning Materials
- Progress Tracking
- Certificates (Future)

Purpose

Help users build AI confidence through guided learning.

---

# 17. Backend Architecture

app/

api/

core/

config/

database/

models/

repositories/

services/

schemas/

ai/

utils/

middlewares/

background/

tests/

---

# 18. Database Architecture

Schemas

auth

career

assessment

intelligence

learning

workshop

reporting

admin

system

Primary Keys

UUID

Soft Delete

deleted_at

Audit Fields

created_at

updated_at

Versioning

Career Profiles

Assessments

Reports

Learning Roadmaps

---

# 19. AI Providers

Supported

OpenAI

Claude

Gemini

Future

Local LLM

Azure OpenAI

Groq

---

# 20. Storage Strategy

Database stores

- Structured Data
- Assessment Results
- AI Outputs
- Metadata

Supabase Storage stores

- Resume
- PDF Reports
- Images
- Certificates
- Workshop Assets

---

# 21. Security

JWT Authentication

RBAC

Refresh Tokens

Password Hashing

HTTPS

CORS

Input Validation

Rate Limiting

Audit Logs

Soft Delete

---

# 22. Performance

Async APIs

Database Indexing

Pagination

Caching (Redis)

Background Jobs

Optimized SQL Queries

Connection Pooling

---

# 23. Scalability

Stateless Backend

Horizontal Scaling

Domain Separation

Cloud Storage

Async Processing

Queue Based Jobs

Future Microservices Ready

---

# 24. Future Enhancements

LinkedIn Import

Resume AI Parser

GitHub Analysis

Interview Preparation

Salary Prediction

Career Coach

AI Chat Assistant

Voice Coach

Enterprise Dashboard

HR Portal

Mobile Application

---

# 25. Success Metrics

- Career Profile Completion
- Assessment Completion Rate
- AI Readiness Improvement
- Learning Progress
- Workshop Enrollment
- User Retention
- Report Downloads
- Daily Active Users
- Recommendation Acceptance
- Career Growth Tracking

---

# 26. Architecture Summary

CareerShift is designed as a modern AI-native SaaS platform that combines structured career profiling, intelligent assessments, AI-powered analysis, personalized learning, and continuous career growth into a single ecosystem.

The architecture follows Domain Driven Design, Clean Architecture, and scalable PostgreSQL-based data modeling to ensure maintainability, extensibility, and enterprise readiness while keeping the platform modular for future AI capabilities.