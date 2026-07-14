(function () {
    "use strict";

    document.querySelectorAll("[data-focus-stats-scope]").forEach((scope) => {
        const toggle = scope.querySelector("[data-focus-stats-toggle]");
        const statistics = [...scope.querySelectorAll("[data-focus-stat]")];
        if (!toggle || statistics.length === 0) return;

        const storageKey = `cocon-focus-statistics-${scope.dataset.focusStatsKey}`;

        function savedVisibility() {
            try {
                return sessionStorage.getItem(storageKey) === "true";
            } catch (error) {
                return false;
            }
        }

        function setVisibility(visible, { save = true } = {}) {
            statistics.forEach((statistic) => {
                statistic.hidden = !visible;
            });
            toggle.setAttribute("aria-pressed", String(visible));
            toggle.textContent = visible ? "Hide statistics" : "Show statistics";

            if (!save) return;
            try {
                sessionStorage.setItem(storageKey, String(visible));
            } catch (error) {
                // The button remains usable when browser storage is unavailable.
            }
        }

        toggle.addEventListener("click", () => {
            setVisibility(toggle.getAttribute("aria-pressed") !== "true");
        });

        setVisibility(savedVisibility(), { save: false });
    });
})();
