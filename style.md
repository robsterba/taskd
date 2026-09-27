/* ============================================================
   STANDARD WEB THEME SPEC — Rob Sterba
   Apply to ALL web applications. Reference this file (or copy
   its tokens) as the single source of truth for color & style.

   Brand palette (from spec image):
     #2A2539  Deep plum-charcoal  — primary dark / night background
     #353044  Slate charcoal      — night surfaces / day primary
     #5E5373  Muted violet-gray   — accents, hover, borders
     #DBD8E3  Pale lavender       — night text / day background

   Usage: import this stylesheet, set data-theme="light" or
   "dark" on <html>. All components consume variables only —
   never hard-code hex values.
   ============================================================ */

/* ---------- LIGHT / DAY THEME (default) ---------- */
:root,
[data-theme="light"] {
  color-scheme: light;

  /* Surfaces */
  --bg-page:        #DBD8E3;  /* pale lavender page background */
  --bg-surface:     #FFFFFF;  /* cards, panels (near-neutral, derived) */
  --bg-surface-alt: #EFEDF5;  /* subtle raised areas, inputs */
  --bg-inset:       #C9C5D5;  /* wells, code blocks, pressed states */

  /* Text */
  --text-primary:   #2A2539;
  --text-secondary: #5E5373;
  --text-disabled:  #A9A4B8;
  --text-inverse:   #DBD8E3;  /* text on dark fills */

  /* Brand / accents */
  --accent:         #353044;  /* primary buttons, links, active nav */
  --accent-hover:   #5E5373;
  --accent-pressed: #2A2539;
  --accent-border:  #5E5373;
  --on-accent:      #DBD8E3;

  /* Lines & dividers */
  --border-default: #5E5373;
  --border-subtle:  #C0BCCC;

  /* Status (derived neutrals — adjust to taste) */
  --success:        #4C6B57;
  --warning:        #8A6D3B;
  --danger:         #8C3A3A;
  --info:           #4A5D7A;

  /* Elevation & focus */
  --shadow-sm: 0 1px 2px rgba(42, 37, 57, 0.15);
  --shadow-md: 0 4px 12px rgba(42, 37, 57, 0.18);
  --shadow-lg: 0 12px 32px rgba(42, 37, 57, 0.22);
  --focus-ring: 0 0 0 3px rgba(94, 83, 115, 0.45);
}

/* ---------- DARK / NIGHT THEME ---------- */
[data-theme="dark"] {
  color-scheme: dark;

  /* Surfaces */
  --bg-page:        #2A2539;  /* deep plum-charcoal page background */
  --bg-surface:     #353044;  /* cards, panels */
  --bg-surface-alt: #3E3850;  /* subtle raised areas, inputs */
  --bg-inset:       #232030;  /* wells, code blocks, pressed states */

  /* Text */
  --text-primary:   #DBD8E3;
  --text-secondary: #B3AEC4;
  --text-disabled:  #6B6480;
  --text-inverse:   #2A2539;  /* text on light fills */

  /* Brand / accents (accent inverts: light fill, dark text) */
  --accent:         #DBD8E3;
  --accent-hover:   #EFEDF5;
  --accent-pressed: #C9C5D5;
  --accent-border:  #5E5373;
  --on-accent:      #2A2539;

  /* Lines & dividers */
  --border-default: #5E5373;
  --border-subtle:  #4A4460;

  /* Status (brightened for dark backgrounds) */
  --success:        #7FA891;
  --warning:        #C9A56A;
  --danger:         #C97A7A;
  --info:           #8FA5C4;

  /* Elevation & focus */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.35);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.40);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.50);
  --focus-ring: 0 0 0 3px rgba(219, 216, 227, 0.35);
}

/* ============================================================
   BASE ELEMENT STYLES — apply everywhere
   ============================================================ */
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

/* ---------- COMPONENT TOKENS ---------- */
.card, .panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

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
}
.btn-secondary:hover { background: var(--bg-surface-alt); color: var(--text-primary); }

input, select, textarea {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font: inherit;
}

:focus-visible { outline: none; box-shadow: var(--focus-ring); }

hr, .divider { border: none; border-top: 1px solid var(--border-subtle); }

code, pre {
  background: var(--bg-inset);
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
code { padding: 0.1rem 0.35rem; }
pre { padding: 1rem; overflow-x: auto; }

/* ============================================================
   THEME SWITCHING SNIPPET (copy into app JS)
   ------------------------------------------------------------
   // Respect saved preference, else OS preference:
   const saved = localStorage.getItem("theme");
   const prefersDark = matchMedia("(prefers-color-scheme: dark)").matches;
   const theme = saved ?? (prefersDark ? "dark" : "light");
   document.documentElement.dataset.theme = theme;
   ------------------------------------------------------------
   // Toggle helper:
   const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
   document.documentElement.dataset.theme = t;
   localStorage.setItem("theme", t);
   ============================================================ */