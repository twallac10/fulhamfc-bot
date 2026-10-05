---
layout: default
title: About | Fulham FC stats dashboard
description: About Fulham Data Bot, an auto-updating tracker for Fulham's Premier League season.
headline: About this project
permalink: /about/
twitter:
  card: summary_large_image
---

<div class="container">
    <div class="minimal-header">
        <h1 class="minimal-headline">{{ page.headline }}</h1>
    </div>
    <div class="text-container">
        <h2 class="about-subhead">What's going on here?</h2>

        <p>Fulham Data Bot is a Premier League version of <a href="https://github.com/twallac10/mkebrewers-bot">Brewers Data Bot</a>, which is itself a fork of <a href="https://mattstiles.me/">Matt Stiles</a>' <a href="https://dodgersdata.bot/">Dodgers Data Bot</a>. It is an auto-updating dashboard that tracks how Fulham are doing, this season and against every Premier League campaign since 2001-02.</p>

        <p>Several times a day the bot pulls fresh data: the league table, results, fixtures and squad from <a href="https://www.espn.com/soccer/club/_/id/370/fulham">ESPN</a>, and player stats, expected goals and injury news from the <a href="https://fantasy.premierleague.com/">Fantasy Premier League</a> data feed. It then rebuilds this site and posts updates to <a href="https://bsky.app/profile/{{ site.bluesky_handle }}">Bluesky</a>: match-day previews, team news, final scores and weekly stat reports.</p>

        <h2 class="about-subhead">A few caveats</h2>

        <p>Only Premier League matches are tracked, not cup competitions. The matchweek-by-matchweek table is rebuilt from results, so ties are separated by goal difference and goals scored only. Team expected goals and card counts add up individual player numbers. This is a non-commercial fan project with no connection to Fulham Football Club or the Premier League.</p>

        <h2 class="about-subhead">Thanks</h2>

        <p>Many thanks to Matt Stiles for the original Dodgers Data Bot and for open-sourcing <a href="https://github.com/stiles/dodgers">the code</a>, to <a href="https://github.com/sogrady">Steve O'Grady</a>'s <a href="https://redsox.bot">Red Sox Data Bot</a>, and to Claude Code for help adapting it all from baseball to football.</p>

        <h2 class="about-subhead">Join the conversation</h2>

        <p><a href="https://github.com/twallac10/fulhamfc-bot">Check out the code on GitHub</a> or drop a suggestion.</p>

        <p>Come on you Whites!</p>
    </div>
</div>
