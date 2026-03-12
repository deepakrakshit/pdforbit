# Contributing to PdfORBIT

Thanks for considering a contribution.

PdfORBIT is a full-stack PDF processing platform with a Next.js frontend and a FastAPI backend.

## Principles

- keep changes focused
- fix root causes where practical
- preserve public behavior unless a change is intentional
- never commit secrets or local env files
- update docs when behavior changes
- add tests for important logic changes

## Before Opening a Pull Request

1. run relevant backend tests
2. run the frontend build
3. verify that no local `.env` files are staged
4. document any environment changes
5. document deploy impact if applicable

## Standards

- follow existing naming conventions
- keep comments sparse and useful
- avoid unnecessary abstractions
- prefer explicit schemas and typed contracts
- avoid committing generated artifacts

## Documentation

If you change project structure, deployment flow, billing behavior, or public product positioning, update the relevant docs:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/OPERATIONS.md`
- `docs/SHOWCASE.md` if public product positioning changes
- `docs/ROADMAP.md` if planned features change
- `docs/STATUS.md` if production posture changes
- `docs/API_CONTRACT.md` if the API contract changes
- `AI_ASSISTANCE.md` if the disclosure needs refinement

## Maintainer

- Deepak Rakshit
- LinkedIn: https://www.linkedin.com/in/deepakrakshit/