/* Tag chip styling: pick readable text for arbitrary tag background colors. */

// WCAG relative luminance for a channel value (0-255).
const channelLuminance = (c) => {
  const s = c / 255
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
}

const relativeLuminance = (r, g, b) =>
  0.2126 * channelLuminance(r) + 0.7152 * channelLuminance(g) + 0.0722 * channelLuminance(b)

// Contrast of black vs white text crosses over near luminance 0.179:
// lighter backgrounds get black text, darker ones get white text.
const isLightBackground = (r, g, b) => relativeLuminance(r, g, b) > 0.179

/**
 * Inline style for a tag chip with the given color.
 * - No color: accent fill, text color comes from --on-accent in the stylesheet.
 * - Hex color: keep it, and select black/white text by WCAG contrast.
 * - Unparseable color: fall back to the accent treatment.
 */
export const tagChipStyle = (color) => {
  if (!color) {
    return { backgroundColor: 'var(--accent)' }
  }
  const hex = color.replace('#', '')
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
    return { backgroundColor: 'var(--accent)' }
  }
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  return {
    backgroundColor: color,
    color: isLightBackground(r, g, b) ? 'black' : 'white'
  }
}
