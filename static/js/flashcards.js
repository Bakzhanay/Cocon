document.querySelectorAll("[data-flashcard-reveal]").forEach((button) => {
    button.addEventListener("click", () => {
        const card = button.closest(".study-flashcard");
        const answer = card.querySelector(".flashcard-answer");
        const isOpen = answer.classList.toggle("is-open");
        answer.hidden = !isOpen;
        button.textContent = isOpen ? "Hide answer" : "Show answer";
    });
});
