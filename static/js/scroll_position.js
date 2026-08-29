(function () {
    const storageKey = "cocon:post-scroll-position";
    const maxAgeMs = 2 * 60 * 1000;

    function findAnchor(anchorName) {
        if (!anchorName) {
            return null;
        }

        return Array.from(document.querySelectorAll("[data-scroll-anchor]")).find(
            (element) => element.dataset.scrollAnchor === anchorName
        ) || null;
    }

    function restoreScrollPosition() {
        let savedPosition;

        try {
            savedPosition = JSON.parse(sessionStorage.getItem(storageKey));
        } catch (error) {
            sessionStorage.removeItem(storageKey);
            return;
        }

        if (!savedPosition) {
            return;
        }

        sessionStorage.removeItem(storageKey);

        const isFresh = Date.now() - savedPosition.savedAt < maxAgeMs;
        const isSamePage = (
            savedPosition.pathname === window.location.pathname
            && savedPosition.search === window.location.search
        );

        if (!isFresh || !isSamePage) {
            return;
        }

        const anchor = findAnchor(savedPosition.anchor);
        let targetTop = savedPosition.scrollY;

        if (anchor && Number.isFinite(savedPosition.anchorOffset)) {
            targetTop = (
                window.scrollY
                + anchor.getBoundingClientRect().top
                - savedPosition.anchorOffset
            );
        }

        window.scrollTo({
            top: Math.max(0, targetTop),
            left: 0,
            behavior: "auto",
        });
    }

    document.addEventListener("submit", (event) => {
        const form = event.target.closest("form");

        if (
            !form
            || form.method.toLowerCase() !== "post"
            || form.hasAttribute("data-no-scroll-restore")
        ) {
            return;
        }

        const anchor = form.closest("[data-scroll-anchor]");
        const savedPosition = {
            pathname: window.location.pathname,
            search: window.location.search,
            scrollY: window.scrollY,
            savedAt: Date.now(),
        };

        if (anchor) {
            savedPosition.anchor = anchor.dataset.scrollAnchor;
            savedPosition.anchorOffset = anchor.getBoundingClientRect().top;
        }

        try {
            sessionStorage.setItem(storageKey, JSON.stringify(savedPosition));
        } catch (error) {
            // A blocked sessionStorage should not prevent the form from saving.
        }
    }, true);

    const restoreAfterLayout = () => {
        window.requestAnimationFrame(() => {
            window.requestAnimationFrame(restoreScrollPosition);
        });
    };

    if (document.readyState === "complete") {
        restoreAfterLayout();
    } else {
        window.addEventListener("load", restoreAfterLayout, { once: true });
    }
})();
