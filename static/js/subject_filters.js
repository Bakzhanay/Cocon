(function () {
    "use strict";

    const filters = document.getElementById("subjectFilters");
    if (!filters) return;

    const statusSelect = document.getElementById("subjectStatusFilter");
    const colorSelect = document.getElementById("subjectColorFilter");
    const orderSelect = document.getElementById("subjectOrderFilter");
    const resetButton = document.getElementById("subjectFilterReset");
    const countLabel = document.getElementById("subjectFilterCount");
    const emptyState = document.getElementById("subjectFilterEmpty");
    const grid = document.querySelector(".subject-grid");
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
            if (validOption(orderSelect, saved.order)) orderSelect.value = saved.order;
        } catch (error) {
            // A blocked or manually edited session store should not break the page.
        }
    }

    function saveFilters() {
        try {
            sessionStorage.setItem(storageKey, JSON.stringify({
                status: statusSelect.value,
                color: colorSelect.value,
                order: orderSelect.value,
            }));
        } catch (error) {
            // Filtering still works when browser storage is unavailable.
        }
    }

    function cardLabel(count) {
        return count === 1 ? "card" : "cards";
    }

    function compareCardGroups(first, second) {
        const firstStatus = first.dataset.subjectStatus === "mastered" ? 1 : 0;
        const secondStatus = second.dataset.subjectStatus === "mastered" ? 1 : 0;
        if (firstStatus !== secondStatus) return firstStatus - secondStatus;

        const firstPinned = first.dataset.subjectPinned === "true" ? 0 : 1;
        const secondPinned = second.dataset.subjectPinned === "true" ? 0 : 1;
        return firstPinned - secondPinned;
    }

    function sortCards() {
        const order = orderSelect.value;
        const sortedCards = [...cards].sort((first, second) => {
            const groupOrder = compareCardGroups(first, second);
            if (groupOrder !== 0) return groupOrder;

            if (order === "alphabetical") {
                return first.dataset.subjectTitle.localeCompare(
                    second.dataset.subjectTitle,
                    undefined,
                    { numeric: true, sensitivity: "base" },
                );
            }

            return Number(first.dataset.subjectOrder) - Number(second.dataset.subjectOrder);
        });

        sortedCards.forEach((card) => grid.appendChild(card));
    }

    function applyFilters({ save = true } = {}) {
        const status = statusSelect.value;
        const color = colorSelect.value;
        let visibleCount = 0;

        sortCards();

        cards.forEach((card) => {
            const matchesStatus = status === "all" || card.dataset.subjectStatus === status;
            const matchesColor = color === "all" || card.dataset.subjectColor === color;
            const visible = matchesStatus && matchesColor;
            card.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        countLabel.textContent = `${visibleCount} of ${cards.length} ${cardLabel(cards.length)}`;
        emptyState.hidden = visibleCount !== 0;
        resetButton.hidden = status === "all" && color === "all" && orderSelect.value === "added";
        if (save) saveFilters();
    }

    statusSelect.addEventListener("change", () => applyFilters());
    colorSelect.addEventListener("change", () => applyFilters());
    orderSelect.addEventListener("change", () => applyFilters());
    resetButton.addEventListener("click", () => {
        statusSelect.value = "all";
        colorSelect.value = "all";
        orderSelect.value = "added";
        applyFilters();
        statusSelect.focus();
    });

    readSavedFilters();
    applyFilters({ save: false });
})();
