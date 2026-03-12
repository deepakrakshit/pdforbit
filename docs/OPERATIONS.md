# Operations

## Key Health Checks

- backend readiness endpoint
- upload success path
- job completion path
- queue connectivity
- storage writability
- pricing page availability
- billing activation path

## Before a Release

- run backend tests
- run frontend build
- apply database migrations before promoting backend
- confirm environment changes
- confirm docs are updated

## After a Release

- verify the backend health endpoint
- verify homepage load
- verify pricing page load
- verify one core tool path
- verify billing route availability if billing changed