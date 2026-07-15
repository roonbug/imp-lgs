# Japanese Vocabulary Memorization Trainer

A self-contained, browser-based tool that helps a participant **memorize** 26
Japanese words (English → romaji, with pictures). It is built on evidence-based
memory techniques — study with dual coding (word + picture), retrieval practice
with feedback (the testing effect), and repeated spaced exposure — followed by a
final self-check. Interaction data (responses, reaction times, JOL/confidence)
are logged for records, with lightweight anti-cheating (behavior) proctoring.

## Files

| File | Purpose |
|------|---------|
| `study.html` | The entire experiment — inline HTML/CSS/JS, no external libraries. |
| `server.py` | Reference Flask server: serves the study + `img/` + `audio/`, receives data. |
| `requirements.txt` | `flask`, `flask-cors`. |
| `img/` | Stimulus images (one per word, except the names *Jon* / *Mia*). |
| `audio/` | Native pronunciation MP3s, one per word (`<english>.mp3`). |
| `make_audio.py` | Regenerates `audio/` via TTS from each word's kana (needs internet). |
| `list.txt` | Source word list (English + romaji). Mirrored in `study.html`. |
| `data/` | Created at runtime; holds collected data (see below). |

## Quick start

```bash
pip install -r requirements.txt
python server.py
# open http://localhost:5000 in a browser
```

Running through the server (rather than double-clicking `study.html`) matters:
the **Fullscreen API** and the **`fetch` upload** require a *secure context*
(`http://localhost` or `https://`). The server hosts the page and `img/` and
receives the data at the same origin, so no configuration is needed for local runs.

## Deploying to GitHub Pages + OSF (recommended)

Free, permanent, HTTPS (so full-screen proctoring works), data saved to your OSF
project. GitHub Pages only serves static files, so data goes to OSF through
**DataPipe** (`pipe.jspsych.org`), which holds your OSF token server-side — **never
put an OSF personal access token in `study.html`; it would be public.**

1. **OSF**: create a project (and a component to hold the data). Generate a personal
   access token at <https://osf.io/settings/tokens> (`osf.full_write` scope).
2. **DataPipe** (<https://pipe.jspsych.org>): sign in, add your OSF token, create an
   **experiment** linked to the OSF component, and switch it to **"Enable data
   collection."** Copy the **experiment ID**.
3. **study.html**: set `CONFIG.DATAPIPE_EXPERIMENT_ID` to that ID (leave it `""` for
   local testing with `server.py`). Each submission is written to your OSF project as
   `<pid>_s<session>_<timestamp>.json`; the download-to-device fallback still fires if
   the upload ever fails.
4. **GitHub Pages**: push `study.html`, `img/`, and `audio/` to a repo and enable
   Pages (Settings → Pages → deploy from branch). Share the
   `https://<user>.github.io/<repo>/study.html` link; the day-2 link is the same URL
   with `?session=2&pid=<CODE>`.

`server.py` is still used for **local development** (when `DATAPIPE_EXPERIMENT_ID` is
empty the page POSTs to it) and as a self-hosting option; it is not needed on Pages.
To point at a different collector instead, set `CONFIG.ENDPOINT_URL` (it receives the
JSON payload described below).

## Experimental design

Single-file pipeline; item order and the image/text assignment are randomized with
a **participant-seeded PRNG** (`mulberry32` seeded from the participant code), so a
given participant's randomization is reproducible and recoverable from the data.

**Session 1**
1. **Consent** (checkbox, timestamped).
2. **Instructions + proctoring start** — requests full-screen, begins event logging.
3. **Demographics** — participant code, age, native language, prior-Japanese rating.
4. **Learning rounds (mastery loop).** Each round runs:
   1. **Introduce (×2)** — the word is shown *with* its romaji and the native
      pronunciation **auto-plays** (replayable with a 🔊 button); the participant
      **types what they see and hear**. The answer is visible, but they must type it
      **correctly to advance** (a mismatch shows a hint and keeps them on the word);
      their first-attempt accuracy is recorded. This runs as **two full passes** over
      the set.
   2. **Multiple-choice (until all correct)** — pick the romaji for the word (4
      options, distractors from the same semantic category). After answering, the
      chosen and correct options are highlighted (green/red) with a **Correct! /
      Correct answer** message and the pronunciation. **Items answered incorrectly are
      re-added and shown again in a later cycle**, so the pass does not end until every
      item has been answered correctly at least once (review cycles are marked with
      `pass_no`).
   3. **Typed recall** — type the romaji **from memory** (no romaji or audio hint on
      the prompt). Typo-tolerant scoring (Levenshtein ≤ 1 for words ≥ 4 letters).
      After answering, feedback shows whether it was correct — on a miss it shows
      what they typed and the correct answer, with the picture and pronunciation.
      The **first full-set pass is the graded gate**.
      - **Remediation:** if that pass isn't all correct, the participant chooses to
        re-practice **all items** or **just the ones they missed**. The chosen set
        goes back through the multiple-choice pass only (step 2, until all correct),
        and then the **full set is typed-recalled again** (recall is always over the
        full set). This repeats until a full-set recall pass is entirely correct.

   Rounds **auto-repeat** until the **first full-set typed-recall pass** scores **100%
   on `MASTERY_CONSECUTIVE` (=2) rounds in a row** — at which point the participant may
   **finish or keep rehearsing** — or until the **`LEARN_MAX_ROUNDS` (=5)** cap. (The
   remediation loop drives every round's *final* recall to 100%, so only the *first*
   full-set pass of each round feeds the mastery/cap decision.) Audio plays on the
   introduce pass and on the answer-feedback cards, never on a live prompt, so it can't
   reveal the answer before the participant responds.
5. **Debrief** — data uploaded (with download fallback); the participant is shown
   their code and a **day-2 return link**.

There is no warm-up/pretest — participants go straight from demographics into the
learning rounds.

**Session 2 (day 2).** Opening `study.html?session=2&pid=<CODE>` runs the **same
learning rounds** (no demographics) and uploads with `session: 2`, so day-2
learning can be compared with day 1.

### Constructs / measures logged

- **Dual coding** — image vs. text-only condition per item (`condition` field),
  balanced within each semantic category.
- **Testing effect / retrieval practice** — multiple-choice + typed recall each round.
- **Learning curve** — typed-recall accuracy (and RT) across rounds (`test_round_N`).
- **Spacing** — `spacing_lag` = trials since the item was last seen.
- **Reaction time** — `rt_ms` on every response (fluency measure).
- **Serial position** — `trial_index` preserves within-phase order.

### Materials note

`img/` covers every word except the proper names **Jon** and **Mia**, which render
as initial-letter cards and are held in the **text-only** condition (excluded from
the image-vs-text contrast). Because their English and romaji forms are identical,
you may wish to exclude both names when analysing recall accuracy.

## Proctoring (behavior logging only — no webcam)

Logged to `proctor_events` with a timestamp and the current phase:
`blur` / `focus`, `visibility_hidden` / `visibility_visible` (tab switching, with
cumulative off-screen time), `fullscreen_enter` / `fullscreen_exit`,
`paste` / `copy` / `cut` (prevented + logged), `contextmenu` (right-click),
`resize`. Each **trial** also carries `focus_lost_during_trial`, and the payload
includes an `integrity_summary` (event counts + total off-screen ms). Copy/paste
and right-click are blocked during the study. A `beforeunload` prompt discourages
accidental early exit.

> The original brief mentioned webcam/video proctoring; per the chosen design this
> build logs behavior only. A `USE_WEBCAM` path can be added later without
> restructuring the flow.

## Data

`server.py` writes, in `./data/`:

- `data/<pid>_s<session>_<timestamp>.json` — one raw file per submission
  (never overwritten).
- `data/trials.csv` — flattened per-trial rows appended across all participants.
- `data/proctor_events.csv` — flattened proctoring events.
- `GET /api/export` — downloads the combined `trials.csv`.

### POST payload schema (`/api/data`)

```jsonc
{
  "participant_id": "P3F9KQ",
  "session": 1,
  "study_version": "2.0.0",
  "submitted_iso": "2026-07-04T18:20:00.000Z",
  "meta": {
    "consent_ts": "…", "age": "27", "native_language": "English",
    "prior_japanese": "none", "randomization_seed": 123456789,
    "condition_assignment_map": { "5": "image", "6": "text", … },
    "user_agent": "…", "screen": { "w": 1920, "h": 1080, "dpr": 2 },
    "integrity_summary": { "total_offscreen_ms": 0, "counts": { … }, "n_events": 12 }
  },
  "trials": [ /* one object per trial — fields below */ ],
  "proctor_events": [ { "event_type": "blur", "ts": "…", "t_ms": 4210, "phase": "learn_round_1_introduce", "details": null } ]
}
```

**Per-trial fields:** `participant_id, session, study_version, phase, block,
trial_index, item_id, english, romaji, category, condition, has_image, test_type
(introduce|recognition|recall), direction, prompt_onset_ts, response_ts,
rt_ms, response_raw, response_normalized, correct, edit_distance, confidence_or_jol,
mcq_options, mcq_choice, pass_no, spacing_lag, focus_lost_during_trial,
timestamp_iso`.

Within a round, the introduce and initial multiple-choice passes share phase
`learn_round_<n>`; the typed-recall gate uses phase `test_round_<n>`; remediation
multiple-choice uses `retry_round_<n>`. `pass_no` counts the pass within its runner —
MCQ review cycles, and successive **full-set** recall passes in a round (every recall
pass is over the full set). **The graded per-round score is the recall pass with
`pass_no:1`** (the pre-remediation attempt).

## Configuration

Constants at the top of `study.html` (`CONFIG`): `DATAPIPE_EXPERIMENT_ID`,
`DATAPIPE_URL`, `ENDPOINT_URL`, `STUDY_VERSION`,
`LEARN_MAX_ROUNDS`, `MASTERY_CONSECUTIVE`, `N_MCQ_OPTIONS`, `RECALL_EDIT_TOLERANCE`,
`REQUIRE_FULLSCREEN`, `AUTO_DOWNLOAD_ON_FAIL`.

## Ethics / consent

The consent screen states voluntariness, the data recorded (responses, timings,
interaction events; **no audio/video**), confidentiality (random code only), and
the integrity monitoring. Replace the consent text and add IRB/ethics-approval and
contact information before running with human participants.
