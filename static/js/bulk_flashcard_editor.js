(function () {
    "use strict";

    const form = document.getElementById("bulkFlashcardForm");
    if (!form) return;

    const source = document.getElementById("id_source_entries");
    const serialized = document.getElementById("id_entries");
    const previewReady = document.getElementById("id_preview_ready");
    const previewList = document.getElementById("bulkFlashcardPreviewList");
    const previewEmpty = document.getElementById("bulkFlashcardPreviewEmpty");
    const countLabel = document.getElementById("bulkFlashcardCount");
    const copyPromptButton = document.querySelector("[data-bulk-copy-prompt]");
    let rows = [];

    function parseLabel(line) {
        const cleaned = line.trim().replace(/^(?:[-*\u2022]\s*)?(?:\d+[.)]\s*)?/, "").replace(/^\*\*/, "").replace(/^__/, "");
        const match = cleaned.match(/^(question|q|answer|a|notes?|n)\s*(?::|\*\*:|__:|:\*\*|:__)\s*(.*)$/i);
        if (!match) return null;
        const label = match[1].toLowerCase();
        return {
            field: ["question", "q"].includes(label) ? "question" : (["answer", "a"].includes(label) ? "answer" : "notes"),
            value: match[2],
        };
    }

    function parseSource(value) {
        const parsed = [];
        let card = { question: "", answer: "", notes: "" };
        let activeField = null;

        function finishCard() {
            if (card.question.trim() || card.answer.trim() || card.notes.trim()) {
                parsed.push({ question: card.question.trim(), answer: card.answer.trim(), notes: card.notes.trim() });
            }
            card = { question: "", answer: "", notes: "" };
            activeField = null;
        }

        value.replace(/\r\n?/g, "\n").split("\n").forEach((line) => {
            const trimmed = line.trim();
            if (trimmed.startsWith("```")) return;
            if (trimmed === "---") {
                finishCard();
                return;
            }
            const labelled = parseLabel(line);
            if (labelled) {
                if (labelled.field === "question" && card.question.trim()) finishCard();
                activeField = labelled.field;
                card[activeField] = labelled.value;
                return;
            }
            if (activeField !== null) card[activeField] += `${card[activeField] ? "\n" : ""}${line}`;
        });
        finishCard();
        return parsed;
    }

    function serializeRows() {
        serialized.value = JSON.stringify(rows);
        previewReady.value = "1";
        countLabel.textContent = `${rows.length} ${rows.length === 1 ? "card" : "cards"}`;
        previewEmpty.hidden = rows.length > 0;
    }

    function createTextarea(labelText, value, field, row) {
        const wrapper = document.createElement("label");
        wrapper.className = `bulk-flashcard-field bulk-flashcard-${field}`;
        const label = document.createElement("span");
        label.textContent = labelText;
        const textarea = document.createElement("textarea");
        textarea.value = value;
        textarea.rows = field === "answer" ? 5 : 3;
        textarea.placeholder = field === "notes" ? "Optional notes for this card" : labelText;
        textarea.addEventListener("input", () => {
            row[field] = textarea.value;
            serializeRows();
        });
        wrapper.append(label, textarea);
        return wrapper;
    }

    function renderRows() {
        previewList.replaceChildren();
        rows.forEach((row, index) => {
            const item = document.createElement("article");
            item.className = "bulk-flashcard-preview-item";
            const itemHeader = document.createElement("header");
            const number = document.createElement("span");
            number.className = "bulk-preview-number";
            number.textContent = String(index + 1);
            const title = document.createElement("strong");
            title.textContent = `Flashcard ${index + 1}`;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "bulk-preview-remove";
            remove.textContent = "Remove";
            remove.addEventListener("click", () => {
                rows.splice(index, 1);
                renderRows();
            });
            itemHeader.append(number, title, remove);
            const fields = document.createElement("div");
            fields.className = "bulk-flashcard-fields";
            fields.append(
                createTextarea("Question", row.question, "question", row),
                createTextarea("Answer", row.answer, "answer", row),
                createTextarea("Notes (optional)", row.notes, "notes", row),
            );
            item.append(itemHeader, fields);
            previewList.appendChild(item);
        });
        serializeRows();
    }

    function rebuildFromSource() {
        rows = parseSource(source.value);
        renderRows();
    }

    source.addEventListener("input", rebuildFromSource);
    form.addEventListener("submit", (event) => {
        serializeRows();
        if (!rows.length) {
            event.preventDefault();
            source.focus();
        }
    });

    if (copyPromptButton) {
        copyPromptButton.addEventListener("click", async () => {
            const contextTitle = copyPromptButton.dataset.contextTitle || "this topic";
            const prompt = `Create a flashcard deck about ${contextTitle}. Use exactly this plain-text format for every card:\n\nQuestion: ...\nAnswer: ...\nNotes: ... (optional)\n---\n\nQuestions, answers, and notes may use multiple lines. Do not use a table. Do not number the cards. Keep factual explanations accurate and self-contained.`;
            try {
                await navigator.clipboard.writeText(prompt);
                copyPromptButton.textContent = "Prompt copied";
                window.setTimeout(() => { copyPromptButton.textContent = "Copy AI prompt"; }, 1800);
            } catch (error) {
                copyPromptButton.textContent = "Copy unavailable";
            }
        });
    }

    if (previewReady.value === "1" && serialized.value) {
        try {
            const savedRows = JSON.parse(serialized.value);
            rows = Array.isArray(savedRows) ? savedRows : [];
        } catch (error) {
            rows = parseSource(source.value);
        }
    } else {
        rows = parseSource(source.value);
    }
    renderRows();
})();
