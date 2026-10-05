---
layout: default
title: Player stats | Fulham FC goals, assists & expected goals
description: Season-to-date Premier League stats for every Fulham player, including expected goals and assists.
permalink: /players/
header:
  og_image: /assets/images/meta_card.png
twitter:
  card: summary_large_image
---

{% assign players = site.data.players.fulham_players_current | where_exp: "p", "p.minutes > 0" %}

<div class="container">
  <div class="minimal-header">
    <h1 class="minimal-headline">Who's delivering?</h1>
    <p class="minimal-subhead">Premier League numbers for every Fulham player who has featured this season, from the <a href="https://fantasy.premierleague.com/">Fantasy Premier League</a> data feed. Expected goals (xG) and expected assists (xA) estimate how many goals a player's chances and passes would produce on average. Click a column to sort.</p>
  </div>

  <h2 class="stat-group">Attacking</h2>
  <div class="table-scroll">
  <table class="data-table sortable" id="attack-table">
    <thead>
      <tr>
        <th class="left" data-type="text">Player</th>
        <th data-type="text" class="hide-sm">Pos</th>
        <th data-type="num">Mins</th>
        <th data-type="num">G</th>
        <th data-type="num">A</th>
        <th data-type="num">xG</th>
        <th data-type="num">xA</th>
        <th data-type="num" title="Goals minus expected goals">G−xG</th>
        <th data-type="num" class="hide-sm" title="Expected goal involvements per 90 minutes">xGI/90</th>
      </tr>
    </thead>
    <tbody>
      {% for p in players %}
      <tr>
        <td class="left">{{ p.name }}</td>
        <td class="hide-sm">{{ p.position | slice: 0, 3 | upcase }}</td>
        <td>{{ p.minutes }}</td>
        <td class="heat" data-value="{{ p.goals_scored }}">{{ p.goals_scored }}</td>
        <td class="heat" data-value="{{ p.assists }}">{{ p.assists }}</td>
        <td class="heat" data-value="{{ p.expected_goals }}">{{ p.expected_goals | round: 2 }}</td>
        <td class="heat" data-value="{{ p.expected_assists }}">{{ p.expected_assists | round: 2 }}</td>
        <td data-value="{{ p.goals_minus_xg }}">{% if p.goals_minus_xg > 0 %}+{% endif %}{{ p.goals_minus_xg | round: 2 }}</td>
        <td class="hide-sm heat" data-value="{{ p.expected_goal_involvements_per_90 | default: 0 }}">{{ p.expected_goal_involvements_per_90 | default: "–" }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  </div>
  <p class="note">Per-90 rates shown for players with at least 90 minutes.</p>

  <h2 class="stat-group">Defending, goalkeeping and discipline</h2>
  <div class="table-scroll">
  <table class="data-table sortable" id="defence-table">
    <thead>
      <tr>
        <th class="left" data-type="text">Player</th>
        <th data-type="num">Starts</th>
        <th data-type="num" title="Clean sheets (60+ minutes played)">CS</th>
        <th data-type="num" title="Tackles">Tkl</th>
        <th data-type="num" class="hide-sm" title="Clearances, blocks and interceptions">CBI</th>
        <th data-type="num" class="hide-sm" title="Ball recoveries">Rec</th>
        <th data-type="num">Saves</th>
        <th data-type="num" title="Yellow cards">YC</th>
        <th data-type="num" title="Red cards">RC</th>
      </tr>
    </thead>
    <tbody>
      {% for p in players %}
      <tr>
        <td class="left">{{ p.name }}</td>
        <td>{{ p.starts }}</td>
        <td class="heat" data-value="{{ p.clean_sheets }}">{{ p.clean_sheets }}</td>
        <td class="heat" data-value="{{ p.tackles }}">{{ p.tackles }}</td>
        <td class="hide-sm heat" data-value="{{ p.clearances_blocks_interceptions }}">{{ p.clearances_blocks_interceptions }}</td>
        <td class="hide-sm heat" data-value="{{ p.recoveries }}">{{ p.recoveries }}</td>
        <td data-value="{{ p.saves }}">{{ p.saves }}</td>
        <td data-value="{{ p.yellow_cards }}">{{ p.yellow_cards }}</td>
        <td data-value="{{ p.red_cards }}">{{ p.red_cards }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  </div>
</div>

<script src="{{ '/assets/js/tables.js' | relative_url }}"></script>
