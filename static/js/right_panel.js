(function () {
    "use strict";

    const panel = document.getElementById("rightSidebar");
    if (!panel) return;

    const appLayout = document.querySelector(".app-layout");
    const learningSidebar = document.querySelector(".sidebar");
    const panelToggle = document.getElementById("rightSidebarToggle");
    const userIdNode = document.getElementById("studyflow-user-id");
    const userId = userIdNode ? JSON.parse(userIdNode.textContent) : "guest";
    const storageKey = `studyflow-pomodoro-v1-${userId}`;
    const activityStorageKey = `studyflow-activity-v1-${userId}`;
    const soundStorageKey = `studyflow-sound-v1-${userId}`;

    const timerDisplay = document.getElementById("timerDisplay");
    const timerDial = document.getElementById("timerDial");
    const timerPhase = document.getElementById("timerPhase");
    const timerStatus = document.getElementById("timerStatus");
    const timerModeLabel = document.getElementById("timerModeLabel");
    const timerMessage = document.getElementById("timerMessage");
    const startButton = document.getElementById("timerStart");
    const pauseButton = document.getElementById("timerPause");
    const resetButton = document.getElementById("timerReset");
    const studyChoices = document.getElementById("studyDurationChoices");
    const breakChoices = document.getElementById("breakDurationChoices");

    const defaultState = {
        version: 1,
        studyMinutes: 25,
        breakMinutes: 5,
        phase: "study",
        remaining: 25 * 60,
        running: false,
        paused: false,
        endAt: null,
        sessionId: null,
        pausedAt: null,
        pausedSeconds: 0,
    };

    let state = loadState();
    let lastAlarmSecond = null;
    let completingPhase = false;
    let sessionRequestNonce = 0;
    let pendingSessionPromise = null;
    let sidebarCollapsedBeforeFocus = null;

    function loadState() {
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            if (!saved || saved.version !== 1) return { ...defaultState };

            const validStudy = [15, 25, 50, 90].includes(Number(saved.studyMinutes));
            const validBreak = [0, 5, 10, 15, 20, 25].includes(Number(saved.breakMinutes));
            const restored = {
                ...defaultState,
                ...saved,
                studyMinutes: validStudy ? Number(saved.studyMinutes) : 25,
                breakMinutes: validBreak ? Number(saved.breakMinutes) : 5,
                phase: saved.phase === "break" ? "break" : "study",
            };

            if (restored.running && restored.endAt) {
                restored.remaining = Math.max(0, Math.ceil((restored.endAt - Date.now()) / 1000));
            }

            return restored;
        } catch (error) {
            return { ...defaultState };
        }
    }

    function saveState() {
        localStorage.setItem(storageKey, JSON.stringify(state));
    }

    function formatTime(seconds) {
        const safeSeconds = Math.max(0, Math.ceil(seconds));
        const minutes = Math.floor(safeSeconds / 60);
        const remainder = safeSeconds % 60;
        return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
    }

    function phaseTotalSeconds() {
        return (state.phase === "study" ? state.studyMinutes : state.breakMinutes) * 60;
    }

    function renderTimer() {
        const total = Math.max(1, phaseTotalSeconds());
        const elapsedRatio = Math.min(1, Math.max(0, (total - state.remaining) / total));
        timerDisplay.textContent = formatTime(state.remaining);
        timerDial.style.setProperty("--timer-progress", `${elapsedRatio * 360}deg`);
        timerModeLabel.textContent = state.phase === "study" ? "Study" : "Break";

        timerStatus.className = "timer-status";
        if (state.running && state.phase === "study") {
            timerPhase.textContent = "Studying now";
            timerStatus.textContent = "Studying";
            timerStatus.classList.add("is-studying");
        } else if (state.running && state.phase === "break") {
            timerPhase.textContent = "Time to recharge";
            timerStatus.textContent = "Break";
            timerStatus.classList.add("is-break");
        } else if (state.paused) {
            timerPhase.textContent = state.phase === "study" ? "Study paused" : "Break paused";
            timerStatus.textContent = "Paused";
            timerStatus.classList.add("is-paused");
        } else {
            timerPhase.textContent = state.phase === "study" ? "Ready to focus" : "Break ready";
            timerStatus.textContent = "Ready";
            timerStatus.classList.add("is-ready");
        }

        startButton.textContent = state.paused ? "Resume" : "Start";
        startButton.disabled = state.running;
        pauseButton.disabled = !state.running;

        const settingsLocked = state.running || state.paused;
        [...studyChoices.querySelectorAll("button"), ...breakChoices.querySelectorAll("button")]
            .forEach((button) => { button.disabled = settingsLocked; });

        studyChoices.querySelectorAll("button").forEach((button) => {
            button.classList.toggle("is-selected", Number(button.dataset.minutes) === state.studyMinutes);
        });
        breakChoices.querySelectorAll("button").forEach((button) => {
            button.classList.toggle("is-selected", Number(button.dataset.minutes) === state.breakMinutes);
        });
    }

    function setMessage(message) {
        timerMessage.textContent = message || "";
    }

    function getCookie(name) {
        const cookie = document.cookie
            .split(";")
            .map((item) => item.trim())
            .find((item) => item.startsWith(`${name}=`));
        return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
    }

    async function postJSON(url, payload) {
        const response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(payload),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || "The session could not be saved.");
        return data;
    }

    function contextValue(value) {
        if (value === undefined || value === null || value === "" || value === "null" || value === "None") return null;
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function currentStudyContext() {
        const context = typeof currentContext === "object" && currentContext ? currentContext : {};
        return {
            topic_id: contextValue(context.topic_id),
            subject_id: contextValue(context.subject_id),
            section_id: contextValue(context.section_id),
            activity_type: context.activity_type || "general",
        };
    }

    async function createStudySession() {
        if (state.phase !== "study" || state.sessionId || pendingSessionPromise) return state.sessionId;

        const nonce = ++sessionRequestNonce;
        const payload = {
            ...currentStudyContext(),
            planned_duration_seconds: state.studyMinutes * 60,
        };

        pendingSessionPromise = postJSON("/study/start/", payload)
            .then(async (data) => {
                if (nonce !== sessionRequestNonce || state.phase !== "study" || (!state.running && !state.paused && !completingPhase)) {
                    await postJSON("/study/cancel/", { session_id: data.session_id }).catch(() => {});
                    return null;
                }
                state.sessionId = data.session_id;
                saveState();
                setMessage("");
                return data.session_id;
            })
            .catch((error) => {
                setMessage(error.message);
                return null;
            })
            .finally(() => {
                pendingSessionPromise = null;
            });

        return pendingSessionPromise;
    }

    async function finishStudySession() {
        if (pendingSessionPromise) await pendingSessionPromise;
        const sessionId = state.sessionId;
        state.sessionId = null;
        saveState();
        if (!sessionId) return false;

        try {
            await postJSON("/study/stop/", {
                session_id: sessionId,
                duration_seconds: state.studyMinutes * 60,
                paused_seconds: state.pausedSeconds || 0,
            });
            setMessage("");
            return true;
        } catch (error) {
            setMessage(error.message);
            return false;
        }
    }

    async function cancelStudySession() {
        const sessionId = state.sessionId;
        state.sessionId = null;
        sessionRequestNonce += 1;
        saveState();
        if (!sessionId) return;
        await postJSON("/study/cancel/", { session_id: sessionId }).catch(() => {});
    }

    function startTimer() {
        ensureAudioContext();
        if (state.running) return;
        if (state.remaining <= 0) state.remaining = phaseTotalSeconds();

        if (state.paused && state.pausedAt) {
            state.pausedSeconds += Math.max(0, Math.round((Date.now() - state.pausedAt) / 1000));
        }

        state.running = true;
        state.paused = false;
        state.pausedAt = null;
        state.endAt = Date.now() + state.remaining * 1000;
        lastAlarmSecond = null;
        setMessage("");
        saveState();
        renderTimer();

        if (state.phase === "study" && !state.sessionId) createStudySession();
        resumeSelectedSound();
    }

    function pauseTimer() {
        if (!state.running) return;
        state.remaining = Math.max(0, Math.ceil((state.endAt - Date.now()) / 1000));
        state.running = false;
        state.paused = true;
        state.pausedAt = Date.now();
        state.endAt = null;
        saveState();
        renderTimer();
    }

    async function resetTimer() {
        const wasStudy = state.phase === "study";
        state.running = false;
        state.paused = false;
        state.phase = "study";
        state.remaining = state.studyMinutes * 60;
        state.endAt = null;
        state.pausedAt = null;
        state.pausedSeconds = 0;
        lastAlarmSecond = null;
        saveState();
        renderTimer();
        setMessage("");
        if (wasStudy || state.sessionId) await cancelStudySession();
    }

    function selectDuration(container, type) {
        container.addEventListener("click", (event) => {
            const button = event.target.closest("button[data-minutes]");
            if (!button || button.disabled) return;
            const minutes = Number(button.dataset.minutes);

            if (type === "study") {
                state.studyMinutes = minutes;
                if (state.phase === "study") state.remaining = minutes * 60;
            } else {
                state.breakMinutes = minutes;
                if (state.phase === "break") state.remaining = minutes * 60;
            }
            saveState();
            renderTimer();
        });
    }

    function tick() {
        if (!state.running || completingPhase) return;
        const remaining = Math.max(0, Math.ceil((state.endAt - Date.now()) / 1000));

        if (remaining !== state.remaining) {
            state.remaining = remaining;
            if (remaining <= 3 && remaining > 0 && lastAlarmSecond !== remaining) {
                playDing(remaining);
                lastAlarmSecond = remaining;
            }
            saveState();
            renderTimer();
        }

        if (remaining === 0) completeCurrentPhase();
    }

    async function completeCurrentPhase() {
        if (completingPhase) return;
        completingPhase = true;
        state.running = false;
        state.paused = false;
        state.endAt = null;
        playFinishSound();

        if (state.phase === "study") {
            await finishStudySession();
            recordLocalCompletion();
            await loadCalendarActivity();

            if (state.breakMinutes > 0) {
                state.phase = "break";
                state.remaining = state.breakMinutes * 60;
                state.running = true;
                state.endAt = Date.now() + state.remaining * 1000;
                lastAlarmSecond = null;
            } else {
                state.phase = "study";
                state.remaining = state.studyMinutes * 60;
                state.pausedSeconds = 0;
            }
        } else {
            state.phase = "study";
            state.remaining = state.studyMinutes * 60;
            state.pausedSeconds = 0;
            setMessage("Break complete — ready for another focus session.");
        }

        saveState();
        renderTimer();
        completingPhase = false;
    }

    // Web Audio keeps the timer self-contained and avoids external media dependencies.
    let audioContext = null;
    let activeSoundNodes = [];
    let activeSoundTimers = [];
    let soundPrefs = loadSoundPrefs();

    function loadSoundPrefs() {
        try {
            return { sound: "none", volume: 32, muted: false, ...JSON.parse(localStorage.getItem(soundStorageKey)) };
        } catch (error) {
            return { sound: "none", volume: 32, muted: false };
        }
    }

    function saveSoundPrefs() {
        localStorage.setItem(soundStorageKey, JSON.stringify(soundPrefs));
    }

    function ensureAudioContext() {
        if (!audioContext) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextClass) return null;
            audioContext = new AudioContextClass();
        }
        if (audioContext.state === "suspended") audioContext.resume();
        return audioContext;
    }

    function playDing(step) {
        const context = ensureAudioContext();
        if (!context) return;
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        const now = context.currentTime;
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(740 + (3 - step) * 90, now);
        gain.gain.setValueAtTime(.0001, now);
        gain.gain.exponentialRampToValueAtTime(.22, now + .012);
        gain.gain.exponentialRampToValueAtTime(.0001, now + .2);
        oscillator.connect(gain).connect(context.destination);
        oscillator.start(now);
        oscillator.stop(now + .22);
    }

    function playFinishSound() {
        const context = ensureAudioContext();
        if (!context) return;
        const now = context.currentTime;
        [659.25, 783.99, 987.77].forEach((frequency, index) => {
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            const start = now + index * .15;
            oscillator.type = index === 2 ? "triangle" : "sine";
            oscillator.frequency.setValueAtTime(frequency, start);
            gain.gain.setValueAtTime(.0001, start);
            gain.gain.exponentialRampToValueAtTime(.13, start + .018);
            gain.gain.exponentialRampToValueAtTime(.0001, start + .72);
            oscillator.connect(gain).connect(context.destination);
            oscillator.start(start);
            oscillator.stop(start + .75);
        });
    }

    function makeNoiseBuffer(kind) {
        const context = audioContext;
        const length = context.sampleRate * 4;
        const buffer = context.createBuffer(1, length, context.sampleRate);
        const output = buffer.getChannelData(0);
        let brown = 0;
        let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;

        for (let i = 0; i < length; i += 1) {
            const white = Math.random() * 2 - 1;
            if (kind === "brown") {
                brown = (brown + .02 * white) / 1.02;
                output[i] = brown * 3.5;
            } else if (kind === "pink") {
                b0 = .99886 * b0 + white * .0555179;
                b1 = .99332 * b1 + white * .0750759;
                b2 = .969 * b2 + white * .153852;
                b3 = .8665 * b3 + white * .3104856;
                b4 = .55 * b4 + white * .5329522;
                b5 = -.7616 * b5 - white * .016898;
                output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * .5362) * .11;
                b6 = white * .115926;
            } else {
                output[i] = white;
            }
        }
        return buffer;
    }

    function stopBackgroundSound() {
        activeSoundTimers.forEach((timer) => window.clearInterval(timer));
        activeSoundTimers = [];
        activeSoundNodes.forEach((node) => {
            try { if (typeof node.stop === "function") node.stop(); } catch (error) { /* already stopped */ }
            try { node.disconnect(); } catch (error) { /* already disconnected */ }
        });
        activeSoundNodes = [];
    }

    function addAmbientDetails(profile, volume) {
        const context = audioContext;
        const scheduleChirp = (frequency, length, delay) => {
            const timer = window.setInterval(() => {
                if (!audioContext || soundPrefs.muted) return;
                const oscillator = context.createOscillator();
                const gain = context.createGain();
                const now = context.currentTime;
                oscillator.type = "sine";
                oscillator.frequency.setValueAtTime(frequency, now);
                oscillator.frequency.exponentialRampToValueAtTime(frequency * 1.35, now + length);
                gain.gain.setValueAtTime(.0001, now);
                gain.gain.exponentialRampToValueAtTime(.055 * volume, now + .018);
                gain.gain.exponentialRampToValueAtTime(.0001, now + length);
                oscillator.connect(gain).connect(context.destination);
                oscillator.start(now);
                oscillator.stop(now + length + .02);
            }, delay);
            activeSoundTimers.push(timer);
        };

        if (profile === "forest") scheduleChirp(1450, .38, 4200);
        if (profile === "night") scheduleChirp(3900, .16, 2600);
        if (profile === "fireplace") {
            const crackleBuffer = makeNoiseBuffer("white");
            const timer = window.setInterval(() => {
                const source = context.createBufferSource();
                const gain = context.createGain();
                const filter = context.createBiquadFilter();
                source.buffer = crackleBuffer;
                filter.type = "highpass";
                filter.frequency.value = 1700 + Math.random() * 1700;
                const now = context.currentTime;
                gain.gain.setValueAtTime(.0001, now);
                gain.gain.exponentialRampToValueAtTime((.02 + Math.random() * .04) * volume, now + .008);
                gain.gain.exponentialRampToValueAtTime(.0001, now + .07);
                source.connect(filter).connect(gain).connect(context.destination);
                source.start(now);
                source.stop(now + .08);
            }, 620);
            activeSoundTimers.push(timer);
        }
        if (profile === "cafe") {
            const hum = context.createOscillator();
            const humGain = context.createGain();
            hum.type = "sine";
            hum.frequency.value = 118;
            humGain.gain.value = .016 * volume;
            hum.connect(humGain).connect(context.destination);
            hum.start();
            activeSoundNodes.push(hum, humGain);
        }
    }

    function startBackgroundSound(profile) {
        stopBackgroundSound();
        if (profile === "none" || soundPrefs.muted) return;
        const context = ensureAudioContext();
        if (!context) return;

        const profileMap = {
            rain: { kind: "white", filter: "highpass", frequency: 1150, volume: .22 },
            forest: { kind: "brown", filter: "lowpass", frequency: 1050, volume: .25 },
            ocean: { kind: "brown", filter: "lowpass", frequency: 640, volume: .32, wave: true },
            fireplace: { kind: "pink", filter: "bandpass", frequency: 520, volume: .2 },
            cafe: { kind: "pink", filter: "bandpass", frequency: 980, volume: .13 },
            night: { kind: "pink", filter: "highpass", frequency: 2600, volume: .09 },
            wind: { kind: "brown", filter: "bandpass", frequency: 460, volume: .2, wave: true },
            brown: { kind: "brown", filter: "lowpass", frequency: 1600, volume: .25 },
            pink: { kind: "pink", filter: "lowpass", frequency: 5200, volume: .18 },
            white: { kind: "white", filter: "lowpass", frequency: 9000, volume: .1 },
        };
        const config = profileMap[profile] || profileMap.pink;
        const source = context.createBufferSource();
        const filter = context.createBiquadFilter();
        const gain = context.createGain();
        source.buffer = makeNoiseBuffer(config.kind);
        source.loop = true;
        filter.type = config.filter;
        filter.frequency.value = config.frequency;
        gain.gain.value = config.volume * (soundPrefs.volume / 100);
        source.connect(filter).connect(gain).connect(context.destination);

        activeSoundNodes = [source, filter, gain];
        if (config.wave) {
            const lfo = context.createOscillator();
            const lfoGain = context.createGain();
            lfo.frequency.value = .12;
            lfoGain.gain.value = gain.gain.value * .55;
            gain.gain.value *= .72;
            lfo.connect(lfoGain).connect(gain.gain);
            lfo.start();
            activeSoundNodes.push(lfo, lfoGain);
        }
        source.start();
        addAmbientDetails(profile, soundPrefs.volume / 100);
    }

    function resumeSelectedSound() {
        if (soundPrefs.sound !== "none" && activeSoundNodes.length === 0 && !soundPrefs.muted) {
            startBackgroundSound(soundPrefs.sound);
        }
    }

    const soundSelect = document.getElementById("backgroundSound");
    const soundVolume = document.getElementById("soundVolume");
    const soundToggle = document.getElementById("soundToggle");
    soundSelect.value = soundPrefs.sound;
    soundVolume.value = soundPrefs.volume;
    soundToggle.classList.toggle("is-muted", soundPrefs.muted);

    soundSelect.addEventListener("change", () => {
        soundPrefs.sound = soundSelect.value;
        soundPrefs.muted = false;
        soundToggle.classList.remove("is-muted");
        saveSoundPrefs();
        startBackgroundSound(soundPrefs.sound);
    });

    soundVolume.addEventListener("input", () => {
        soundPrefs.volume = Number(soundVolume.value);
        saveSoundPrefs();
        if (soundPrefs.sound !== "none") startBackgroundSound(soundPrefs.sound);
    });

    soundToggle.addEventListener("click", () => {
        soundPrefs.muted = !soundPrefs.muted;
        soundToggle.classList.toggle("is-muted", soundPrefs.muted);
        saveSoundPrefs();
        if (soundPrefs.muted) stopBackgroundSound();
        else startBackgroundSound(soundPrefs.sound);
    });

    // Activity calendar merges saved server sessions with an immediate local marker.
    const calendarMonth = document.getElementById("calendarMonth");
    const calendarGrid = document.getElementById("calendarGrid");
    const calendarPrevious = document.getElementById("calendarPrevious");
    const calendarNext = document.getElementById("calendarNext");
    let visibleMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    let activityByDate = {};
    let tasksByDate = {};

    function localDateKey(date = new Date()) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function loadLocalActivity() {
        try { return JSON.parse(localStorage.getItem(activityStorageKey)) || {}; }
        catch (error) { return {}; }
    }

    function recordLocalCompletion() {
        const activity = loadLocalActivity();
        const key = localDateKey();
        activity[key] = (activity[key] || 0) + 1;
        localStorage.setItem(activityStorageKey, JSON.stringify(activity));
    }

    function renderCalendar() {
        const year = visibleMonth.getFullYear();
        const month = visibleMonth.getMonth();
        const firstDay = new Date(year, month, 1);
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const mondayOffset = (firstDay.getDay() + 6) % 7;
        calendarMonth.textContent = firstDay.toLocaleDateString(
            document.documentElement.lang || "en",
            { month: "long", year: "numeric" },
        );
        calendarGrid.innerHTML = "";

        for (let index = 0; index < mondayOffset; index += 1) {
            const empty = document.createElement("span");
            empty.className = "calendar-day is-empty";
            calendarGrid.appendChild(empty);
        }

        for (let day = 1; day <= daysInMonth; day += 1) {
            const date = new Date(year, month, day);
            const key = localDateKey(date);
            const cell = document.createElement("span");
            const sessionCount = activityByDate[key] || 0;
            const taskInfo = tasksByDate[key] || { count: 0, missed: false };
            cell.className = "calendar-day";
            cell.textContent = day;
            if (key === localDateKey()) cell.classList.add("is-today");
            if (sessionCount > 0) {
                cell.classList.add("has-session");
                cell.title = `${sessionCount} completed focus session${sessionCount === 1 ? "" : "s"}`;
                cell.setAttribute("aria-label", `${key}: ${sessionCount} completed focus session${sessionCount === 1 ? "" : "s"}`);
            }
            if (taskInfo.count > 0) {
                cell.classList.add("has-task");
                if (taskInfo.missed && sessionCount === 0) cell.classList.add("missed-task");
                const taskText = `${taskInfo.count} planned task${taskInfo.count === 1 ? "" : "s"}`;
                cell.title = cell.title ? `${cell.title}; ${taskText}` : taskText;
            }
            calendarGrid.appendChild(cell);
        }
    }

    async function loadCalendarActivity() {
        const year = visibleMonth.getFullYear();
        const month = visibleMonth.getMonth() + 1;
        const localActivity = loadLocalActivity();
        activityByDate = { ...localActivity };
        tasksByDate = {};
        renderCalendar();

        try {
            const response = await fetch(`/study/activity/?year=${year}&month=${month}`, { credentials: "same-origin" });
            if (!response.ok) return;
            const data = await response.json();
            data.days.forEach((item) => {
                activityByDate[item.date] = Math.max(activityByDate[item.date] || 0, item.count);
            });
            (data.tasks || []).forEach((item) => {
                const taskInfo = tasksByDate[item.date] || { count: 0, missed: false };
                taskInfo.count += 1;
                taskInfo.missed = taskInfo.missed || item.missed;
                tasksByDate[item.date] = taskInfo;
            });
            renderCalendar();
        } catch (error) {
            // Local activity remains visible if the app is temporarily offline.
        }
    }

    calendarPrevious.addEventListener("click", () => {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() - 1, 1);
        loadCalendarActivity();
    });

    calendarNext.addEventListener("click", () => {
        visibleMonth = new Date(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1, 1);
        loadCalendarActivity();
    });

    function setLowStimulusNavigationVisible(visible) {
        if (!learningSidebar) return;

        const shouldShow = visible && document.documentElement.classList.contains("low-stimulus");
        if (shouldShow) {
            if (sidebarCollapsedBeforeFocus === null) {
                sidebarCollapsedBeforeFocus = learningSidebar.classList.contains("collapsed");
            }
            learningSidebar.classList.remove("collapsed");
            appLayout.classList.remove("left-sidebar-is-collapsed");
            return;
        }

        if (sidebarCollapsedBeforeFocus !== null) {
            learningSidebar.classList.toggle("collapsed", sidebarCollapsedBeforeFocus);
            appLayout.classList.toggle("left-sidebar-is-collapsed", sidebarCollapsedBeforeFocus);
            sidebarCollapsedBeforeFocus = null;
        }
    }

    function setPanelCollapsed(collapsed) {
        panel.classList.toggle("is-collapsed", collapsed);
        appLayout.classList.toggle("right-sidebar-is-collapsed", collapsed);
        document.documentElement.classList.toggle("focus-panel-is-open", !collapsed);
        setLowStimulusNavigationVisible(!collapsed);
        panelToggle.setAttribute("aria-expanded", String(!collapsed));
        panelToggle.setAttribute("aria-label", collapsed ? "Show focus panel" : "Hide focus panel");
        panelToggle.title = collapsed ? "Show focus panel" : "Hide focus panel";
        sessionStorage.setItem("studyflow-right-panel-collapsed", String(collapsed));
    }

    function openFocusPanel(options = {}) {
        const { smooth = true } = options;
        setPanelCollapsed(false);
        if (
            learningSidebar
            && !document.documentElement.classList.contains("low-stimulus")
        ) {
            learningSidebar.classList.remove("collapsed");
            appLayout.classList.remove("left-sidebar-is-collapsed");
            localStorage.setItem("cocon-left-sidebar-collapsed", "false");
        }
        window.setTimeout(() => {
            document.querySelector(".timer-card")?.scrollIntoView({
                behavior: smooth ? "smooth" : "auto",
                block: "start",
            });
            startButton.focus({ preventScroll: true });
        }, smooth ? 300 : 0);
    }

    const savedPanelPreference = sessionStorage.getItem("studyflow-right-panel-collapsed");
    const panelCollapsed = savedPanelPreference === null || savedPanelPreference === "true";
    setPanelCollapsed(panelCollapsed);

    panelToggle.addEventListener("click", () => {
        setPanelCollapsed(!panel.classList.contains("is-collapsed"));
    });

    window.addEventListener("cocon:low-stimulus-change", (event) => {
        if (event.detail?.active) {
            setPanelCollapsed(true);
        } else {
            setLowStimulusNavigationVisible(false);
        }
    });

    document.querySelectorAll("[data-open-focus-panel]").forEach((trigger) => {
        trigger.addEventListener("click", () => openFocusPanel());
    });

    if (new URLSearchParams(window.location.search).get("focus") === "resume") {
        openFocusPanel({ smooth: false });
    }

    startButton.addEventListener("click", startTimer);
    pauseButton.addEventListener("click", pauseTimer);
    resetButton.addEventListener("click", resetTimer);
    selectDuration(studyChoices, "study");
    selectDuration(breakChoices, "break");

    renderTimer();
    loadCalendarActivity();
    if (state.running) {
        const restoredAudioMessage = "Timer restored — tap once anywhere to keep the finish alarm audible.";
        setMessage(restoredAudioMessage);
        const unlockRestoredAudio = () => {
            ensureAudioContext();
            resumeSelectedSound();
            if (timerMessage.textContent === restoredAudioMessage) setMessage("");
            document.removeEventListener("pointerdown", unlockRestoredAudio);
            document.removeEventListener("keydown", unlockRestoredAudio);
        };
        document.addEventListener("pointerdown", unlockRestoredAudio);
        document.addEventListener("keydown", unlockRestoredAudio);
    }
    if (state.running && state.phase === "study" && !state.sessionId) createStudySession();
    if (state.running && state.remaining === 0) completeCurrentPhase();
    window.setInterval(tick, 250);
})();
