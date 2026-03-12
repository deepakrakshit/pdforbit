# Open-Source Publishing Notes

This repository was cleaned specifically for public GitHub publication.

Cleanup actions included:

- deleting local env files
- deleting local caches and build outputs where safe
- deleting stale planning and utility files not suitable for a public repo
- removing runtime data folders
- adding a root `.gitignore`
- replacing old docs with fresh public-facing documentation

One local exception may still exist on disk:

- a locked `frontend/node_modules/` directory can remain physically present if another process is holding files open

That is still safe for GitHub publication because it is now ignored by `.gitignore`.