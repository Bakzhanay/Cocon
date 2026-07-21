(function () {
    "use strict";

    const startButton = document.getElementById("subjectSelectionStart");
    const toolbar = document.getElementById("subjectSelectionToolbar");
    const form = document.getElementById("bulkDeleteSubjectsForm");
    if (!startButton || !toolbar || !form) return;

    const scope = document.querySelector(".page-content");
    const cancelButton = document.getElementById("subjectSelectionCancel");
    const selectAll = document.getElementById("subjectSelectAll");
    const deleteButton = document.getElementById("subjectBulkDeleteButton");
    const countLabel = document.getElementById("subjectSelectionCount");
    const selectors = [...document.querySelectorAll("[data-subject-selector]")];
    const filterControls = document.querySelectorAll(
        "#subjectStatusFilter, #subjectColorFilter, #subjectOrderFilter, #subjectFilterReset",
    );

    function cardFor(selector) {
        return selector.closest("[data-subject-card]");
    }

    function visibleSelectors() {
        return selectors.filter((selector) => !cardFor(selector).hidden);
    }

    function selectedSelectors() {
        return selectors.filter((selector) => selector.checked);
    }

    function updateSelection() {
        const selected = selectedSelectors();
        const visible = visibleSelectors();
        const visibleSelected = visible.filter((selector) => selector.checked);
        countLabel.textContent = `${selected.length} selected`;
        deleteButton.disabled = selected.length === 0;
        selectAll.checked = visible.length > 0 && visibleSelected.length === visible.length;
        selectAll.indeterminate = visibleSelected.length > 0 && visibleSelected.length < visible.length;
    }

    function startSelection() {
        scope.classList.add("is-selecting-subjects");
        toolbar.hidden = false;
        startButton.hidden = true;
        updateSelection();
        const firstVisible = visibleSelectors()[0];
        if (firstVisible) firstVisible.focus();
    }

    function cancelSelection() {
        selectors.forEach((selector) => {
            selector.checked = false;
        });
        scope.classList.remove("is-selecting-subjects");
        toolbar.hidden = true;
        startButton.hidden = false;
        updateSelection();
        startButton.focus();
    }

    startButton.addEventListener("click", startSelection);
    cancelButton.addEventListener("click", cancelSelection);
    selectors.forEach((selector) => {
        selector.addEventListener("change", updateSelection);
    });
    selectAll.addEventListener("change", () => {
        visibleSelectors().forEach((selector) => {
            selector.checked = selectAll.checked;
        });
        updateSelection();
    });

    filterControls.forEach((control) => {
        control.addEventListener("change", () => {
            window.setTimeout(() => {
                selectors.forEach((selector) => {
                    if (cardFor(selector).hidden) selector.checked = false;
                });
                updateSelection();
            }, 0);
        });
        if (control.tagName === "BUTTON") {
            control.addEventListener("click", () => window.setTimeout(updateSelection, 0));
        }
    });

    form.addEventListener("submit", (event) => {
        const count = selectedSelectors().length;
        if (!count) {
            event.preventDefault();
            return;
        }
        const message = form.dataset.confirmMessage || "Delete the selected subjects?";
        if (!window.confirm(`${message}\n\n${count} selected.`)) {
            event.preventDefault();
        }
    });

    updateSelection();
})();
