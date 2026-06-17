---
name: my-agent Console
description: Chat-centered Agent Workspace Console with restrained dark Liquid Glass surfaces.
colors:
  console-background: "oklch(0.13 0.026 258)"
  glass-surface: "oklch(0.2 0.036 258 / 0.72)"
  glass-surface-strong: "oklch(0.24 0.038 258 / 0.88)"
  foreground: "oklch(0.96 0.012 248)"
  muted: "oklch(0.76 0.03 248)"
  border: "oklch(0.94 0.018 248 / 0.16)"
  signal-teal: "oklch(0.78 0.15 183)"
  signal-teal-strong: "oklch(0.7 0.16 183)"
  danger-red: "oklch(0.66 0.22 25)"
  runtime-amber: "oklch(0.82 0.15 82)"
typography:
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.12
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.35
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.62
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
    fontSize: "0.78rem"
    fontWeight: 800
    lineHeight: 1.2
rounded:
  md: "12px"
  lg: "18px"
  panel: "20px"
  auth-card: "22px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "18px"
  xl: "24px"
  auth-card: "32px"
components:
  button-primary:
    backgroundColor: "{colors.signal-teal}"
    textColor: "{colors.console-background}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "44px"
  button-danger:
    backgroundColor: "{colors.danger-red}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "44px"
  button-icon:
    backgroundColor: "{colors.glass-surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    height: "44px"
    width: "44px"
  field:
    backgroundColor: "{colors.console-background}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "46px"
  panel-glass:
    backgroundColor: "{colors.glass-surface}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.panel}"
---

# Design System: my-agent Console

## 1. Overview

**Creative North Star: "Quiet Cockpit"**

my-agent Console is a restrained product interface for developers operating an Agent runtime. The workspace should feel like a quiet cockpit: chat is the center instrument, session state and approval risk live in nearby rails, and every action remains legible under pressure.

The visual system uses dark Liquid Glass as a material language, not as decoration. Glass panels separate durable work zones, but text, code-like content, error states, and approval reasons always keep higher contrast than the material effect.

This system explicitly rejects a pure chat skin, full-screen translucent glass, heavy operations dashboards, editable secrets panels, and emoji-as-icons. Familiar product controls win over novelty.

**Key Characteristics:**
- Dark, cool console base with one operational teal accent.
- Chat-centered three-column workspace that collapses structurally on smaller screens.
- Glass surfaces with inner highlights, not soft drop-shadow cards.
- High-contrast text and semantic warning/error states.
- Standard controls, Lucide icons, and visible focus states.

## 2. Colors

The palette is restrained and operational: cool dark neutrals carry the work surface, signal teal marks primary action and active state, amber and red are reserved for runtime risk.

### Primary
- **Signal Teal** (`--color-accent`): used for primary actions, selected navigation, message role labels, focus outlines, empty-state icons, metric icons, and checkbox accents. It should remain rare enough to signal action.
- **Signal Teal Strong** (`--color-accent-strong`): used as the deeper endpoint of primary button gradients and stronger interactive emphasis.

### Secondary
- **Runtime Amber** (`--color-warning`): used for pending approval surfaces and warning labels. It means operational attention, not general decoration.
- **Danger Red** (`--color-danger`): used for destructive actions and error treatment. It must remain semantic.

### Neutral
- **Console Background** (`--color-background`): the root dark surface and deepest field background.
- **Glass Surface** (`--color-surface`): translucent panel material for sidebar, chat panel, runtime rail, and auth card.
- **Glass Surface Strong** (`--color-surface-strong`): stronger glass layer for elevated or dense surfaces.
- **Foreground** (`--color-foreground`): primary text and icon color.
- **Muted** (`--color-muted`): secondary copy, helper text, metadata, and inactive controls.
- **Hairline Border** (`--color-border`): subtle panel and card borders.

### Named Rules

**The Accent Rarity Rule.** Signal Teal is for primary action, active selection, and state indicators only. Do not use it as ambient decoration across inactive surfaces.

**The Semantic Heat Rule.** Amber and red are reserved for approval, warning, error, and destructive flows. Never reuse them for branding flourishes.

## 3. Typography

**Display Font:** Inter with `ui-sans-serif`, system UI, and Segoe UI fallbacks.
**Body Font:** Inter with the same system fallback stack.
**Label/Mono Font:** No separate mono font is defined in the current UI.

**Character:** The type system is a single-family product scale. It is compact, legible, and familiar; there is no decorative display face because the product should disappear into the work.

### Hierarchy
- **Display**: not currently used. Avoid marketing-scale display typography in product surfaces.
- **Headline** (700, `2rem`, `1.12`): auth heading and panel header titles.
- **Title** (700, `1rem`, `1.35`): section headers, labels, and compact component titles.
- **Body** (400, `1rem`, `1.62`): chat messages, form copy, runtime details, and prose-like helper text. Keep long prose around 65-75ch where possible.
- **Label** (800, `0.78rem`, `1.2`): message roles, eyebrow labels, and compact metadata. Keep casing purposeful; do not turn every section into an uppercase tracked kicker.

### Named Rules

**The One-Family Rule.** Product UI uses one tuned sans family. Do not introduce a display or serif font for labels, buttons, data, or runtime status.

**The Fixed Scale Rule.** Use fixed rem sizes for product surfaces. Avoid fluid `clamp()` headings inside panels, sidebars, and settings screens.

## 4. Elevation

Depth is created with tonal glass layering, thin borders, backdrop blur, and inner highlights. The default surface is not a floating card with a soft external shadow; the cockpit should feel stable, not stacked.

### Shadow Vocabulary
- **Glass Inner Highlight** (`inset 0 1px 0 oklch(1 0 0 / 0.14), inset 0 -1px 0 oklch(0 0 0 / 0.18)`): the standard panel material on `.glass-panel`.
- **Brand Mark Glow** (`0 0 42px oklch(0.78 0.15 183 / 0.28)`): reserved for the bot mark only. Do not apply this glow to cards or panels.

### Named Rules

**The Stable Panel Rule.** Panels use borders, inner highlights, and blur. Do not pair a one-pixel border with a wide decorative drop shadow on cards or buttons.

**The Glass Serves Text Rule.** Backdrop blur is allowed only where foreground text remains comfortably readable.

## 5. Components

### Buttons

Buttons are familiar product controls with clear semantic weight.

- **Shape:** medium rounded rectangle (`12px` radius), minimum height `44px`.
- **Primary:** Signal Teal gradient, dark text, icon plus label, `0 16px` padding, `800` weight.
- **Danger:** red-toned filled button for destructive approval and logout flows.
- **Ghost:** transparent full-width text button for secondary auth-mode switching.
- **Icon:** square `44px` action button with translucent white background for refresh and create-session actions.
- **Hover / Focus:** focus uses a `3px` Signal Teal outline with `3px` offset. Current CSS does not define hover transitions; future additions should stay within 150-250ms and convey state only.

### Chips

The current UI does not use standalone chips. Session pills function as selectable list items and should keep the same shape and active treatment as navigation items.

### Cards / Containers

Glass panels are the major containers: auth card, sidebar, chat panel, runtime rail, and settings panel.

- **Corner Style:** large but controlled (`20px` panels, `22px` auth card, `18px` composer).
- **Background:** translucent glass surface with a subtle white gradient.
- **Shadow Strategy:** inner highlights only, except the brand mark glow.
- **Border:** one-pixel Hairline Border.
- **Internal Padding:** `16px` for rails, `18px` for work panels, `32px` for auth card.

### Inputs / Fields

Inputs are dark recessed controls, not bright form boxes.

- **Style:** one-pixel Hairline Border, `12px` radius, deep console background, foreground text.
- **Focus:** global `:focus-visible` Signal Teal outline.
- **Error / Disabled:** errors use a red border, red-tinted background, and high-contrast error text. Disabled controls lower opacity to `0.58` and switch cursor to `not-allowed`.

### Navigation

Navigation is a quiet left rail with icon-plus-label controls.

- **Default:** muted text on transparent background.
- **Active:** foreground text on a translucent white active fill.
- **Session Pills:** same selected treatment as navigation, with text truncation and chevron affordance.
- **Mobile:** the shell collapses from grid to stacked flex at `760px`; navigation remains above the workspace rather than becoming a modal.

### Agent Workspace

The signature pattern is a chat-centered three-zone cockpit: sidebar for session/navigation, chat panel for primary work, runtime rail for status and approvals.

- **Messages:** max width `min(78%, 760px)` on desktop, `100%` on mobile; user messages align right with Signal Teal tint, assistant messages align left with neutral tint.
- **Composer:** bordered dark container with resizable textarea and primary send button.
- **Approval Card:** amber-tinted inline alert inside the chat flow, with explicit reject and approve buttons.
- **Runtime Rail:** compact metric grid and state sections. Metrics must never dominate the chat task.

## 6. Do's and Don'ts

### Do:

- **Do** keep chat as the center stage and runtime state as a supporting rail.
- **Do** use Signal Teal only for primary action, active state, and state indicators.
- **Do** keep text, code-like content, error messages, and approval reasons high contrast over glass.
- **Do** use Lucide icons or equivalent line icons with accessible labels for icon-only controls.
- **Do** collapse layout structurally at `1120px` and `760px`; do not rely on fluid typography to solve product layout.
- **Do** respect `prefers-reduced-motion` and keep motion tied to state feedback.

### Don't:

- **Don't** make a pure chat skin; it must preserve Agent runtime state, approvals, sessions, jobs, tasks, worktrees, and teammate visibility.
- **Don't** use full-screen translucent glass that makes code, logs, or long text hard to read.
- **Don't** turn the console into a heavy operations dashboard where metric cards overpower the chat task.
- **Don't** add online editing for API keys, model settings, or `.env` secrets in this settings surface.
- **Don't** use emoji as structural icons.
- **Don't** pair one-pixel borders with wide decorative drop shadows, add side-stripe borders, or use gradient text.
