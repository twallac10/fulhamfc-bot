---
layout: default
title: "Fulham FC Premier League dashboard | Updated stats & analysis"
description: "An auto-updating dashboard that answers the question: How are Fulham doing?"
permalink: /
header:
  og_image: /assets/images/meta_card.png
twitter:
  card: summary_large_image
---

{% assign summary_data = site.data.standings.season_summary_latest %}
{% assign last_result = summary_data | where: "stat", "last_match_result" | first %}
{% assign summary_item = summary_data | where: "stat", "summary" | first %}

<div class="container">

<div class="minimal-header">
  <div class="minimal-trend-icon">
    {% if last_result.value == 'win' %}
      <i class="fa-solid fa-arrow-trend-up"></i>
    {% elsif last_result.value == 'loss' %}
      <i class="fa-solid fa-arrow-trend-down"></i>
    {% else %}
      <i class="fa-solid fa-arrows-left-right"></i>
    {% endif %}
  </div>
  <h1 class="minimal-headline">{{ site.headline }}</h1>
  <p class="minimal-subhead">
    {% if summary_item %}{{ summary_item.value }}{% else %}Data for the new season is on its way.{% endif %}
  </p>
</div>

<h2 class="stat-group">{{ site.data.matches.fulham_matches_current.first.season | default: "This season" }} Premier League season</h2>
<div class="stat-grid">
  {% for item in summary_data %}
    {% if item.category == 'standings' %}
    <div class="stat-card">
      <div class="stat-card-label">{{ item.stat_label }}</div>
      <div class="stat-card-value{% if item.stat == 'form' %} form-value{% endif %}">
        {% if item.stat == 'form' %}
          {% assign letters = item.value | split: "" %}
          {% for l in letters %}<span class="form-badge form-{{ l }}">{{ l }}</span>{% endfor %}
        {% else %}{{ item.value }}{% endif %}
      </div>
      <p class="stat-card-context">{{ item.context_value_label }}: {{ item.context_value }}</p>
    </div>
    {% endif %}
  {% endfor %}
</div>

<h3 class="visual-subhead">Match by match: <span class="win">wins</span>, <span class="draw">draws</span>, <span class="loss">losses</span> and goal difference</h3>
<div id="results-chart" class="chart-container"></div>

<h3 class="visual-subhead">Points race: Then and now</h3>
<p class="chart-chatter">Fulham's running points total this season (<span class="highlight">red</span>) against every Premier League season since 2001-02. Pick a season to compare.</p>
<select id="season-select" aria-label="Compare with a past season">
  <option value="">Compare with a past season</option>
</select>
<div id="points-race-chart" class="chart-container"></div>

<h3 class="visual-subhead">League position by matchweek</h3>
<p class="chart-chatter">Where Fulham sat in the table after each round of fixtures. The shaded band is the relegation zone.</p>
<div id="position-chart" class="chart-container"></div>
<p class="note">Note: Rebuilt from every Premier League result, so ties are broken by goal difference then goals scored.</p>

<div class="tables-container schedule-tables">
  <div class="table-wrapper">
    <h3 class="visual-subhead">Last five</h3>
    <table class="data-table">
      <thead><tr><th>Date</th><th>Opponent</th><th></th><th>Result</th></tr></thead>
      <tbody>
        {% assign last_five = site.data.matches.fulham_schedule | where: "placement", "last" %}
        {% for m in last_five %}
        <tr>
          <td>{{ m.date | date: "%b %-d" }}</td>
          <td>{{ m.opponent }}</td>
          <td>{% if m.home_away == 'home' %}<i class="fas fa-home home-icon" title="Home"></i>{% else %}<i class="fas fa-road road-icon" title="Away"></i>{% endif %}</td>
          <td><span class="form-badge form-{{ m.result }}">{{ m.result }}</span> {{ m.score }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="table-wrapper">
    <h3 class="visual-subhead">Next five</h3>
    <table class="data-table">
      <thead><tr><th>Date</th><th>Opponent</th><th></th><th>Kickoff (UK)</th></tr></thead>
      <tbody>
        {% assign next_five = site.data.matches.fulham_schedule | where: "placement", "next" %}
        {% for m in next_five %}
        <tr>
          <td>{{ m.date | date: "%b %-d" }}</td>
          <td>{{ m.opponent }}</td>
          <td>{% if m.home_away == 'home' %}<i class="fas fa-home home-icon" title="Home"></i>{% else %}<i class="fas fa-road road-icon" title="Away"></i>{% endif %}</td>
          <td>{{ m.kickoff_local }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<h2 class="stat-group">Premier League table</h2>
<div class="table-scroll">
<table class="data-table league-table">
  <thead>
    <tr><th>Pos</th><th class="left">Club</th><th>P</th><th class="hide-sm">W</th><th class="hide-sm">D</th><th class="hide-sm">L</th><th class="hide-sm">GF</th><th class="hide-sm">GA</th><th>GD</th><th>Pts</th></tr>
  </thead>
  <tbody>
    {% for team in site.data.standings.league_table %}
    <tr class="{% if team.is_team %}team-row{% endif %}">
      <td><span class="zone-marker" {% if team.zone_color %}style="background: {{ team.zone_color }}" title="{{ team.zone }}"{% endif %}></span>{{ team.position }}</td>
      <td class="left">{{ team.team }}</td>
      <td>{{ team.played }}</td>
      <td class="hide-sm">{{ team.won }}</td>
      <td class="hide-sm">{{ team.drawn }}</td>
      <td class="hide-sm">{{ team.lost }}</td>
      <td class="hide-sm">{{ team.goals_for }}</td>
      <td class="hide-sm">{{ team.goals_against }}</td>
      <td>{% if team.goal_difference > 0 %}+{% endif %}{{ team.goal_difference }}</td>
      <td><strong>{{ team.points }}</strong></td>
    </tr>
    {% endfor %}
  </tbody>
</table>
</div>
<p class="note">Colored markers show European qualification and relegation places.</p>

<h2 class="stat-group">Attack and defence</h2>
<div class="stat-grid">
  {% for item in summary_data %}
    {% if item.category == 'attack' or item.category == 'defence' %}
    <div class="stat-card">
      <div class="stat-card-label">{{ item.stat_label }}</div>
      <div class="stat-card-value{% if item.stat == 'top_scorer' or item.stat == 'top_assister' %} text-value{% endif %}">{{ item.value }}</div>
      <p class="stat-card-context">{{ item.context_value_label }}: {{ item.context_value }}</p>
    </div>
    {% endif %}
  {% endfor %}
</div>
<p class="note">Expected goals and card counts sum Fulham's players in the <a href="https://fantasy.premierleague.com/">Fantasy Premier League</a> data. See the <a href="{{ '/players/' | relative_url }}">players page</a> for individual numbers.</p>

<h2 class="stat-group">Fulham in the Premier League</h2>
<p class="chart-chatter">Final position in every top-flight season since 2001-02.</p>
<div id="history-chart" class="chart-container"></div>
<div class="table-scroll">
<table class="data-table league-table">
  <thead><tr><th class="left">Season</th><th>Pos</th><th>W</th><th>D</th><th>L</th><th class="hide-sm">GF</th><th class="hide-sm">GA</th><th>Pts</th></tr></thead>
  <tbody>
    {% assign seasons = site.data.history.fulham_pl_seasons | reverse %}
    {% for s in seasons %}
      {% if s.played > 0 %}
      <tr>
        <td class="left">{{ s.season }}</td>
        <td>{{ s.position | default: "–" }}</td>
        <td>{{ s.won }}</td><td>{{ s.drawn }}</td><td>{{ s.lost }}</td>
        <td class="hide-sm">{{ s.goals_for }}</td><td class="hide-sm">{{ s.goals_against }}</td>
        <td><strong>{{ s.points }}</strong></td>
      </tr>
      {% endif %}
    {% endfor %}
  </tbody>
</table>
</div>

{% if site.data.news.fulham_news and site.data.news.fulham_news.size > 0 %}
<h2 class="stat-group">Latest headlines</h2>
<ul class="headline-list">
  {% for a in site.data.news.fulham_news limit: 6 %}
  <li><a href="{{ a.url }}">{{ a.headline }}</a> <span class="headline-meta">{{ a.source }} · {{ a.published | date: "%b %-d" }}</span></li>
  {% endfor %}
</ul>
{% endif %}

</div>

<script>
  window.FULHAM_DATA = {
    matches: {{ site.data.matches.fulham_matches_current | jsonify }},
    history: {{ site.data.history.fulham_pl_history_matches | jsonify }},
    seasons: {{ site.data.history.fulham_pl_seasons | jsonify }},
    tableByGameweek: {{ site.data.standings.table_by_gameweek | jsonify }}
  };
</script>
<script src="{{ '/assets/js/dashboard.js' | relative_url }}"></script>
