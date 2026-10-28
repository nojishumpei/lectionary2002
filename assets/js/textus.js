"use strict";

(() => {
  const script = document.currentScript;
  const url = script?.dataset.textusUrl;
  const pdfBase = script?.dataset.pdfBase;
  const main = document.querySelector(".catalogue");
  if (!url || !pdfBase || !main) return;
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const dialog = el("dialog", null, "textus-reader");
  dialog.id = "textus-reader";
  dialog.setAttribute("lang", "la");
  dialog.setAttribute("aria-labelledby", "textus-title");
  const header = el("div", null, "textus-header");
  const heading = el("div");
  const context = el("p", null, "textus-context");
  const title = el("h2"); title.id = "textus-title";
  const reference = el("p", null, "textus-reference");
  heading.append(context, title, reference);
  const close = el("button", "Claude", "textus-close");
  close.type = "button"; close.setAttribute("aria-label", "Claude textum");
  header.append(heading, close);
  const body = el("div", null, "textus-body");
  const footer = el("div", null, "textus-pdfs");
  dialog.append(header, body, footer); document.body.append(dialog);
  let opener;
  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => {
    if (opener) { opener.setAttribute("aria-expanded", "false"); opener.focus({preventScroll: true}); }
  });
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const r = dialog.getBoundingClientRect();
    if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();
  });
  function open(record, button) {
    opener = button;
    context.textContent = [record.celebration, record.year && `Anno ${record.year}`, record.mass].filter(Boolean).join(" · ");
    title.textContent = record.reading;
    reference.textContent = [record.reference, record.form, record.number && `N. ${record.number}`].filter(Boolean).join(" · ");
    body.replaceChildren();
    if (record.intro) body.append(el("p", record.intro, "textus-intro"));
    record.paragraphs.forEach(p => body.append(el("p", p)));
    body.append(el("p", "Verbum Dómini.", "textus-conclusion"));
    footer.replaceChildren();
    record.pdfs.forEach((pdf, index) => {
      const link = el("a", record.pdfs.length > 1 ? (index ? "Tonus Evangelii · PDF" : "Tonus Antiquior · PDF") : "PDF");
      link.href = pdfBase + pdf; link.target = "_blank"; link.rel = "noopener noreferrer"; footer.append(link);
    });
    button.setAttribute("aria-expanded", "true");
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0; close.focus({preventScroll: true});
  }
  fetch(url).then(response => {
    if (!response.ok) throw new Error("Reading text unavailable");
    return response.json();
  }).then(records => {
    const cellReadings = new WeakMap();
    for (const link of main.querySelectorAll('a[href*="files/"]')) {
      const path = new URL(link.href, document.baseURI).pathname;
      const match = path.match(/\/files\/([^/]+\/[^/]+)\.pdf$/i);
      if (!match || !records[match[1]]) continue;
      const record = records[match[1].replace(/ge(?=_br$|$)/, "ga")] || records[match[1]];
      const cell = link.closest?.("td");
      if (cell) {
        if (!cellReadings.has(cell)) cellReadings.set(cell, new Set());
        if (cellReadings.get(cell).has(record.id)) continue;
        cellReadings.get(cell).add(record.id);
      }
      const button = el("button", "Textus", "textus-button");
      button.type = "button";
      button.setAttribute("aria-haspopup", "dialog"); button.setAttribute("aria-controls", dialog.id);
      button.setAttribute("aria-expanded", "false");
      button.setAttribute("aria-label", `Textus: ${record.reading}, ${record.reference}${record.form ? ", " + record.form : ""}`);
      button.addEventListener("click", () => open(record, button));
      const reference = cell?.querySelector(`[data-textus-key="${record.id}"]`);
      (reference || link).after(button);
    }
  }).catch(() => { dialog.remove(); });
})();
