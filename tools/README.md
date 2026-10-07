# Rebuilding the plan

1. Re-scrape the Oliveboard course page (logged in) into `course.json` (class list + live dates), `links.json` (class ids, PDF links) and `status.json` (half-watched classes).
2. `python3 build_schedule.py course.json schedule.json links.json status.json` → writes `schedule_plan.json` (class queues, original-plan dates, tests).
3. `python3 build_site.py "<date>"` → writes `site/index.html`; copy it to the repo root.

The page schedules itself in the browser from `schedule_plan.json` and whatever the user has marked done, so class ids (`c<index>`) must stay stable between rebuilds.
Upcoming live classes have no class id until they air: re-run step 1 every week or two to fill in their video links.
