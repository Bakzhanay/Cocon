(() => {
    const panel = document.querySelector("[data-rhythm-panel]");
    if (!panel) return;

    const popover = panel.querySelector("[data-rhythm-popover]");
    const buttons = Array.from(panel.querySelectorAll("[data-rhythm-bucket]"));
    if (!popover || !buttons.length) return;

    let activeButton = null;
    let pinnedButton = null;
    let hideTimer = null;

    const clearHideTimer = () => {
        if (hideTimer) {
            window.clearTimeout(hideTimer);
            hideTimer = null;
        }
    };

    const positionPopover = (button) => {
        const panelRect = panel.getBoundingClientRect();
        const buttonRect = button.getBoundingClientRect();
        const panelPadding = 12;
        const popoverWidth = popover.offsetWidth;
        const popoverHeight = popover.offsetHeight;
        const buttonCenter = buttonRect.left - panelRect.left + (buttonRect.width / 2);
        const left = Math.max(
            panelPadding,
            Math.min(
                buttonCenter - (popoverWidth / 2),
                panel.clientWidth - popoverWidth - panelPadding,
            ),
        );
        const heading = panel.querySelector(".panel-heading");
        const minimumTop = (heading?.offsetHeight || 0) + 24;
        const aboveButton = buttonRect.top - panelRect.top - popoverHeight - 10;
        const belowValue = buttonRect.top - panelRect.top + 28;
        const top = aboveButton >= minimumTop ? aboveButton : belowValue;

        popover.style.left = `${left}px`;
        popover.style.top = `${Math.max(minimumTop, top)}px`;
    };

    const showBreakdown = (button) => {
        clearHideTimer();
        const templateId = button.dataset.breakdownTemplate;
        const template = templateId ? document.getElementById(templateId) : null;
        if (!(template instanceof HTMLTemplateElement)) return;

        if (activeButton && activeButton !== button) {
            activeButton.setAttribute("aria-expanded", "false");
        }
        popover.replaceChildren(template.content.cloneNode(true));
        popover.hidden = false;
        activeButton = button;
        button.setAttribute("aria-expanded", "true");
        positionPopover(button);
    };

    const closeBreakdown = () => {
        clearHideTimer();
        if (activeButton) {
            activeButton.setAttribute("aria-expanded", "false");
        }
        popover.hidden = true;
        popover.replaceChildren();
        activeButton = null;
        pinnedButton = null;
    };

    const scheduleClose = () => {
        clearHideTimer();
        hideTimer = window.setTimeout(() => {
            if (!pinnedButton && !popover.matches(":hover")) {
                closeBreakdown();
            }
        }, 120);
    };

    buttons.forEach((button) => {
        button.addEventListener("pointerenter", () => {
            if (!pinnedButton) showBreakdown(button);
        });
        button.addEventListener("pointerleave", () => {
            if (!pinnedButton) scheduleClose();
        });
        button.addEventListener("focus", () => {
            if (!pinnedButton) showBreakdown(button);
        });
        button.addEventListener("blur", () => {
            if (!pinnedButton) scheduleClose();
        });
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            if (pinnedButton === button) {
                closeBreakdown();
                return;
            }
            pinnedButton = button;
            showBreakdown(button);
        });
    });

    popover.addEventListener("pointerenter", clearHideTimer);
    popover.addEventListener("pointerleave", () => {
        if (!pinnedButton) scheduleClose();
    });
    popover.addEventListener("click", (event) => event.stopPropagation());

    document.addEventListener("click", closeBreakdown);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeBreakdown();
    });
    window.addEventListener("resize", () => {
        if (activeButton && !popover.hidden) positionPopover(activeButton);
    });
})();
