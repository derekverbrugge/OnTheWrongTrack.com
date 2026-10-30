/**
 * Sync On the Wrong Track designs from the private Google Calendar iCal feed.
 * Requires CALENDAR_ICAL_URL (GitHub Actions secret). Never commit that URL.
 * Run: npm install --no-save ical.js && node scripts/sync-designs.mjs
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import ICAL from 'ical.js';

const output = path.resolve('designs.json');
const linkRe = /https?:\/\/creatorsclub\.dovetailgames\.com\/(?:creations|mods)\/\d+/i;
const imageRe = /https?:\/\/screenshot-prod\.dovetailgames\.net\/[\w-]+/i;
const url = process.env.CALENDAR_ICAL_URL?.trim();
if (!url || !url.startsWith('https://')) throw new Error('Missing CALENDAR_ICAL_URL GitHub Actions secret');

function clean(s) {
  return String(s || '').replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, ' ').trim();
}
function titleFrom(description) {
  const line = description.split(/\r?\n/).find(s => s.trim() && !/^\s*(?:https?:|#)/i.test(s));
  return clean((line || 'Train Sim World design').split(/\s+#(?:TSW|USA|Germany|BR\d)/i)[0]);
}
function isoDate(value) {
  if (!value) return '';
  return String(value.toString()).slice(0, 10);
}
function isoTimestamp(value) {
  if (!value) return '';
  try { return value.toJSDate().toISOString(); } catch { return ''; }
}
const response = await fetch(url, { headers: { 'User-Agent': 'OnTheWrongTrack-CalendarSync/1.0' }, signal: AbortSignal.timeout(35000) });
if (!response.ok) throw new Error('Calendar fetch failed: HTTP ' + response.status);
const calendar = new ICAL.Component(ICAL.parse(await response.text()));
const events = calendar.getAllSubcomponents('vevent');
const previous = JSON.parse(await fs.readFile(output, 'utf8').catch(() => '[]'));
const byUrl = new Map(previous.map(d => [d.url, d]));
const found = new Map();
for (const event of events) {
  if (String(event.getFirstPropertyValue('status') || '').toUpperCase() === 'CANCELLED') continue;
  const description = String(event.getFirstPropertyValue('description') || '');
  const summary = String(event.getFirstPropertyValue('summary') || '');
  const link = (description + ' ' + summary).match(linkRe)?.[0];
  const image = (summary + ' ' + description).match(imageRe)?.[0];
  if (!link || !image) continue; // Never expose unrelated calendar events
  const old = byUrl.get(link) || {};
  const title = titleFrom(description);
  const modified = isoTimestamp(event.getFirstPropertyValue('last-modified'));
  const changed = !old.url || old.title !== title || old.image !== image;
  const updated = changed ? (modified || new Date().toISOString())
    : (modified && modified > (old.calendar_modified_at || '') ? modified : old.updated_at || modified);
  const item = {
    title,
    date: old.date || isoDate(event.getFirstPropertyValue('dtstart')),
    url: link,
    image,
    updated_at: updated,
    calendar_modified_at: modified
  };
  if (!found.has(link) || item.updated_at > found.get(link).updated_at) found.set(link, item);
}
if (!found.size) throw new Error('No matching TSW designs found; existing gallery left unchanged.');
const result = [...found.values()].sort((a, b) => b.updated_at.localeCompare(a.updated_at) || a.url.localeCompare(b.url));
await fs.writeFile(output, JSON.stringify(result, null, 2) + '\n', 'utf8');
console.log('Synchronized ' + result.length + ' designs from Google Calendar.');
