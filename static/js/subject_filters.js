(function () {
    "use strict";

    const filters = document.getElementById("subjectFilters");
    if (!filters) return;

    const statusSelect = document.getElementById("subjectStatusFilter");
    const colorSelect = document.getElementById("subjectColorFilter");
    const resetButton = document.getElementById("subjectFilterReset");
    const countLabel = document.getElementById("subjectFilterCount");
    const emptyState = document.getElementById("subjectFilterEmpty");
    const cards = [...document.querySelectorAll("[data-subject-card]")];
    const storageKey = `cocon-subject-filters-${filters.dataset.sectionId}`;

    function validOption(select, value) {
        return [...select.options].some((option) => option.value === value);
    }

    function readSavedFilters() {
        try {
            const saved = JSON.parse(sessionStorage.getItem(storageKey));
            if (!saved || typeof saved !== "object") return;
            if (validOption(statusSelect, saved.status)) statusSelect.value = saved.status;
            if (validOption(colorSelect, saved.color)) colorSelect.value = saved.color;
        } catch (error) {
            // A blocked or manually edited session store should not break the page.
        }
    }

    function saveFilters() {
        try {
            sessionStorage.setItem(storageKey, JSON.stringify({
                status: statusSelect.value,
                color: colorSelect.value,
            }));
        } catch (error) {
            // Filtering still works when browser storage is unavailable.
        }
    }

    function cardLabel(count) {
        return count === 1 ? "card" : "cards";
    }

    function applyFilters({ save = true } = {}) {
        const status = statusSelect.value;
        const color = colorSelect.value;
        let visibleCount = 0;

        cards.forEach((card) => {
            const matchesStatus = status === "all" || card.dataset.subjectStatus === status;
            const matchesColor = color === "all" || card.dataset.subjectColor === color;
            const visible = matchesStatus && matchesColor;
            card.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        countLabel.textContent = `${visibleCount} of ${cards.length} ${cardLabel(cards.length)}`;
        emptyState.hidden = visibleCount !== 0;
        resetButton.hidden = status === "all" && color === "all";
        if (save) saveFilters();
    }

    statusSelect.addEventListener("change", () => applyFilters());
    colorSelect.addEventListener("change", () => applyFilters());
    resetButton.addEventListener("click", () => {
        statusSelect.value = "all";
        colorSelect.value = "all";
        applyFilters();
        statusSelect.focus();
    });

    readSavedFilters();
    applyFilters({ save: false });
})();
