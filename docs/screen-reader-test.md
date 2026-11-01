# Screen-reader test (task E5)

Automated checks (axe-core, `npm run a11y`, run in CI on every page of every edition in light and dark mode) catch missing names, contrast and structure errors. They cannot tell whether a page *makes sense* when listened to. This test does, and it needs a person.

## Setup

- **NVDA** (Windows, free) with Firefox or Chrome.
- **VoiceOver** (macOS: Cmd+F5; iOS: Settings → Accessibility) with Safari.
- Test the live site, one full municipality page with every section, e.g. `/opcina/jalzabet/` (it has payments), in Croatian, and the same page in English (`/en/municipality/jalzabet/`).
- Ideally with a resident who uses a screen reader daily; otherwise a team member who has practised for an hour first.

## Tasks

Ask the tester to do each task without looking at the screen. Note where they hesitate, what they hear that confuses them, and how long each task takes.

1. From the home page, find Ludbreg by typing in the search box. Is the number of results announced as it changes?
2. Open Jalžabet's page. Jump between headings (NVDA: H; VoiceOver: VO+Cmd+H). Is the page outline clear?
3. How much did Jalžabet spend in total last year? (The key figures under the heading.)
4. What does Jalžabet spend the most money on? (The summary sentence above the chart, then the bar list.)
5. Open the data table behind that chart ("Prikaži podatke kao tablicu") and read the second row by table navigation (NVDA: Ctrl+Alt+arrows). Are the column headers read with each cell?
6. In which month were the payments lowest? (The monthly table; the chart itself is hidden from screen readers.)
7. Who is the largest supplier, and with how many contracts?
8. Is there a kindergarten in Jalžabet? What is its address?
9. Where does the budget figure come from? Follow the source link to the sources table.
10. Switch to English with the language link. Are Croatian names (payment categories, contract subjects) pronounced in Croatian?

## Record and fix

For each task, record: done / done with difficulty / not done, and what was confusing. File each problem as an issue labelled `accessibility`, fix it, and re-test that task. When every task is done without difficulty in both screen readers, tick E5 in `TASKS.md` and update the accessibility statement (`src/messages/*-accessibility.tsx`), which lists the missing screen-reader test as a known gap.
