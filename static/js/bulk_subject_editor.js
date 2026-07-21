(function () {
    "use strict";

    const form = document.getElementById("bulkSubjectForm");
    if (!form) return;

    const source = document.getElementById("id_source_entries");
    const serialized = document.getElementById("id_entries");
    const previewReady = document.getElementById("id_preview_ready");
    const commonSubtitle = document.getElementById("id_common_subtitle");
    const previewList = document.getElementById("bulkPreviewList");
    const previewEmpty = document.getElementById("bulkPreviewEmpty");
    const countLabel = document.getElementById("bulkSubjectCount");
    const subtitleChoices = document.querySelectorAll("[data-common-subtitle]");
    const bulletPattern = /^(?:[-*\u2022\u25e6\u25cb\u25aa\u2023\u203a]|\d+[.)])\s*/;
    let rows = [];

    function cleanPrefix(value) {
        return value
            .trim()
            .replace(bulletPattern, "")
            .replace(/^\[[ xX]\]\s*/, "")
            .trim();
    }

    function stripFormatting(value) {
        let result = value.trim().replace(/^#+\s*/, "");
        ["**", "__", "`"].forEach((marker) => {
            if (result.startsWith(marker) && result.endsWith(marker)) {
                result = result.slice(marker.length, -marker.length).trim();
            }
        });
        return result;
    }

    function parseLines(value) {
        let currentSubtitle = "";
        const parsed = [];
        const lines = value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

        lines.forEach((trimmed, index) => {
            const isBullet = bulletPattern.test(trimmed);
            const nextIsBullet = index + 1 < lines.length && bulletPattern.test(lines[index + 1]);
            const explicitHeading = trimmed.endsWith(":")
                || trimmed.startsWith("#")
                || (trimmed.startsWith("**") && trimmed.endsWith("**"))
                || (trimmed.startsWith("__") && trimmed.endsWith("__"));

            if (!trimmed.includes("|") && (explicitHeading || (!isBullet && nextIsBullet))) {
                currentSubtitle = stripFormatting(cleanPrefix(trimmed.replace(/:$/, "")));
                return;
            }

            const cleaned = cleanPrefix(trimmed);
            if (!cleaned) return;
            const separatorIndex = cleaned.indexOf("|");
            const title = separatorIndex >= 0
                ? cleaned.slice(0, separatorIndex).trim()
                : cleaned;
            const subtitle = separatorIndex >= 0
                ? cleaned.slice(separatorIndex + 1).trim()
                : currentSubtitle;
            if (title) parsed.push({
                title: stripFormatting(title),
                subtitle: stripFormatting(subtitle),
            });
        });

        return parsed;
    }

    function subjectLabel(count) {
        return count === 1 ? "subject" : "subjects";
    }

    function serializeRows() {
        const validRows = rows
            .filter((row) => row.title.trim());
        serialized.value = validRows.map((row) => {
                const title = row.title.trim();
                const subtitle = row.subtitle.trim();
                return subtitle ? `${title} | ${subtitle}` : title;
            })
            .join("\n");
        previewReady.value = "1";
        countLabel.textContent = `${validRows.length} ${subjectLabel(validRows.length)}`;
        previewEmpty.hidden = rows.length !== 0;
    }

    function createField(labelText, value, className, onInput) {
        const wrapper = document.createElement("label");
        wrapper.className = className;
        const label = document.createElement("span");
        label.textContent = labelText;
        const input = document.createElement("input");
        input.type = "text";
        input.value = value;
        input.maxLength = labelText === "Subject name" ? 100 : 240;
        input.autocomplete = "off";
        if (labelText !== "Subject name") {
            input.setAttribute("list", "subjectSubtitleHistory");
            input.placeholder = commonSubtitle.value.trim()
                ? `Optional — common: ${commonSubtitle.value.trim()}`
                : "Optional subtitle";
        }
        input.addEventListener("input", () => onInput(input.value));
        wrapper.append(label, input);
        return wrapper;
    }

    function renderRows() {
        previewList.replaceChildren();

        rows.forEach((row, index) => {
            const item = document.createElement("article");
            item.className = "bulk-preview-item";

            const number = document.createElement("span");
            number.className = "bulk-preview-number";
            number.textContent = String(index + 1);

            const fields = document.createElement("div");
            fields.className = "bulk-preview-fields";
            fields.append(
                createField("Subject name", row.title, "bulk-preview-title", (value) => {
                    row.title = value;
                    serializeRows();
                }),
                createField("Individual subtitle", row.subtitle, "bulk-preview-subtitle", (value) => {
                    row.subtitle = value;
                    serializeRows();
                }),
            );

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className = "bulk-preview-remove";
            removeButton.textContent = "Remove";
            removeButton.setAttribute("aria-label", `Remove ${row.title || `subject ${index + 1}`}`);
            removeButton.addEventListener("click", () => {
                rows.splice(index, 1);
                renderRows();
            });

            item.append(number, fields, removeButton);
            previewList.appendChild(item);
        });

        serializeRows();
    }

    function rebuildFromSource() {
        rows = parseLines(source.value);
        renderRows();
    }

    source.addEventListener("input", rebuildFromSource);
    commonSubtitle.addEventListener("input", renderRows);
    subtitleChoices.forEach((button) => {
        button.addEventListener("click", () => {
            commonSubtitle.value = button.dataset.commonSubtitle || "";
            commonSubtitle.focus();
            renderRows();
        });
    });

    form.addEventListener("submit", (event) => {
        serializeRows();
        if (!serialized.value.trim()) {
            event.preventDefault();
            source.focus();
        }
    });

    rows = parseLines(serialized.value || source.value);
    renderRows();
})();
