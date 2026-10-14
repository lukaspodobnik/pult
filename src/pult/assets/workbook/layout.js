() => {
    // A short answer uses the remaining line; long prompts wrap the line below.
    for (const answer of document.querySelectorAll('.answer-lines')) {
        const prompt = answer.previousElementSibling;
        if (prompt?.tagName !== 'P' || prompt.classList.contains('subtask-label') ||
            prompt.querySelector('img, br')) continue;
        const row = document.createElement('div');
        row.className = 'answer-inline-row';
        prompt.before(row);
        row.append(prompt, answer.firstElementChild);
    }
    // Explicit rows let Chromium paginate grids without splitting a subtask or
    // its answer field. Reduce the requested columns if formulas do not fit.
    for (const grid of [...document.querySelectorAll('.subtasks')].reverse()) {
        const items = [...grid.children].filter(e => e.classList.contains('subtask'));
        if (!items.length) continue;
        let columns = Math.min(Number(grid.dataset.columns), items.length);
        const overflow = () => items.some(item => {
            const content = item.querySelector(':scope > .subtask-content');
            return content.scrollWidth > content.clientWidth + 1;
        });
        const place = count => {
            grid.classList.add('print-rows');
            grid.replaceChildren();
            for (let i = 0; i < items.length; i += count) {
                const row = document.createElement('div');
                row.className = 'subtask-row';
                row.style.setProperty('--columns', count);
                row.append(...items.slice(i, i + count));
                grid.append(row);
            }
        };
        place(columns);
        while (columns > 1 && overflow()) place(--columns);
    }
    // Thin gradient backgrounds disappear in some Chromium PDF versions.
    // Real SVG paths remain crisp, consistently spaced and printable.
    const mm = 96 / 25.4;
    for (const field of document.querySelectorAll('.answer-grid')) {
        const width = Math.floor(field.getBoundingClientRect().width / mm / 5) * 5;
        const height = Number(getComputedStyle(field).getPropertyValue('--rows')) * 5;
        field.style.width = `${width}mm`;
        field.style.marginLeft = field.style.marginRight = 'auto';
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        const path = document.createElementNS(svg.namespaceURI, 'path');
        const half = 0.3 * 25.4 / 72 / 2;
        const segments = [`M${half},${half}H${width-half}V${height-half}H${half}Z`];
        for (let x = 5; x < width; x += 5) segments.push(`M${x},0V${height}`);
        for (let y = 5; y < height; y += 5) segments.push(`M0,${y}H${width}`);
        path.setAttribute('d', segments.join(' '));
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', '#D2D7DD');
        path.setAttribute('stroke-width', String(half * 2));
        svg.append(path);
        field.append(svg);
    }
    const pageHeight = 251 * 96 / 25.4;
    for (const task of document.querySelectorAll('.exercise')) {
        if (task.getBoundingClientRect().height > pageHeight)
            task.classList.add('long-exercise');
    }
    for (const field of document.querySelectorAll('.answer-area, .subtask-row')) {
        if (field.getBoundingClientRect().height > pageHeight - 35) {
            const title = field.closest('.exercise').querySelector('h2').textContent;
            return `${title}: Der Antwortbereich oder eine Teilaufgabe ist zu hoch für eine Seite. Bitte export.zeilen reduzieren oder die Teilaufgabe kürzen.`;
        }
    }
    for (const content of document.querySelectorAll('.subtask-content, .exercise-body')) {
        if (content.scrollWidth > content.clientWidth + 2) {
            const title = content.closest('.exercise').querySelector('h2').textContent;
            return `${title}: Ein Inhalt ist zu breit für das Blatt. Bitte lange Formeln oder Tabellen aufteilen.`;
        }
    }
    return null;
}
