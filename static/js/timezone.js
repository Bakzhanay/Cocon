(function () {
    const syncUrl = document.body.dataset.timezoneSyncUrl;
    const timezoneName = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;

    if (!syncUrl || !timezoneName || !csrfToken) return;

    const body = new URLSearchParams({ timezone: timezoneName });
    fetch(syncUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "X-CSRFToken": csrfToken,
        },
        body,
        credentials: "same-origin",
    })
        .then((response) => response.ok ? response.json() : null)
        .then((data) => {
            if (data?.changed && document.querySelector("[data-timezone-dependent]")) {
                window.location.reload();
            }
        })
        .catch(() => {
            // UTC remains the safe fallback if browser timezone detection is unavailable.
        });
}());
