"use strict";

(() => {
  const main = document.querySelector(".catalogue");
  if (!main) return;
  const nav = document.querySelector(".section-nav");
  const headings = [...main.querySelectorAll("h2")];
  if (nav && headings.length) {
    for (const [index, heading] of headings.entries()) {
      if (!heading.id) heading.id = `section-${index + 1}`;
      const link = document.createElement("a");
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent;
      nav.append(link);
    }
    nav.hidden = false;
  }

  const tables = [];
  const years = new Set();
  for (const [index, table] of [...main.querySelectorAll("table")].entries()) {
    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    wrapper.tabIndex = 0;
    wrapper.setAttribute("role", "region");
    let heading = table.previousElementSibling;
    while (heading && !/^H[23]$/.test(heading.tagName)) heading = heading.previousElementSibling;
    const name = heading ? heading.textContent.trim() : `Reading table ${index + 1}`;
    wrapper.setAttribute("aria-label", `${name} — scroll horizontally for more columns`);
    table.before(wrapper);
    wrapper.append(table);

    const dateColumns = [];
    [...table.rows[0].cells].forEach((cell, position) => {
      const match = cell.textContent.trim().match(/^(20\d{2})(?:\s*[-–]\s*20\d{2})?$/);
      if (!match) return;
      const year = Number(match[1]);
      years.add(year);
      dateColumns.push({ position, year });
      for (const row of table.rows) row.cells[position]?.classList.add("date-column");
    });
    if (!dateColumns.length) continue;
    const message = document.createElement("p");
    message.className = "date-unavailable";
    message.textContent = "This table does not list dates for the selected years. All reading links remain available.";
    message.hidden = true;
    wrapper.after(message);
    tables.push({ table, dateColumns, message });
  }

  const form = document.querySelector(".calendar-controls");
  const select = document.querySelector("#first-year");
  const showAll = document.querySelector("#all-years");
  const status = document.querySelector("#year-status");
  if (!form || !select || !showAll || !status || !years.size) return;
  const available = [...years].sort((a, b) => a - b);
  for (const year of available) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = String(year);
    select.append(option);
  }
  const now = new Date().getFullYear();
  select.value = String(available.find(year => year >= now) ?? available.at(-1));

  const update = () => {
    const first = Number(select.value);
    const last = Math.min(first + 2, available.at(-1));
    select.disabled = showAll.checked;
    for (const { table, dateColumns, message } of tables) {
      let shown = 0;
      for (const { position, year } of dateColumns) {
        const visible = showAll.checked || (year >= first && year <= last);
        if (visible) shown += 1;
        for (const row of table.rows) if (row.cells[position]) row.cells[position].hidden = !visible;
      }
      message.hidden = shown > 0;
    }
    status.textContent = showAll.checked
      ? `All date columns: ${available[0]}–${available.at(-1)}`
      : `Year columns: ${first}${first === last ? "" : `–${last}`}`;
  };
  form.addEventListener("submit", event => event.preventDefault());
  select.addEventListener("change", update);
  showAll.addEventListener("change", update);
  form.hidden = false;
  update();
})();
