import { describe, it, expect } from 'vitest'
import config from '../../tailwind.config.js'

function luminance(hex) {
  const rgb = hex.match(/[a-f\d]{2}/gi).map(v => parseInt(v, 16) / 255)
    .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722
}
function contrast(a, b) {
  const values = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (values[0] + 0.05) / (values[1] + 0.05)
}
describe('theme text contrast', () => {
  const { gray, dark, primary } = config.theme.extend.colors
  it('keeps normal and muted light text at AA contrast', () => {
    for (const text of [gray[400], gray[500], gray[900], primary[500], primary[600], primary[700]]) {
      for (const background of ['#ffffff', gray[50], gray[100]]) {
        expect(contrast(text, background), `${text} on ${background}`).toBeGreaterThanOrEqual(4.5)
      }
    }
  })
  it('keeps dark theme table text legible across nested surfaces', () => {
    for (const text of [dark[100], dark[300], dark[400], dark[500], primary[400]]) {
      for (const background of [dark[800], dark[900], dark[950]]) {
        expect(contrast(text, background), `${text} on ${background}`).toBeGreaterThanOrEqual(4.5)
      }
    }
  })
  it('uses dark text on lime actions and readable white text on forest fills', () => {
    expect(contrast('#15220c', primary[400])).toBeGreaterThanOrEqual(7)
    expect(contrast('#ffffff', primary[600])).toBeGreaterThanOrEqual(4.5)
  })
})
