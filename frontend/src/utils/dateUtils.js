/**
 * Shared date utilities for InternHub frontend.
 *
 * Backend serializers may return dates in DD.MM.YYYY HH:MM format (Czech locale).
 * Always prefer ISO 8601 from the API (YYYY-MM-DD or YYYY-MM-DDTHH:mm:ss),
 * but when DD.MM.YYYY is unavoidable, use parseCzechDateTime().
 */

/**
 * Parse a Czech-locale date string "DD.MM.YYYY HH:MM" into a Date object.
 * Returns null for falsy, empty, or unparseable input.
 *
 * @param {string|null|undefined} dateStr — e.g. "25.12.2024 14:30" or "25.12.2024"
 * @returns {Date|null}
 */
export function parseCzechDateTime(dateStr) {
  if (!dateStr) return null;
  const parts = dateStr.split(" ");
  const dateParts = parts[0].split(".");
  if (dateParts.length < 3) return null;

  const day = parseInt(dateParts[0], 10);
  const month = parseInt(dateParts[1], 10) - 1; // JS months are 0-indexed
  const year = parseInt(dateParts[2], 10);
  if (isNaN(day) || isNaN(month) || isNaN(year)) return null;

  if (parts[1]) {
    const timeParts = parts[1].split(":");
    const hours = parseInt(timeParts[0], 10);
    const minutes = parseInt(timeParts[1], 10);
    return new Date(year, month, day, hours || 0, minutes || 0);
  }
  return new Date(year, month, day);
}

/**
 * Compute the number of full days between a parsed Czech date and now.
 * Returns 0 when dateStr is null/unparseable.
 *
 * @param {string|null|undefined} dateStr
 * @returns {number} days elapsed (rounded up)
 */
export function daysSinceCzechDate(dateStr) {
  const date = parseCzechDateTime(dateStr);
  if (!date) return 0;
  const now = new Date();
  return Math.ceil(Math.abs(now - date) / (1000 * 60 * 60 * 24));
}

/**
 * Returns true if the given Czech date string is older than `thresholdDays` days.
 *
 * @param {string|null|undefined} dateStr
 * @param {number} thresholdDays
 * @returns {boolean}
 */
export function isOlderThan(dateStr, thresholdDays) {
  return daysSinceCzechDate(dateStr) > thresholdDays;
}
