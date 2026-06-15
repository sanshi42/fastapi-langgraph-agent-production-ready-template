# Postgres For Agent Runtime State

We decided to store Agent runtime state in Postgres rather than preserving the learning runtime's `.tasks`, `.team`, `.worktrees`, and `.scheduled_tasks.json` files as the production source of truth. The file-based format remains useful for workspace-readable project memory and skills, but task, approval, cron, teammate, job, and event state need user/session isolation and deployment-safe recovery.
