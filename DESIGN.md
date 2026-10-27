# Design

Design system for the notebooklm-lite frontend.
Quiet and precise; built for long text readability.

---

## Palette

| Token              | Hex       | Role                                           |
|--------------------|-----------|-------------------------------------------------|
| `--ground`         | `#f4f3f1` | Page background                                 |
| `--surface`        | `#eae8e5` | Rail, panels, inset regions                      |
| `--surface-2`      | `#d5d2cd` | Subtle divider tone step                         |
| `--ink`            | `#1d1d1f` | Primary text                                     |
| `--accent`         | `#2b5e8c` | Upload button, focus rings, selected notebook bar |
| `--error`          | `#b44130` | Error text and error-state borders               |

Accent darkened from original `#3a6ea5` to pass WCAG AA contrast
on both `--ground` (6.2:1) and `--surface` (5.6:1). White on accent
gives 6.8:1.

Dark mode (not M6a): swap ground/surface/surface-2/ink; accent and
error stay. All color usage goes through these tokens.

---

## Type

One family: **Inter** via `@fontsource-variable/inter`.

| Role      | Size     | Weight | Line-height | Max-width | Token              |
|-----------|----------|--------|-------------|-----------|--------------------|
| Title     | 1.25rem  | 600    | 1.3         | --        | `--font-title`     |
| Section   | 0.8125rem| 600    | 1.4         | --        | `--font-section`   |
| Body/UI   | 0.875rem | 400    | 1.5         | --        | `--font-body`      |
| Reading   | 1rem     | 400    | 1.575       | 70ch      | `--font-reading`   |
| Caption   | 0.75rem  | 400    | 1.4         | --        | `--font-caption`   |

Reading role is for long-form text (chat answers, evidence quotes
in M6b). Sentence case everywhere; no tracked all-caps.

Tabular figures on counts: `font-variant-numeric: tabular-lnums`.

---

## Layout

One radius: `--radius: 4px`. No shadows, no lines. Surfaces
separated by tone steps only.

### Desktop (>=960px): rail + main + evidence panel

```
+------------------+----------------------------+-------------------+
| notebooklm lite  |                            |                   |
|                  | Research papers   (title)  |                   |
| Notebooks        |                            |                   |
|                  | Documents                  |  (reserved:       |
| [____________]   | paper-v3.pdf  12pp  47ch   |   evidence panel, |
| create           | survey.pdf     8pp  31ch   |   M6b)            |
|                  |                            |                   |
| > Research p...  | [choose file]              |                   |
|   Side project   | pdf, up to 20 mb           |                   |
|   Reading list   |                            |                   |
|                  +----------------------------+                   |
|                  |                            |                   |
|                  | (reserved: chat, M6b)      |                   |
|                  |                            |                   |
+------------------+----------------------------+-------------------+
  240px  surface      flex   ground                 320px  surface
```

Rail: 240px fixed, `--surface` background. App name in the rail
header (caption weight, muted).

Main column: flex, `--ground` background. Upper region has
notebook title + document list + upload. Lower region reserved
for chat (M6b), shown as an empty `--surface` container.

Evidence panel: 320px fixed, `--surface` background, full height.
Reserved for M6b. Shows: "Sources will appear here."

### Tablet (640-959px)

Rail narrows to 200px. Evidence panel stacks below main as a
full-width region. Single scrolling column for main + evidence.

### Phone (<640px)

```
+----------------------------------+
| notebooklm lite  [+ create]     |
| [v notebook select          v]   |
+----------------------------------+
| Research papers                  |
|                                  |
| Documents                        |
| paper-v3.pdf     12pp   47ch    |
| survey.pdf        8pp   31ch    |
|                                  |
| [choose file]                    |
| pdf, up to 20 mb                |
|                                  |
| (chat: M6b)                     |
+----------------------------------+
| (sources: M6b)                   |
+----------------------------------+
```

Rail becomes a horizontal strip: a `<select>` for notebook
switching + a create button. Evidence panel stacks below main.

---

## States

### No notebook selected (initial load, or after notebooks load)

Main area shows: "Select a notebook or create one to get started."
Upload control hidden. Evidence panel reserved text visible.

### Notebook rail

| State             | Display                                              |
|-------------------|------------------------------------------------------|
| Loading           | Three pulsing placeholder lines (respects prefers-reduced-motion) |
| Empty             | "No notebooks yet. Create one above."                |
| Loaded            | List of names, most recent first. Selected: `--ink` text + `--accent` left border, `aria-current="true"` |
| Error             | `--error` text: "Could not load notebooks. Reload the page." |
| Creating          | Field disabled, "Creating..." beside it              |
| Create error 422  | "Notebook name cannot be empty."                     |

### Document list

| State    | Display                                                     |
|----------|-------------------------------------------------------------|
| Loading  | Three pulsing placeholder rows                               |
| Empty    | "No documents yet. Upload a PDF to get started."             |
| Loaded   | Rows: filename, page count, chunk count                      |
| Error    | "Could not load documents. Reload the page."                 |

### Upload

| State       | Display                                                    |
|-------------|-------------------------------------------------------------|
| Idle        | Styled file button labeled "choose file", hint: "pdf, up to 20 mb" |
| Pre-send    | Client rejects non-.pdf extension: "Select a .pdf file."   |
| Over 20 MB  | Client rejects: "File exceeds 20 MB limit."                |
| Uploading   | Button disabled. Live region: "Uploading and processing [filename]... This may take a minute." |
| Success     | Live region: "[filename] uploaded successfully." Document list refreshes. Status clears after 4s. |
| Error 400   | Show backend detail string (e.g. "Only PDF files are accepted") |
| Error 413   | "File exceeds 20 MB limit."                                |
| Error 422   | "No extractable text in this PDF. It may be a scanned image." |
| Error 502   | "Embedding service failed. Nothing was saved. Try again."  |
| Error 404   | "Notebook not found. Select another notebook."             |
| Network/5xx | "Something went wrong. Check your connection and try again." |

Uploads are tied to the originating notebook: if the selected
notebook changes while an upload is in flight, the success refresh
targets the notebook that initiated the upload.

---

## Boldness budget

**One bold element: the upload button.** `--accent` background,
white text, the only colored control. Everything else stays quiet.

Selected notebook: `--ink` text + `--accent` left border (not
accent-colored text, which would fail contrast on `--surface`).

---

## Accessibility

- Focus ring: 2px solid `--accent`, 2px offset. Visible on both
  `--ground` and `--surface` backgrounds.
- Selected notebook: `aria-current="true"`.
- File input: visually hidden native input, label styled as button.
- Upload status: `aria-live="polite"` region for progress, success,
  and error messages.
- Skeleton loading: CSS animation with `prefers-reduced-motion: reduce`
  disabling the pulse.
- All inputs labeled. Interactive elements have visible focus states.
- Tabular figures for numeric data.

---

## Error handling (client.ts)

- Backend `detail` field may be a string or a list of validation
  objects. Client normalizes both to a display string.
- 400-range errors: show the backend `detail` message.
- 500-range and network errors: show a generic fallback.
- Client-side 20 MB check before upload (avoid sending large files).

---

## Stale-response protection

`useDocuments(notebookId)` hook:
- Aborts in-flight fetches when `notebookId` changes.
- Ignores responses that arrive for a notebook other than the
  current one.
- Upload success refresh checks that the originating notebook
  is still selected before updating the list.
