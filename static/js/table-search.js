function wireTableSearch(inputId, containerSelector) {
    const input = document.getElementById(inputId);
    const container = document.querySelector(containerSelector);
    if (!input || !container) return;

    input.addEventListener('input', () => {
        const query = input.value.toLowerCase();
        container.querySelectorAll('table.table').forEach((table) => {
            let anyVisible = false;
            table.querySelectorAll('tbody tr').forEach((row) => {
                const match = row.textContent.toLowerCase().includes(query);
                row.style.display = match ? '' : 'none';
                if (match) anyVisible = true;
            });
            table.style.display = anyVisible ? '' : 'none';
            const heading = table.previousElementSibling;
            if (heading && (heading.tagName === 'H2' || heading.tagName === 'H3')) {
                heading.style.display = anyVisible ? '' : 'none';
            }
        });
    });
}
