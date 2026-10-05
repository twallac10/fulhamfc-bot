---
layout: default
title: Squad | Fulham FC players & availability
description: The current Fulham first-team squad with shirt numbers, positions and injury or suspension news.
permalink: /squad/
header:
  og_image: /assets/images/meta_card.png
twitter:
  card: summary_large_image
---

{% assign squad = site.data.squad.fulham_squad_current %}
{% assign unavailable = site.data.squad.fulham_availability %}

<div class="container">
  <div class="minimal-header">
    <h1 class="minimal-headline">Who's in the squad?</h1>
    <p class="minimal-subhead">Fulham's first-team squad, according to <a href="https://www.espn.com/soccer/team/squad/_/id/370/fulham">ESPN</a>, with injury and suspension news from the <a href="https://fantasy.premierleague.com/">Fantasy Premier League</a> feed.</p>
  </div>

  <h2 class="stat-group">Availability</h2>
  {% if unavailable and unavailable.size > 0 %}
  <div class="table-scroll">
  <table class="data-table">
    <thead><tr><th class="left">Player</th><th>Status</th><th class="left">News</th></tr></thead>
    <tbody>
      {% for p in unavailable %}
      <tr>
        <td class="left">{{ p.name }}</td>
        <td><span class="status-pill status-{{ p.status }}">{{ p.status_label }}</span></td>
        <td class="left">{{ p.news | default: "–" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  </div>
  {% else %}
  <p class="chart-chatter">No injury or suspension news. Everyone is available.</p>
  {% endif %}

  {% assign position_groups = squad | map: "position_group" | uniq %}
  {% for group in position_groups %}
    <h2 class="stat-group">{{ group }}</h2>
    <div class="roster-grid">
      {% assign group_players = squad | where: "position_group", group %}
      {% for player in group_players %}
        <div class="stat-card player-card">
          {% if player.status == 'i' %}
            <div class="player-flag player-flag-injured">INJURED</div>
          {% elsif player.status == 'd' %}
            <div class="player-flag player-flag-doubtful">DOUBTFUL</div>
          {% elsif player.status == 's' %}
            <div class="player-flag player-flag-injured">SUSPENDED</div>
          {% elsif player.status == 'u' or player.status == 'n' %}
            <div class="player-flag player-flag-minors">UNAVAILABLE</div>
          {% endif %}
          <img src="{{ '/assets/images/placeholder-avatar.png' | relative_url }}" alt="" class="player-avatar" />
          <div class="player-name">{{ player.name }}</div>
          <div class="player-details">
            {{ player.position }}{% if player.age %} | Age {{ player.age }}{% endif %}{% if player.nationality %} | {{ player.nationality }}{% endif %}
          </div>
          {% if player.jersey %}<div class="player-jersey">#{{ player.jersey }}</div>{% endif %}
        </div>
      {% endfor %}
    </div>
  {% endfor %}
</div>
