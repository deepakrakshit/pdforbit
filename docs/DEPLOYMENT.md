# Deployment

## Recommended Topology

- frontend service
- backend API service
- worker service
- cleanup service
- PostgreSQL
- Redis
- persistent storage volume for backend runtime files

## Frontend Variables

- `NEXT_PUBLIC_API_BASE`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `BILLING_INTERNAL_API_SECRET`

## Backend Variables

The variables below are required for a working deployment. Additional variables for OCR, rate limiting, cleanup intervals, translation, and internal admin are supported. See `README.md` for the full list.

- `DATABASE_URL`
- `REDIS_URL`
- `FILES_ROOT`
- `JWT_ACCESS_SECRET`
- `JWT_REFRESH_SECRET`
- `DOWNLOAD_SIGNING_SECRET`
- `BILLING_INTERNAL_API_SECRET`

## Deployment Checklist

1. run backend tests
2. run frontend build
3. apply migrations
4. deploy backend
5. deploy frontend
6. verify backend readiness
7. verify homepage and pricing page
8. verify billing route behavior