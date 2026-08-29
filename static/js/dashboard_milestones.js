(function () {
    const form = document.querySelector("[data-milestone-form]");

    if (form) {
        const kind = form.querySelector("[data-milestone-kind]");
        const target = form.querySelector("[data-milestone-target]");
        const targetLabel = form.querySelector("[data-milestone-date-label]");

        const syncDateRequirement = () => {
            const isDeadline = kind.value === "deadline";
            target.required = isDeadline;
            target.setAttribute(
                "aria-label",
                isDeadline ? "Deadline date and time" : "Optional date and time"
            );
            targetLabel.textContent = (
                isDeadline ? "Deadline date and time" : "Optional date and time"
            );
        };

        kind.addEventListener("change", syncDateRequirement);
        syncDateRequirement();
    }

    document.querySelectorAll("[data-milestone-priority]").forEach((select) => {
        select.addEventListener("change", () => {
            select.form.requestSubmit();
        });
    });

    const previewPanel = document.querySelector(
        '[data-dashboard-widget="milestones"][data-milestone-list-size]'
    );

    if (previewPanel) {
        const sizes = [
            { name: "compact", label: "Compact" },
            { name: "comfortable", label: "Medium" },
            { name: "large", label: "Large" },
        ];
        const storageKey = "cocon:milestone-preview-size";
        const sizeLabel = previewPanel.querySelector("[data-milestone-size-label]");
        const sizeButtons = Array.from(
            previewPanel.querySelectorAll("[data-milestone-size-change]")
        );
        let currentIndex = 0;

        try {
            const savedSize = window.localStorage.getItem(storageKey);
            const savedIndex = sizes.findIndex((size) => size.name === savedSize);
            if (savedIndex >= 0) currentIndex = savedIndex;
        } catch (error) {
            // The compact default still works when browser storage is unavailable.
        }

        const renderSize = () => {
            const currentSize = sizes[currentIndex];
            previewPanel.dataset.milestoneListSize = currentSize.name;
            if (sizeLabel) sizeLabel.textContent = currentSize.label;

            sizeButtons.forEach((button) => {
                const direction = Number(button.dataset.milestoneSizeChange);
                button.disabled = (
                    (direction < 0 && currentIndex === 0)
                    || (direction > 0 && currentIndex === sizes.length - 1)
                );
            });
        };

        sizeButtons.forEach((button) => {
            button.addEventListener("click", () => {
                const direction = Number(button.dataset.milestoneSizeChange);
                currentIndex = Math.max(
                    0,
                    Math.min(sizes.length - 1, currentIndex + direction)
                );
                renderSize();
                try {
                    window.localStorage.setItem(storageKey, sizes[currentIndex].name);
                } catch (error) {
                    // Resizing remains available for the current page visit.
                }
            });
        });

        renderSize();
    }
})();
