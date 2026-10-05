// Fulham Data Bot dashboard charts (D3 v6).
// Data is embedded in the page by Jekyll as window.FULHAM_DATA.

(function () {
  const DATA = window.FULHAM_DATA || {};
  const COLORS = { W: '#000000', D: '#9e9e9e', L: '#CC0000', team: '#CC0000', past: '#d5d5d5', selected: '#333333' };
  const MATCHES_PER_SEASON = 38;
  const RESULT_WORD = { W: 'Win', D: 'Draw', L: 'Loss' };

  const containerWidth = (el) => Math.max(300, Math.min(900, el.getBoundingClientRect().width || 900));
  const isSmall = () => window.innerWidth < 600;

  function setup(selector, height, margin) {
    const el = document.querySelector(selector);
    if (!el) return null;
    el.innerHTML = '';
    const width = containerWidth(el);
    const svg = d3.select(el).append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('width', '100%')
      .attr('role', 'img');
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
    return { el, svg, g, width: width - margin.left - margin.right, height: height - margin.top - margin.bottom };
  }

  function empty(selector, message) {
    const el = document.querySelector(selector);
    if (el) el.innerHTML = `<p class="note">${message}</p>`;
  }

  // --- Match by match goal difference ---
  function drawResults() {
    const matches = (DATA.matches || []).filter(d => d.match_no != null);
    if (!matches.length) return empty('#results-chart', 'Results will appear after the first match.');
    const margin = { top: 20, right: 10, bottom: 30, left: 30 };
    const c = setup('#results-chart', 220, margin);
    if (!c) return;
    const gd = d => d.goals_for - d.goals_against;
    const maxAbs = Math.max(3, d3.max(matches, d => Math.abs(gd(d))));
    const x = d3.scaleBand().domain(d3.range(1, MATCHES_PER_SEASON + 1)).range([0, c.width]).padding(0.2);
    const y = d3.scaleLinear().domain([-maxAbs, maxAbs]).range([c.height, 0]);

    c.g.append('g').attr('class', 'axis').call(d3.axisLeft(y).ticks(5).tickFormat(d => (d > 0 ? '+' : '') + d));
    c.g.append('line').attr('x1', 0).attr('x2', c.width).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', '#999');
    c.g.append('g').attr('class', 'axis').attr('transform', `translate(0,${c.height})`)
      .call(d3.axisBottom(x).tickValues([1, 10, 19, 28, 38]).tickSize(0)).select('.domain').remove();

    c.g.selectAll('rect.result').data(matches).enter().append('rect')
      .attr('class', 'result')
      .attr('x', d => x(d.match_no))
      .attr('width', x.bandwidth())
      .attr('y', d => (gd(d) === 0 ? y(0) - 2 : y(Math.max(0, gd(d)))))
      .attr('height', d => (gd(d) === 0 ? 4 : Math.abs(y(gd(d)) - y(0))))
      .attr('fill', d => COLORS[d.result])
      .append('title')
      .text(d => `${d.date}: ${RESULT_WORD[d.result]} ${d.goals_for}-${d.goals_against} ${d.home_away === 'home' ? 'vs' : 'at'} ${d.opponent}`);

    c.g.append('text').attr('class', 'axis-label').attr('x', c.width).attr('y', c.height + 26)
      .attr('text-anchor', 'end').text('Match');
  }

  // --- Cumulative points: this season vs past seasons ---
  function drawPointsRace(selectedSeason) {
    const history = DATA.history || [];
    const current = (DATA.matches || []).filter(d => d.match_no != null);
    if (!history.length && !current.length) return empty('#points-race-chart', 'No data yet.');
    const margin = { top: 20, right: isSmall() ? 60 : 80, bottom: 30, left: 35 };
    const c = setup('#points-race-chart', isSmall() ? 300 : 380, margin);
    if (!c) return;

    const bySeason = d3.groups(history, d => d.season);
    const maxPts = Math.max(60, d3.max(history, d => d.cum_points) || 0, d3.max(current, d => d.cum_points) || 0);
    const x = d3.scaleLinear().domain([0, MATCHES_PER_SEASON]).range([0, c.width]);
    const y = d3.scaleLinear().domain([0, maxPts]).nice().range([c.height, 0]);
    const line = d3.line().x(d => x(d.match_no)).y(d => y(d.cum_points));
    const withStart = rows => [{ match_no: 0, cum_points: 0 }, ...rows];

    c.g.append('g').attr('class', 'axis').call(d3.axisLeft(y).ticks(6).tickSize(-c.width))
      .call(g => g.selectAll('.tick line').attr('stroke', '#eee')).select('.domain').remove();
    c.g.append('g').attr('class', 'axis').attr('transform', `translate(0,${c.height})`)
      .call(d3.axisBottom(x).tickValues([0, 10, 19, 28, 38]));

    bySeason.forEach(([season, rows]) => {
      c.g.append('path').datum(withStart(rows)).attr('fill', 'none')
        .attr('stroke', COLORS.past).attr('stroke-width', 1).attr('d', line)
        .append('title').text(`${season}: ${rows[rows.length - 1].cum_points} pts`);
    });

    const label = (rows, text, color) => {
      const last = rows[rows.length - 1];
      c.g.append('text').attr('x', x(last.match_no) + 5).attr('y', y(last.cum_points) + 4)
        .attr('class', 'anno-dark-small').attr('fill', color).text(text);
    };

    if (selectedSeason) {
      const rows = (bySeason.find(([s]) => s === selectedSeason) || [])[1];
      if (rows) {
        c.g.append('path').datum(withStart(rows)).attr('fill', 'none')
          .attr('stroke', COLORS.selected).attr('stroke-width', 2.5).attr('d', line);
        label(rows, `${selectedSeason}: ${rows[rows.length - 1].cum_points}`, COLORS.selected);
      }
    }
    if (current.length) {
      c.g.append('path').datum(withStart(current)).attr('fill', 'none')
        .attr('stroke', COLORS.team).attr('stroke-width', 3.5).attr('d', line);
      c.g.selectAll('circle.current').data(current).enter().append('circle')
        .attr('class', 'current').attr('r', 3).attr('fill', COLORS.team)
        .attr('cx', d => x(d.match_no)).attr('cy', d => y(d.cum_points))
        .append('title').text(d => `Match ${d.match_no}: ${d.cum_points} pts`);
      label(current, `${current[0].season}: ${current[current.length - 1].cum_points}`, COLORS.team);
    }
    c.g.append('text').attr('class', 'axis-label').attr('x', c.width).attr('y', c.height + 26)
      .attr('text-anchor', 'end').text('Match');
    c.g.append('text').attr('class', 'axis-label').attr('x', 4).attr('y', -6).text('Points');
  }

  function setupSeasonSelect() {
    const select = document.getElementById('season-select');
    if (!select) return;
    const seasons = Array.from(new Set((DATA.history || []).map(d => d.season))).sort().reverse();
    seasons.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s;
      opt.textContent = s;
      select.appendChild(opt);
    });
    select.value = seasons[0] || '';
    select.addEventListener('change', () => drawPointsRace(select.value));
  }

  // --- League position after each gameweek ---
  function drawPosition() {
    const rows = (DATA.tableByGameweek || []).filter(d => d.is_team);
    if (!rows.length) return empty('#position-chart', 'The table chart will appear after the first matchweek.');
    const teams = d3.max(DATA.tableByGameweek, d => d.position) || 20;
    const margin = { top: 15, right: 20, bottom: 30, left: 35 };
    const c = setup('#position-chart', 260, margin);
    if (!c) return;
    const maxGw = Math.max(10, d3.max(rows, d => d.gameweek));
    const x = d3.scaleLinear().domain([1, maxGw]).range([0, c.width]);
    const y = d3.scaleLinear().domain([1, teams]).range([0, c.height]);

    c.g.append('rect').attr('x', 0).attr('width', c.width)
      .attr('y', y(teams - 2.5)).attr('height', c.height - y(teams - 2.5))
      .attr('fill', '#fbeaea');
    c.g.append('text').attr('x', c.width - 4).attr('y', c.height - 4).attr('text-anchor', 'end')
      .attr('class', 'anno-grey-small').text('Relegation zone');
    c.g.append('g').attr('class', 'axis').call(d3.axisLeft(y).tickValues([1, 5, 10, 15, 20]));
    c.g.append('g').attr('class', 'axis').attr('transform', `translate(0,${c.height})`)
      .call(d3.axisBottom(x).ticks(Math.min(maxGw, 10)).tickFormat(d3.format('d')));

    c.g.append('path').datum(rows).attr('fill', 'none').attr('stroke', COLORS.team).attr('stroke-width', 3)
      .attr('d', d3.line().x(d => x(d.gameweek)).y(d => y(d.position)));
    c.g.selectAll('circle').data(rows).enter().append('circle').attr('r', 4).attr('fill', COLORS.team)
      .attr('cx', d => x(d.gameweek)).attr('cy', d => y(d.position))
      .append('title').text(d => `Matchweek ${d.gameweek}: position ${d.position} (${d.points} pts)`);
    c.g.append('text').attr('class', 'axis-label').attr('x', c.width).attr('y', c.height + 26)
      .attr('text-anchor', 'end').text('Matchweek');
  }

  // --- Final position in each Premier League season ---
  function drawHistory() {
    const seasons = (DATA.seasons || []).filter(d => d.played > 0 && d.position);
    if (!seasons.length) return empty('#history-chart', 'History data is loading.');
    const all = (DATA.seasons || []).map(d => d.season);
    const margin = { top: 20, right: 10, bottom: 45, left: 30 };
    const c = setup('#history-chart', 240, margin);
    if (!c) return;
    const x = d3.scaleBand().domain(all).range([0, c.width]).padding(0.15);
    const y = d3.scaleLinear().domain([20.5, 1]).range([c.height, 0]);

    c.g.append('g').attr('class', 'axis').call(d3.axisLeft(y).tickValues([1, 5, 10, 15, 20]));
    c.g.append('g').attr('class', 'axis').attr('transform', `translate(0,${c.height})`)
      .call(d3.axisBottom(x).tickValues(all.filter((_, i) => i % (isSmall() ? 4 : 2) === 0)).tickFormat(s => s.slice(2)))
      .selectAll('text').attr('transform', 'rotate(-40)').style('text-anchor', 'end');
    c.g.selectAll('rect').data(seasons).enter().append('rect')
      .attr('x', d => x(d.season)).attr('width', x.bandwidth())
      .attr('y', d => y(d.position)).attr('height', d => c.height - y(d.position))
      .attr('fill', d => (d.zone === 'Relegation' ? COLORS.L : COLORS.W))
      .append('title').text(d => `${d.season}: ${d.position} (${d.points} pts)`);
    c.g.selectAll('text.pos').data(seasons).enter().append('text').attr('class', 'anno-grey-small pos')
      .attr('x', d => x(d.season) + x.bandwidth() / 2).attr('y', d => y(d.position) - 4)
      .attr('text-anchor', 'middle').text(d => (isSmall() ? '' : d.position));
  }

  function drawAll() {
    drawResults();
    const select = document.getElementById('season-select');
    drawPointsRace(select ? select.value : null);
    drawPosition();
    drawHistory();
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (typeof d3 === 'undefined') return;
    setupSeasonSelect();
    drawAll();
    let timer;
    window.addEventListener('resize', () => {
      clearTimeout(timer);
      timer = setTimeout(drawAll, 200);
    });
  });
})();
