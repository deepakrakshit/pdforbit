# Architecture

## Overview

PdfORBIT is a monorepo that separates presentation, business state, asynchronous processing, and deployment concerns.

High-level topology:

- Next.js frontend
- FastAPI backend
- Redis-backed job queue
- worker processes
- cleanup process
- PostgreSQL persistence
- filesystem-backed runtime storage abstraction

## Frontend Role

The frontend handles:

- public marketing pages
- tool entry flows
- pricing and subscription UI
- account-facing flows
- secure Razorpay-facing API routes

## Backend Role

The backend handles:

- upload validation
- job creation
- job polling
- download signing
- user state
- billing and subscription authority
- retention-aware cleanup logic

## Billing Design

Billing is intentionally split:

- frontend server routes talk to Razorpay using secrets that never reach the browser
- backend remains the source of truth for payment and subscription state
- an internal shared secret protects backend billing routes

## Processing Model

Heavy PDF operations are handled asynchronously.

This improves:

- responsiveness
- failure isolation
- scalability
- user experience during long-running jobs
