function toggleTopic(event, button) {

    event.preventDefault();
    event.stopPropagation();

    const topicBlock = button.closest(".topic-block");
    const sectionList = topicBlock.querySelector(".section-list");
    const topicId = topicBlock.dataset.topic;

    const openedTopics =
        JSON.parse(localStorage.getItem("openedTopics")) || [];

    if (sectionList.style.display === "flex") {

        sectionList.style.display = "none";
        button.textContent = "▶";

        const updated = openedTopics.filter(id => id != topicId);

        localStorage.setItem(
            "openedTopics",
            JSON.stringify(updated)
        );

    } else {

        sectionList.style.display = "flex";
        button.textContent = "▼";

        if (!openedTopics.includes(topicId)) {

            openedTopics.push(topicId);

        }

        localStorage.setItem(
            "openedTopics",
            JSON.stringify(openedTopics)
        );

    }

}



function restoreOpenedTopics() {

    const openedTopics =
        JSON.parse(localStorage.getItem("openedTopics")) || [];

    document.querySelectorAll(".topic-block").forEach(topic => {

        const topicId = topic.dataset.topic;

        const list = topic.querySelector(".section-list");
        const button = topic.querySelector(".topic-toggle");

        if (openedTopics.includes(topicId)) {

            list.style.display = "flex";
            button.textContent = "▼";

        } else {

            list.style.display = "none";
            button.textContent = "▶";

        }

    });

}



function toggleMenu(event, button) {

    event.preventDefault();
    event.stopPropagation();

    document.querySelectorAll(".menu-dropdown").forEach(menu => {

        if (menu !== button.nextElementSibling) {

            menu.style.display = "none";

        }

    });

    const menu = button.nextElementSibling;

    menu.style.display =
        menu.style.display === "block"
            ? "none"
            : "block";

}



document.addEventListener("click", () => {

    document.querySelectorAll(".menu-dropdown").forEach(menu => {

        menu.style.display = "none";

    });

});



document.addEventListener("DOMContentLoaded", () => {

    restoreOpenedTopics();

    const sidebar = document.querySelector(".sidebar");
    const toggleButton = document.getElementById("sidebarToggle");
    const appLayout = document.querySelector(".app-layout");

    if (sidebar && toggleButton && appLayout) {

        const collapsed = localStorage.getItem("cocon-left-sidebar-collapsed") === "true";
        sidebar.classList.toggle("collapsed", collapsed);
        appLayout.classList.toggle("left-sidebar-is-collapsed", collapsed);

        toggleButton.addEventListener("click", () => {

            const isCollapsed = sidebar.classList.toggle("collapsed");
            appLayout.classList.toggle("left-sidebar-is-collapsed", isCollapsed);
            localStorage.setItem("cocon-left-sidebar-collapsed", String(isCollapsed));

        });

    }

});
