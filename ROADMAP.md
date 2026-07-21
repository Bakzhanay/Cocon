# Cocon roadmap

This is a living product roadmap, not a promise that every idea must be built.
Priorities should continue to come from using Cocon in real life and noticing
where it creates clarity, friction, or pressure.

## Product vision

Cocon is a calm focus system that turns intentional time into visible evidence
of progress.

It should help people:

- keep learning materials, plans, and focused work in one place;
- understand where their attention and energy are going;
- notice important areas that have received less attention;
- remember how much work sits behind results they might otherwise devalue;
- begin with one small step when a large plan feels overwhelming;
- work with hyperfocus without being controlled or exhausted by it.

The long-term opportunity extends beyond studying. A user could eventually
organize areas such as Work, University preparation, Languages, Music,
Exercise, Home, Cooking, or Family and decide which of them should be measured.
Cocon should support balance without implying that every meaningful part of
life can be reduced to minutes.

## Product principles

1. **Intentional time, not passive surveillance.** Time is recorded when the
   user deliberately starts a focus session, not merely because a page is open.
2. **Evidence, not judgment.** Statistics should say where energy went, not
   shame the user for failing to be productive enough.
3. **Complexity by choice.** The full dashboard can offer depth, while Calm Mode
   leaves only the information needed for the next step.
4. **Private by default.** Notes, activity, goals, and statistics remain private
   unless the user explicitly chooses to share something.
5. **Human control over automation.** Imports and future AI suggestions must be
   previewed, editable, and confirmed before changing the learning map.
6. **No addictive design.** Cocon may make it easier to begin and stay curious,
   but should never use an infinite feed, guilt, or artificial urgency to keep
   somebody inside the app.
7. **Accessibility is part of the product.** Low-stimulation design, readable
   contrast, keyboard access, responsive layouts, and gentle language are core
   requirements rather than optional polish.

## Foundation already built

- Topic -> Section -> Subject -> Notes / Flashcards learning hierarchy.
- Notes with references and attachments, quick notes, and pinned notes.
- Flashcards with mastery controls and spaced-review scheduling.
- Persistent Pomodoro timer, configurable breaks, and soundscapes.
- Focus attribution across the hierarchy and individual activities.
- Dashboard statistics, streaks, goals, calendar, and focus balance.
- To-do items and study plans that can progress from matching focus sessions.
- Bulk subject creation, subtitle presets, colors, filters, and bulk actions.
- Light, dark, and low-stimulation modes.
- Automated regression tests and fresh-database migration checks.

## Horizon 0: Build Week submission and stable release

**Goal:** present the strongest existing workflow instead of adding another
large feature immediately before submission.

- Finish the real screen-recorded demo and English captions.
- Show the complete story: plan -> choose context -> focus -> recorded time ->
  hierarchical analytics -> Calm Mode.
- Replace outdated public screenshots and the README demo GIF.
- Run the complete automated test suite and one final browser walkthrough.
- Fix submission-blocking bugs only; record smaller issues for the next release.
- Push the verified version, confirm GitHub Actions, and submit on Devpost.
- Preserve a tagged release so the Build Week version can always be recovered.

## Horizon 1: Reliability, accounts, and personal control

**Goal:** make Cocon safe and comfortable for continued personal use and future
public testing.

- Profile page with display name, username, avatar, timezone, and study goals.
- Password change and password-reset flow.
- Automatic local-timezone detection with an explicit user override.
- Export and import for the learning map, notes, plans, and focus history.
- Clear backup and restore instructions before any hosted release.
- More responsive testing across laptop, desktop, tablet, and phone widths.
- Keyboard navigation, visible focus states, screen-reader labels, and a full
  light/dark contrast audit.
- Better recovery from interrupted timers, closed tabs, network failures, and
  partially uploaded files.
- A small in-app feedback or issue-reporting path for beta users.

## Horizon 2: Gentle focus care

**Goal:** help users enter hyperfocus without forgetting the person doing the
work.

- Optional reminders based on active focused time rather than page-open time.
- User-selected intervals such as 45, 60, or 90 minutes.
- Gentle suggestions for water, movement, changing posture, resting the eyes,
  or taking a real break.
- Actions such as `Take a short break`, `Remind me in 10 minutes`, and
  `Continue`.
- Quiet notifications without alarms, punishment, or lost streaks.
- Prefer reminders between sessions, with an optional non-interrupting mode for
  people who do not want to be pulled out of a thought.
- A daily option to reduce or disable goals when the user has less capacity.
- Calm Mode should be able to hide statistics while Cocon continues recording
  progress quietly in the background.

Suggested language:

> Your focus has been strong. Let's take care of the person doing the work.

## Horizon 3: Meaningful long-term analytics

**Goal:** help users see accumulated effort and rebalance attention without
turning the dashboard into a scorecard.

- Weekly, monthly, quarterly, and yearly views.
- A personal "evidence of effort" summary: focused hours, completed sessions,
  revisited subjects, finished plans, and consistent habits.
- Drill-down from Topic -> Section -> Subject -> Notes / Flashcards.
- Clear distinction between time spent directly at one level and time rolled up
  from its children.
- Planned-versus-actual focus time for tasks, deadlines, and life areas.
- Trends that show where attention is increasing, decreasing, or staying
  balanced.
- Neutral wording such as `Received less focus recently` instead of
  `You are behind`.
- User-controlled weekly targets; no universal definition of a good number of
  hours.
- Optional exportable or shareable summaries with private details removed.
- A retrospective view such as `What you actually did this month` to make
  invisible work visible.

## Horizon 4: Planning, deadlines, and routines

**Goal:** connect intention and completed focus more closely.

- Dedicated deadlines with a target date, related learning context, and planned
  preparation time.
- Break a deadline into small study plans without duplicating the hierarchy.
- Daily and weekly planning views.
- Recurring routines for areas that need regular attention.
- Searchable context picker everywhere a topic, section, or subject is chosen.
- Automatic completion when matching Pomodoro time reaches a plan's target,
  while still allowing manual completion and correction.
- Rescheduling that preserves history instead of treating a changed plan as a
  failure.
- Calendar view combining planned work, completed sessions, and rest days.

## Horizon 5: Explore mode

**Goal:** let opening Cocon casually turn into learning through curiosity, not
pressure.

- A quiet `Explore` entry point for days when the user does not know what to
  choose.
- Gently resurface one old note, due flashcard set, unfinished plan, or
  previously important subject.
- Offer a low-friction `Focus for 15 minutes` action.
- Allow the user to dismiss, save for later, or ask for another suggestion.
- Never become an infinite recommendation feed.
- Base suggestions on the user's own materials and goals, not engagement time.

Product line:

> A place where wandering can turn into learning.

## Horizon 6: Mobile and cross-device Cocon

**Goal:** make intentional focus and quick capture available away from a
laptop.

- Begin with a responsive, installable progressive web app before committing to
  separate native applications.
- Quick notes and task capture from a phone.
- Mobile flashcard review and a distraction-free timer screen.
- Background timer notifications that remain accurate when the screen sleeps.
- Offline-safe capture with later synchronization.
- Only then evaluate native applications and cross-device sync.
- Design authentication, encryption, data deletion, and conflict resolution
  before storing private learning data in the cloud.

## Horizon 7: AI-assisted learning setup

**Goal:** reduce repetitive organization while keeping the learner responsible
for what enters their workspace.

- Paste or upload a syllabus and generate a proposed Topic -> Section -> Subject
  structure.
- Show a complete editable preview before saving anything.
- Suggest subtitles, study plans, starter questions, and flashcards.
- Generate flashcards from selected notes rather than from unrelated context.
- Keep references to source material where possible and make uncertainty clear.
- Let users regenerate one item instead of replacing an entire learning map.
- Never silently publish, share, or overwrite private material.
- Make AI optional; the core timer, notes, flashcards, and analytics must remain
  useful without it.

## Horizon 8: Optional social layer

**Goal:** allow encouragement and selective sharing without turning the private
workspace into a social network by default.

- A separate profile area rather than social content inside the study flow.
- Optional public introduction, interests, current goals, and selected topics.
- User-selected progress cards, deadline updates, or monthly summaries.
- Optional `Currently focusing on...` status that is off by default.
- Shareable private links for a mentor, teacher, friend, or accountability
  partner.
- Interest-based discovery only after privacy controls are understandable.
- Direct messages only after blocking, reporting, abuse prevention, and
  moderation have been designed.
- No public activity feed based on private sessions and no automatic exposure of
  study times, notes, or personal routines.

Social features should remain an addition to Cocon, never a requirement for
using its core workspace.

## Ideas intentionally kept out of the near-term scope

- Gamification built around public rankings or maximum hours.
- Punishing streaks that make rest feel like failure.
- Passive background tracking of all computer or phone activity.
- Automatic medical or psychological conclusions from focus behavior.
- A public feed optimized for time spent in the app.
- AI that creates large amounts of unreviewed material and makes the workspace
  harder to trust.

## How to choose the next feature

Before starting a roadmap item, ask:

1. Did real use reveal this problem more than once?
2. Does it strengthen the focus loop or merely add another destination?
3. Can the user understand and reverse what it does?
4. Does it remain calm in both the normal and low-stimulation interfaces?
5. Can its data be explained without double-counting or hidden tracking?
6. Is it more important than fixing the friction already observed?

When several ideas compete, prioritize in this order:

1. Data correctness and privacy.
2. A complete focus workflow without dead ends.
3. Accessibility and emotional safety.
4. Clear long-term insight.
5. Convenience and automation.
6. Optional AI and social expansion.

## North-star idea

> Cocon turns focused time into visible proof of progress, then becomes quiet
> when seeing all that progress feels like too much.
