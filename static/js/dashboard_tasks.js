(function () {
    "use strict";

    const form = document.querySelector("[data-study-task-form]");
    if (form) {
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
            submit.textContent = isStudy ? "Add plan" : "Add";
        }

        contextSearch.addEventListener("input", renderContextOptions);
        type.addEventListener("change", renderTaskType);
        renderContextOptions();
        renderTaskType();
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
        }
    });
})();
