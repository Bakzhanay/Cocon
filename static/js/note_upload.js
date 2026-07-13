document.addEventListener("DOMContentLoaded", () => {
    // Изолированные массивы для накопления файлов из разных папок
    let accumulatedImages = [];
    let accumulatedPdfs = [];

    const imageInput = document.getElementById("id_image");
    const imageQueueContainer = document.getElementById("imageQueueContainer");

    const pdfInput = document.getElementById("id_pdf");
    const pdfQueueContainer = document.getElementById("pdfQueueContainer");

    // Функция обновления встроенного свойства .files инпута перед отправкой
    function syncInputFiles(input, filesArray) {
        const dataTransfer = new DataTransfer();
        filesArray.forEach(file => dataTransfer.items.add(file));
        input.files = dataTransfer.files;
    }

    // --- ЛОГИКА ДЛЯ ИЗОБРАЖЕНИЙ ---
    if (imageInput && imageQueueContainer) {
        imageInput.addEventListener("change", function () {
            const newFiles = Array.from(this.files);
            accumulatedImages = accumulatedImages.concat(newFiles);

            syncInputFiles(imageInput, accumulatedImages);
            renderImageQueue();

            // Сбрасываем значение, чтобы инпут реагировал на повторный выбор одного и того же файла
            this.value = "";
        });
    }

    function renderImageQueue() {
        imageQueueContainer.innerHTML = "";
        accumulatedImages.forEach((file, index) => {
            // Основной контейнер теперь вертикальный, чтобы инпут был снизу
            const item = document.createElement("div");
            item.style.display = "flex";
            item.style.flexDirection = "column";
            item.style.marginBottom = "8px";
            item.style.background = "#f5f5f5";
            item.style.padding = "8px";
            item.style.borderRadius = "4px";

            // Верхняя строка: картинка, имя и кнопка удаления
            const topRow = document.createElement("div");
            topRow.style.display = "flex";
            topRow.style.alignItems = "center";
            topRow.style.width = "100%";

            const img = document.createElement("img");
            img.style.maxWidth = "50px";
            img.style.maxHeight = "50px";
            img.style.marginRight = "10px";
            img.style.borderRadius = "2px";

            const reader = new FileReader();
            reader.onload = function (e) {
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);

            const nameLabel = document.createElement("span");
            nameLabel.textContent = file.name;
            nameLabel.style.flexGrow = "1";
            nameLabel.style.fontSize = "0.85em";
            nameLabel.style.overflow = "hidden";
            nameLabel.style.textOverflow = "ellipsis";

            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.textContent = "✖";
            removeBtn.style.color = "red";
            removeBtn.style.border = "none";
            removeBtn.style.background = "none";
            removeBtn.style.cursor = "pointer";
            removeBtn.style.padding = "0 10px";

            removeBtn.addEventListener("click", () => {
                accumulatedImages.splice(index, 1);
                syncInputFiles(imageInput, accumulatedImages);
                renderImageQueue();
            });

            // Собираем верхнюю строку
            topRow.appendChild(img);
            topRow.appendChild(nameLabel);
            topRow.appendChild(removeBtn);

            // Поле для ввода подписи под конкретной картинкой
            const captionInput = document.createElement("input");
            captionInput.type = "text";
            captionInput.name = "new_captions"; // Имя для request.POST.getlist() во views.py
            captionInput.placeholder = "Добавить подпись под этой картинкой...";
            captionInput.value = file.customCaption || ""; // Восстанавливаем текст при перерендере

            // Стили для аккуратного отображения инпута
            captionInput.style.width = "100%";
            captionInput.style.marginTop = "6px";
            captionInput.style.padding = "4px 8px";
            captionInput.style.border = "1px solid #ccc";
            captionInput.style.borderRadius = "4px";
            captionInput.style.fontSize = "0.85em";
            captionInput.style.boxSizing = "border-box";

            // Перехватываем ввод и сохраняем его в объект файла
            captionInput.addEventListener("input", (e) => {
                file.customCaption = e.target.value;
            });

            // Добавляем элементы в главный контейнер карточки
            item.appendChild(topRow);
            item.appendChild(captionInput);

            imageQueueContainer.appendChild(item);
        });
    }

    // --- ЛОГИКА ДЛЯ PDF ---
    if (pdfInput && pdfQueueContainer) {
        pdfInput.addEventListener("change", function () {
            const newFiles = Array.from(this.files);
            accumulatedPdfs = accumulatedPdfs.concat(newFiles);

            syncInputFiles(pdfInput, accumulatedPdfs);
            renderPdfQueue();

            this.value = "";
        });
    }

    function renderPdfQueue() {
        pdfQueueContainer.innerHTML = "";
        accumulatedPdfs.forEach((file, index) => {
            const item = document.createElement("div");
            item.style.display = "flex";
            item.style.alignItems = "center";
            item.style.marginBottom = "8px";
            item.style.background = "#f5f5f5";
            item.style.padding = "6px";
            item.style.borderRadius = "4px";

            const icon = document.createElement("span");
            icon.textContent = "📄 ";
            icon.style.marginRight = "8px";

            const nameLabel = document.createElement("span");
            nameLabel.textContent = file.name;
            nameLabel.style.flexGrow = "1";
            nameLabel.style.minWidth = "0"; // Запрещает флексу раздуваться
            nameLabel.style.wordBreak = "break-all"; // Включает перенос длинных названий
            nameLabel.style.fontSize = "0.85em";

            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.textContent = "✖";
            removeBtn.style.color = "red";
            removeBtn.style.border = "none";
            removeBtn.style.background = "none";
            removeBtn.style.cursor = "pointer";
            removeBtn.style.padding = "0 10px";

            removeBtn.addEventListener("click", () => {
                accumulatedPdfs.splice(index, 1);
                syncInputFiles(pdfInput, accumulatedPdfs);
                renderPdfQueue();
            });

            item.appendChild(icon);
            item.appendChild(nameLabel);
            item.appendChild(removeBtn);
            pdfQueueContainer.appendChild(item);
        });
    }

    // Финальная принудительная синхронизация перед отправкой формы
    const mainForm = imageInput ? imageInput.closest("form") : null;
    if (mainForm) {
        mainForm.addEventListener("submit", () => {
            if (imageInput) syncInputFiles(imageInput, accumulatedImages);
            if (pdfInput) syncInputFiles(pdfInput, accumulatedPdfs);
        });
    }
});
