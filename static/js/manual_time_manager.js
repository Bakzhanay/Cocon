(function () {
    "use strict";

    const manager = document.getElementById("manual-focus-time");
    const openButton = document.querySelector("[data-open-manual-time]");
    if (!manager || !openButton) return;

    openButton.addEventListener("click", () => {
        manager.open = true;
        manager.scrollIntoView({ behavior: "smooth", block: "start" });
        window.setTimeout(() => {
            manager.querySelector("input")?.focus({ preventScroll: true });
        }, 350);
    });
})();
