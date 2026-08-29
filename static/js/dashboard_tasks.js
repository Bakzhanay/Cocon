(function () {
    "use strict";

    function setupTaskForm(form) {
        const type = form.querySelector("[data-task-type]");
        const title = form.querySelector("[data-task-title]");
        const fields = form.querySelector("[data-study-task-fields]");
        const context = form.querySelector("[data-study-context]");
        const contextSearch = form.querySelector("[data-study-context-search]");
        const contextResults = form.querySelector("[data-study-context-results]");
        const minutes = form.querySelector("[data-task-minutes]");
        const activity = form.querySelector("[data-task-activity]");
        const submit = form.querySelector("[data-task-submit]");
        const contextOptions = Array.from(context.options)
            .filter((option) => option.value)
            .map((option) => ({ value: option.value, label: option.textContent.trim() }));

        function normalizeSearchText(value) {
            return value
                .toLocaleLowerCase()
                .normalize("NFD")
                .replace(/[\u0300-\u036f]/g, "")
                .trim();
        }

        function renderContextOptions() {
            const selectedValue = context.value;
            const searchTokens = normalizeSearchText(contextSearch.value)
                .split(/\s+/)
                .filter(Boolean);
            const matches = contextOptions.filter((option) => {
                const label = normalizeSearchText(option.label);
                return searchTokens.every((token) => label.includes(token));
            });

            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = matches.length
                ? "Choose what to study"
                : "No matching study items";
            context.replaceChildren(placeholder);

            matches.forEach((item) => {
                const option = document.createElement("option");
                option.value = item.value;
                option.textContent = item.label;
                context.append(option);
            });

            context.value = matches.some((item) => item.value === selectedValue)
                ? selectedValue
                : "";
            const noun = matches.length === 1 ? "item" : "items";
            contextResults.textContent = searchTokens.length
                ? `${matches.length} matching ${noun}`
                : `${matches.length} study ${noun}`;
        }

        function renderTaskType() {
            const isStudy = type.value === "study";
            fields.hidden = !isStudy;
            [contextSearch, context, minutes, activity].forEach((field) => {
                field.disabled = !isStudy;
            });
            context.required = isStudy;
            minutes.required = isStudy;
            title.required = !isStudy;
            title.placeholder = isStudy
                ? "Optional title — Cocon can name it"
                : "What needs to be done?";
            if (!form.matches("[data-task-edit-form]")) {
                submit.textContent = isStudy ? "Add plan" : "Add";
            }
        }

        contextSearch.addEventListener("input", renderContextOptions);
        type.addEventListener("change", renderTaskType);
        form.addEventListener("cocon:refresh-task-form", () => {
            renderContextOptions();
            renderTaskType();
        });
        renderContextOptions();
        renderTaskType();
    }

    document.querySelectorAll("[data-study-task-form]").forEach(setupTaskForm);

    const editDialog = document.getElementById("taskEditDialog");
    const editForm = editDialog?.querySelector("[data-task-edit-form]");
    if (editDialog && editForm) {
        const editType = editForm.querySelector("[data-task-type]");
        const editTitle = editForm.querySelector("[data-task-title]");
        const editDueDate = editForm.querySelector("[data-task-due-date]");
        const editPriority = editForm.querySelector("[data-task-priority]");
        const editContext = editForm.querySelector("[data-study-context]");
        const editContextSearch = editForm.querySelector("[data-study-context-search]");
        const editMinutes = editForm.querySelector("[data-task-minutes]");
        const editActivity = editForm.querySelector("[data-task-activity]");

        document.querySelectorAll("[data-edit-task]").forEach((button) => {
            button.addEventListener("click", () => {
                editForm.action = button.dataset.taskEditUrl;
                editType.value = button.dataset.taskType;
                editTitle.value = button.dataset.taskTitle;
                editDueDate.value = button.dataset.taskDueDate;
                editPriority.value = button.dataset.taskPriority;
                editContextSearch.value = "";
                editForm.dispatchEvent(new Event("cocon:refresh-task-form"));
                editContext.value = button.dataset.taskContext;
                editMinutes.value = button.dataset.taskMinutes;
                editActivity.value = button.dataset.taskActivity;
                editDialog.showModal();
                editTitle.focus();
            });
        });

        editDialog.querySelectorAll("[data-close-task-edit]").forEach((button) => {
            button.addEventListener("click", () => editDialog.close());
        });

        editDialog.addEventListener("click", (event) => {
            if (event.target === editDialog) editDialog.close();
        });
    }

    const completeDialog = document.getElementById("taskCompleteDialog");
    const completeForm = completeDialog?.querySelector("[data-task-complete-form]");
    if (completeDialog && completeForm) {
        const completeTitle = completeDialog.querySelector("[data-task-complete-title]");
        const completeSummary = completeDialog.querySelector("[data-task-complete-summary]");
        const completeNote = completeDialog.querySelector("[data-task-completion-note]");

        document.querySelectorAll("[data-complete-task]").forEach((button) => {
            button.addEventListener("click", () => {
                completeForm.action = button.dataset.taskCompleteUrl;
                completeTitle.textContent = button.dataset.taskTitle;
                completeSummary.textContent = button.dataset.taskSummary;
                completeNote.value = "";
                completeDialog.showModal();
                completeNote.focus();
            });
        });

        completeDialog.querySelectorAll("[data-close-task-complete]").forEach((button) => {
            button.addEventListener("click", () => completeDialog.close());
        });

        completeDialog.addEventListener("click", (event) => {
            if (event.target === completeDialog) completeDialog.close();
        });
    }

    window.addEventListener("cocon:task-progress", (event) => {
        const task = event.detail;
        if (!task?.id) return;
        const row = document.querySelector(`[data-task-row="${task.id}"]`);
        if (!row) return;

        const bar = row.querySelector("[data-task-progress-bar]");
        const progress = row.querySelector("[data-task-progress-label]");
        const completion = row.querySelector("[data-task-completion-label]");
        if (bar) bar.style.width = `${task.progress_percent}%`;
        if (progress) progress.textContent = `${task.focused_minutes} / ${task.target_minutes} min`;
        if (completion) {
            completion.textContent = task.completed
                ? "Completed automatically"
                : `${task.remaining_minutes} min remaining`;
        }

        if (task.completed) {
            row.classList.add("is-completed");
            const check = row.querySelector(".task-check");
            if (check) check.textContent = "✓";
            row.querySelector("[data-start-study-task]")?.remove();
            window.setTimeout(() => row.remove(), 450);
        }
    });
})();
