(function () {
    const root = document.documentElement;
    const themeButton = document.getElementById("themeToggle");
    const stimulusButton = document.getElementById("stimulusToggle");
    if (!themeButton || !stimulusButton) return;

    function render() {
        const dark = root.classList.contains("dark-mode");
        const lowStimulus = root.classList.contains("low-stimulus");
        themeButton.setAttribute("aria-pressed", String(dark));
        stimulusButton.setAttribute("aria-pressed", String(lowStimulus));
        themeButton.title = dark ? "Use light mode" : "Use dark mode";
        stimulusButton.title = lowStimulus ? "Exit low-stimulus mode" : "Use low-stimulus mode";
        themeButton.classList.toggle("is-active", dark);
        stimulusButton.classList.toggle("is-active", lowStimulus);
    }

    themeButton.addEventListener("click", () => {
        const dark = root.classList.toggle("dark-mode");
        localStorage.setItem("cocon-theme", dark ? "dark" : "light");
        render();
    });

    stimulusButton.addEventListener("click", () => {
        const active = root.classList.toggle("low-stimulus");
        localStorage.setItem("cocon-low-stimulus", String(active));
        render();
    });

    render();
})();
