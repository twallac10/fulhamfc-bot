// Sortable tables and heat shading for the players page.

document.addEventListener('DOMContentLoaded', () => {
  const HEAT_LOW = [255, 255, 255];
  const HEAT_HIGH = [204, 0, 0]; // Fulham red

  const shade = (table) => {
    const cols = {};
    table.querySelectorAll('tbody td.heat').forEach(td => {
      const idx = td.cellIndex;
      (cols[idx] = cols[idx] || []).push(td);
    });
    Object.values(cols).forEach(cells => {
      const values = cells.map(td => parseFloat(td.dataset.value) || 0);
      const max = Math.max(...values);
      cells.forEach((td, i) => {
        const t = max > 0 ? values[i] / max : 0;
        const rgb = HEAT_LOW.map((lo, k) => Math.round(lo + t * (HEAT_HIGH[k] - lo)));
        td.style.backgroundColor = `rgb(${rgb.join(',')})`;
        td.style.color = t > 0.55 ? '#fff' : '';
      });
    });
  };

  const cellValue = (row, idx, type) => {
    const td = row.cells[idx];
    if (type === 'num') {
      const v = parseFloat(td.dataset.value !== undefined ? td.dataset.value : td.textContent);
      return isNaN(v) ? -Infinity : v;
    }
    return td.textContent.trim().toLowerCase();
  };

  document.querySelectorAll('table.sortable').forEach(table => {
    shade(table);
    table.querySelectorAll('thead th').forEach((th, idx) => {
      th.classList.add('sort-header');
      th.addEventListener('click', () => {
        const type = th.dataset.type || 'text';
        const desc = th.dataset.sorted !== 'desc';
        table.querySelectorAll('thead th').forEach(h => delete h.dataset.sorted);
        th.dataset.sorted = desc ? 'desc' : 'asc';
        const body = table.tBodies[0];
        const rows = Array.from(body.rows);
        rows.sort((a, b) => {
          const va = cellValue(a, idx, type);
          const vb = cellValue(b, idx, type);
          if (va === vb) return 0;
          const cmp = va > vb ? 1 : -1;
          return type === 'text' ? (desc ? cmp : -cmp) : (desc ? -cmp : cmp);
        });
        rows.forEach(r => body.appendChild(r));
      });
    });
  });
});
