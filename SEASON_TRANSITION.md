# Season transition

Premier League seasons run August to May. Each summer, after the new fixtures are published (mid-June):

1. **Bump the season** in `scripts/config.py`:

   ```python
   SEASON_START_YEAR = 2027  # 2027-28
   ```

   This updates the league table, fixtures and summary scripts. The next run of `06_fetch_historical_seasons.py` then adds the season just finished (e.g. 2026-27) to the history automatically.

2. **Fantasy Premier League reset.** The FPL API switches to the new season in July. Until the first matchweek is played, player stats are zero and `03_build_table_progression.py` exits without saving. The dashboard shows "will appear after the first matchweek" messages. That's expected.

3. **If Fulham are relegated**, the Premier League feeds stop covering them. Options:
   - Pause the posting workflows (Actions → workflow → "Disable workflow").
   - Or adapt to the Championship: set `ESPN_LEAGUE = "eng.2"` in `scripts/config.py`. FPL only covers the Premier League, so scripts 03, 04 and 05 need another source or should be disabled.

4. **Check the first run** of `fetch` after the opening weekend:
   - The table shows the new season, the "points race" has a new red line, and the history includes last season.
   - The match-day bot posts on the first match day (check `post_matchday` logs).

Optionally, run `fetch_historical` manually once the season has ended to refresh the history cache immediately.
