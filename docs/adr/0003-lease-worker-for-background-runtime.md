# Lease Worker For Background Runtime

We decided that cron, teammate, and background runtime work should use application-level workers guarded by Postgres leases. This avoids the duplicate execution risk of simple in-process threads when the API is run with multiple workers, without introducing a separate queue service in the first implementation.
