# API Contract

The frontend is built against these routes:

- `POST /api/v1/upload`
- `POST /api/v1/organize/*`
- `POST /api/v1/optimize/*`
- `POST /api/v1/convert/*`
- `POST /api/v1/edit/*`
- `POST /api/v1/security/*`
- `POST /api/v1/intelligence/translate`
- `POST /api/v1/intelligence/summarize`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/download/{job_id}?exp=...&sig=...`

The polling response returns top-level `download_url`, `result_url`, and tool metrics needed by the UI.