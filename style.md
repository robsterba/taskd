# Standard Web Theme Spec — Rob Sterba

This document is the single source of truth for the look, feel, and style of
**all** web applications. It defines design tokens, base element styles,
universal components, and reusable patterns. Copy the code blocks into each
app's stylesheet (or import a shared stylesheet built from them) and consume
the CSS variables — **never hard-code hex values in app code**.

Derived from the taskd application, generalized for reuse.

---

## Table of contents

1. [Brand palette](#1-brand-palette)
2. [Design tokens](#2-design-tokens)
3. [Base element styles](#3-base-element-styles)
4. [Core components](#4-core-components)
5. [Data display components](#5-data-display-components)
6. [Patterns](#6-patterns)
7. [Theme switching](#7-theme-switching)
8. [Adoption checklist](#8-adoption-checklist)

---

## 1. Brand palette

Five core colors from the spec image; everything else is derived.

| Hex       | Name        | Role                                              |
|-----------|-------------|---------------------------------------------------|
| `#E7ECEF` | Platinum    | Day page background / night text                   |
| `#274C77` | Dusk Blue   | Night page background / day primary accent & text  |
| `#6096BA` | Steel Blue  | Secondary accent, borders, hover                   |
| `#A3CEF1` | Icy Blue    | Highlights, night accent fills (with dusk-blue text) |
| `#8B8C89` | Grey Olive  | Muted/secondary text (day theme)                  |

Design language: cool, calm, blue-forward. Day theme is a platinum page with
dusk-blue text and primary accents; night theme inverts to a dusk-blue page
with platinum text and icy-blue accent fills carrying dusk-blue text
(inverted accent). Status colors are desaturated neutrals — never fully
saturated web-blue/green/red.

---

## 2. Design tokens

Usage: import these blocks into each app's global stylesheet, set
`data-theme="light"` or `"dark"` on `<html>`. Components consume variables
only.

### Light / day theme (default)

```css
:root,
[data-theme="light"] {
  color-scheme: light;

  /* Surfaces */
  --bg-page:        #E7ECEF;  /* platinum page background */
  --bg-surface:     #FFFFFF;  /* cards, panels (near-neutral, derived) */
  --bg-surface-alt: #F5F8FA;  /* subtle raised areas, inputs */
  --bg-inset:       #D3DCE3;  /* wells, code blocks, pressed states */

  /* Text */
  --text-primary:   #274C77;
  --text-secondary: #8B8C89;
  --text-disabled:  #B4B7B3;
  --text-inverse:   #E7ECEF;  /* text on dark fills */

  /* Brand / accents */
  --accent:         #274C77;  /* primary buttons, links, active nav */
  --accent-hover:   #6096BA;
  --accent-pressed: #1F3D5E;
  --accent-border:  #6096BA;
  --on-accent:      #E7ECEF;

  /* Highlights */
  --highlight:      #A3CEF1;  /* selected rows, info chips */
  --highlight-soft: #D9EAF8;

  /* Lines & dividers */
  --border-default: #6096BA;
  --border-subtle:  #C5CDD4;

  /* Status (derived harmonized neutrals) */
  --success:        #4C6B57;
  --warning:        #8A6D3B;
  --danger:         #8C3A3A;
  --info:           #6096BA;

  /* Elevation & focus */
  --shadow-sm: 0 1px 2px rgba(39, 76, 119, 0.15);
  --shadow-md: 0 4px 12px rgba(39, 76, 119, 0.18);
  --shadow-lg: 0 12px 32px rgba(39, 76, 119, 0.22);
  --focus-ring: 0 0 0 3px rgba(96, 150, 186, 0.50);
}
```

### Dark / night theme

```css
[data-theme="dark"] {
  color-scheme: dark;

  /* Surfaces */
  --bg-page:        #274C77;  /* dusk blue page background */
  --bg-surface:     #2F587F;  /* cards, panels (derived raised tone) */
  --bg-surface-alt: #37628C;  /* subtle raised areas, inputs */
  --bg-inset:       #1F3A5C;  /* wells, code blocks, pressed states */

  /* Text */
  --text-primary:   #E7ECEF;
  --text-secondary: #A3CEF1;
  --text-disabled:  #7E93AA;
  --text-inverse:   #274C77;  /* text on light fills */

  /* Brand / accents (accent inverts: light fill, dark text) */
  --accent:         #A3CEF1;
  --accent-hover:   #C6E2F7;
  --accent-pressed: #8FBDE4;
  --accent-border:  #6096BA;
  --on-accent:      #274C77;

  /* Highlights */
  --highlight:      #A3CEF1;
  --highlight-soft: #3F6D97;

  /* Lines & dividers */
  --border-default: #6096BA;
  --border-subtle:  #46688B;

  /* Status (brightened for dark backgrounds) */
  --success:        #7FA891;
  --warning:        #C9A56A;
  --danger:         #C97A7A;
  --info:           #A3CEF1;

  /* Elevation & focus */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.30);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.35);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.45);
  --focus-ring: 0 0 0 3px rgba(163, 206, 241, 0.40);
}
```

---

## 3. Base element styles

Apply everywhere, before any component styles.

```css
* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  transition: background-color 0.25s ease, color 0.25s ease;
}

h1, h2, h3, h4 { color: var(--text-primary); line-height: 1.25; }
a { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--accent-hover); }

:focus-visible { outline: none; box-shadow: var(--focus-ring); }

hr, .divider { border: none; border-top: 1px solid var(--border-subtle); }

code, pre {
  background: var(--bg-inset);
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
code { padding: 0.1rem 0.35rem; }
pre { padding: 1rem; overflow-x: auto; }
```

---

## 4. Core components

Every app has these; style them identically.

### 4.1 Cards and panels

```css
.card, .panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}
```

### 4.2 Buttons

Primary button (accent fill) and secondary button (outline). Interactive
buttons press down 1px on `:active`.

```css
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.1rem;
  border-radius: 6px;
  border: 1px solid var(--accent-border);
  background: var(--accent);
  color: var(--on-accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease, transform 0.05s ease;
}
.btn:hover  { background: var(--accent-hover); }
.btn:active { background: var(--accent-pressed); transform: translateY(1px); }

.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  font-weight: 500;
}
.btn-secondary:hover { background: var(--bg-surface-alt); color: var(--text-primary); }

button:disabled { cursor: not-allowed; opacity: 0.5; }
```

Rule: default `button` elements get the secondary (outline) treatment;
reserve the accent fill for the one primary action per view.

### 4.3 Form inputs

```css
input, select, textarea {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font: inherit;
}
```

---

## 5. Data display components

Components for showing lists, records, and user-generated content.

### 5.1 Badges

Small pill labels for status, priority, severity, or category. Use the tinted
badge recipe: `color-mix` the status color into a 15-22% transparent tint,
with the full status color as text.

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  text-transform: uppercase;
}

/* Status tints */
.badge.todo, .badge.info, .badge.in_progress {
  background: color-mix(in srgb, var(--info) 15%, transparent);
  color: var(--info);
}
.badge.done, .badge.success, .badge.ok {
  background: color-mix(in srgb, var(--success) 15%, transparent);
  color: var(--success);
}
.badge.archived, .badge.muted {
  background: var(--bg-surface-alt);
  color: var(--text-secondary);
}

/* Severity / priority tints */
.badge.low    { background: color-mix(in srgb, var(--success) 18%, transparent); color: var(--success); }
.badge.medium { background: color-mix(in srgb, var(--warning) 18%, transparent); color: var(--warning); }
.badge.high   { background: color-mix(in srgb, var(--danger) 18%, transparent);  color: color-mix(in srgb, var(--danger) 75%, var(--text-primary)); }
.badge.urgent, .badge.critical {
  background: color-mix(in srgb, var(--danger) 22%, transparent);
  color: var(--danger);
}
```

Notes:
- Larger badges (detail views) scale up: `padding: 6px 12px;
  border-radius: 16px; font-size: 0.85rem;` and drop `text-transform`.
- Completed items may add `text-decoration: line-through`.

### 5.2 Chips and tags

Neutral pill for a keyword/tag, clickable to filter or toggle. Hover inverts
to accent fill.

```css
.chip {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}
.chip:hover { background: var(--accent); color: var(--on-accent); }

/* Non-interactive variant */
.chip-static { cursor: default; }
```

### 5.3 Meta grid (definition rows)

Label/value rows for record metadata, stacked or wrapped. Label in secondary
text, value in primary text, on a raised surface.

```css
.meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 16px;
  background: var(--bg-surface-alt);
  border-radius: 8px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: var(--bg-surface-alt);
  border-radius: 8px;
}
.meta-item label { font-size: 0.85rem; color: var(--text-secondary); }
.meta-item span  { font-size: 0.85rem; color: var(--text-primary); }
```

### 5.4 Tables

Tables use the inset well treatment for contrast against page and card
backgrounds.

```css
table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-surface);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
th, td {
  padding: 10px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
}
th {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-secondary);
  background: var(--bg-surface-alt);
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: var(--bg-surface-alt); }
```

### 5.5 Stat blocks

Compact key/number summaries; centered, secondary text, divider-attached.

```css
.stats {
  text-align: center;
  padding: 16px;
  color: var(--text-secondary);
  font-size: 0.9rem;
  border-top: 1px solid var(--border-subtle);
}
.stats strong { color: var(--text-primary); font-weight: 600; }
```

### 5.6 Markdown-rendered content

User-authored rich text (descriptions, notes, docs) inside cards.

```css
.markdown { white-space: pre-wrap; word-wrap: break-word; }
.markdown p:not(:last-child) { margin-bottom: 1rem; }
.markdown h1, .markdown h2, .markdown h3,
.markdown h4, .markdown h5, .markdown h6 {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
}
.markdown ul, .markdown ol { margin-bottom: 1rem; padding-left: 2rem; }
.markdown li { margin-bottom: 0.5rem; }
.markdown a { color: var(--accent); text-decoration: underline; }
.markdown blockquote {
  border-left: 3px solid var(--border-default);
  margin: 0 0 1rem;
  padding: 0.25rem 1rem;
  color: var(--text-secondary);
}
```

### 5.7 Timestamps and dates

```css
.timestamp { color: var(--text-secondary); }
.timestamp.overdue { color: var(--danger); font-weight: 600; }
```

---

## 6. Patterns

Generalized recipes extracted from taskd. Adapt the class names to the app;
keep the structure and token usage.

### 6.1 Color-coded item card

Any card in a list whose category is signaled by a colored left stripe. The
stripe is 4px wide, set via `border-left` on the card, using status colors.

```css
.item-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-left: 4px solid var(--border-default);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.item-card:hover { box-shadow: var(--shadow-md); }

/* Severity mapping (priority, health, urgency...) */
.item-card.urgent  { border-left-color: var(--danger); }
.item-card.high    { border-left-color: color-mix(in srgb, var(--danger) 70%, var(--text-primary)); }
.item-card.medium  { border-left-color: var(--warning); }
.item-card.low     { border-left-color: var(--success); }
```

### 6.2 Tinted status badge

Already covered in [5.1](#51-badges); the recipe itself:
`background: color-mix(in srgb, var(--status-token) 15-22%, transparent);
color: var(--status-token);`. Use one consistent tint strength within an app
(15% for informational, 18-22% for severity).

### 6.3 Item structure inside cards

Cards containing a selectable/inspectable item follow this layout grammar:

```
.item-card
├── .item-header        row: checkbox or icon, name (bold), badges on the right
├── .item-meta          row: chips, timestamps — small, secondary color
└── .item-section       optional nested content, separated by
                        border-top: 1px dashed var(--border-subtle)
```

- Done/completed items: `text-decoration: line-through` on the name, value in
  `var(--text-secondary)`.
- IDs and technical values render in the monospace stack
  (`ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`) at `0.8rem`.

### 6.4 Motion

Keep animations short (0.05-0.25s ease) and functional only: hover/press
feedback, theme transition on body, and `slideIn` for newly appearing cards.

```css
@keyframes slideIn {
  from { transform: translateY(-10px); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}
```

---

## 7. Theme switching

Copy into app JS. Respect saved preference, else OS preference.

```js
// Initial load
const saved = localStorage.getItem("theme");
const prefersDark = matchMedia("(prefers-color-scheme: dark)").matches;
const theme = saved ?? (prefersDark ? "dark" : "light");
document.documentElement.dataset.theme = theme;

// Toggle helper
const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
document.documentElement.dataset.theme = t;
localStorage.setItem("theme", t);
```

Theme toggle button styling (outline button, no text weight emphasis):

```css
.theme-toggle {
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.theme-toggle:hover {
  background: var(--bg-surface-alt);
  border-color: var(--accent-border);
}
```

---

## 8. Adoption checklist

For an app to conform to this spec:

- [ ] Includes both token blocks (light + dark) verbatim.
- [ ] Includes base element styles.
- [ ] Uses `data-theme` switching with `localStorage` persistence.
- [ ] No hard-coded hex values outside the token blocks.
- [ ] Cards use 8px radius, subtle border, `--shadow-sm`.
- [ ] Buttons use 6px radius; default buttons are outline, primary action is
      accent fill; `:active` translates 1px down.
- [ ] Badges and chips use 12px radius pills with tinted `color-mix`
      backgrounds.
- [ ] Status/severity coloring maps to `--success` / `--warning` / `--danger`
      / `--info` only.
- [ ] Monospace stack for IDs, code, and technical values.
- [ ] Interactive transitions stay within 0.05-0.25s.
