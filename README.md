# open-job-radar
Personal platform for discovering, filtering, and tracking jobs from ATS platforms and remote job sources.

## Scheduled synchronization

Configure `DATABASE_URL` and run this one-shot command with Heroku Scheduler:

```text
python -m open_job_radar.scheduled_sync
```

The command synchronizes each enabled source tenant once and exits with status
`0` on success or a non-zero status when synchronization fails.
