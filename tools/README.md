# Rebuilding the plan

1. Re-scrape the Oliveboard course page (logged in) into `course.json` (class list + live dates) and `links.json` (class ids, PDF links).
2. `python3 build_schedule.py course.json schedule.json links.json`
3. Copy `template.html` and `build_site.py` next to `schedule.json`, run `python3 build_site.py "<date>"`, and copy `site/index.html` to the repo root.

Upcoming live classes have no class id until they air, so re-run step 1 every week or two to fill in their video links.
