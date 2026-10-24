import React from "react";
import { useTranslation } from "react-i18next";

/**
 * Maps workflow_state / progress_status values to translation keys.
 * Central single source of truth — replaces ad-hoc statusToText/statusVariant patterns.
 *
 * Translations live in public/locales/cs/translation.json under "state_badge"
 * (exists only for `cs`; no `en` file). Kanonické labely inzerce:
 * OPEN_FOR_APPLICATIONS → "Aktivní", CLOSED_FOR_APPLICATIONS → "Uzavřeno".
 * POZOR: Practice stavy (PENDING_CONTENT_APPROVAL..CLOSED_FOR_APPLICATIONS)
 * ≠ StudentPractice stavy (APPLIED..CONTENT_APPROVED) — toto je pro Practice.
 */
export function getStateLabelKey(status) {
  const keyMap = {
    // Integer values from django_enumfield / DRF
    0: "state_badge.APPLIED",
    1: "state_badge.PRELIMINARY_APPROVED",
    2: "state_badge.REJECTED",
    3: "state_badge.CONTRACTED",
    4: "state_badge.STARTED",
    5: "state_badge.ENDED",
    6: "state_badge.COMPLETED",
    7: "state_badge.AWAITING_CONTRACT",
    8: "state_badge.AWAITING_DOCUMENTS",
    9: "state_badge.DOCUMENTS_REJECTED",
    10: "state_badge.AWAITING_CONTENT_APPROVAL",
    11: "state_badge.CONTENT_REJECTED",
    12: "state_badge.CONTENT_APPROVED",
    13: "state_badge.DOCUMENTS_RESUBMITTED",

    // String keys
    DRAFT: "state_badge.DRAFT",
    PENDING_CONTENT_APPROVAL: "state_badge.PENDING_CONTENT_APPROVAL",
    CONTENT_APPROVED: "state_badge.CONTENT_APPROVED",
    CONTENT_REJECTED: "state_badge.CONTENT_REJECTED",
    OPEN_FOR_APPLICATIONS: "state_badge.OPEN_FOR_APPLICATIONS",
    CLOSED_FOR_APPLICATIONS: "state_badge.CLOSED_FOR_APPLICATIONS",

    APPLIED: "state_badge.APPLIED",
    PRELIMINARY_APPROVED: "state_badge.PRELIMINARY_APPROVED",
    REJECTED: "state_badge.REJECTED",
    CONTRACTED: "state_badge.CONTRACTED",
    STARTED: "state_badge.STARTED",
    ENDED: "state_badge.ENDED",
    COMPLETED: "state_badge.COMPLETED",
    CANCELLED: "state_badge.CANCELLED",

    AWAITING_CONTRACT: "state_badge.AWAITING_CONTRACT",
    AWAITING_DOCUMENTS: "state_badge.AWAITING_DOCUMENTS",
    DOCUMENTS_REJECTED: "state_badge.DOCUMENTS_REJECTED",
    DOCUMENTS_RESUBMITTED: "state_badge.DOCUMENTS_RESUBMITTED",
    AWAITING_CONTENT_APPROVAL: "state_badge.AWAITING_CONTENT_APPROVAL",

    // Legacy / approval_status
    PENDING: "state_badge.PENDING",
    APPROVED: "state_badge.APPROVED",
    IN_PROGRESS: "state_badge.IN_PROGRESS",
  };
  return (
    keyMap[status] || (status !== undefined && status !== null ? `state_badge.${status}` : "state_badge.UNKNOWN")
  );
}

/**
 * Maps status to Button variant (color).
 */
export function getStateVariant(status) {
  const warning = [
    "PENDING",
    "PENDING_CONTENT_APPROVAL",
    "AWAITING_CONTENT_APPROVAL",
    "PRELIMINARY_APPROVED",
    "AWAITING_CONTRACT",
    "AWAITING_DOCUMENTS",
    "DOCUMENTS_RESUBMITTED",
    "CLOSED_FOR_APPLICATIONS",
    1,
    7,
    8,
    10,
    13,
  ];
  const success = [
    "APPROVED",
    "CONTENT_APPROVED",
    "CONTRACTED",
    "COMPLETED",
    3,
    6,
    12,
  ];
  const danger = ["REJECTED", "CONTENT_REJECTED", "DOCUMENTS_REJECTED", "CANCELLED", 2, 9, 11];
  const active = ["OPEN_FOR_APPLICATIONS", "IN_PROGRESS", "STARTED", 4, 5];
  const neutral = ["DRAFT", "APPLIED", "ENDED", 0];

  if (warning.includes(status)) return "yellow";
  if (success.includes(status)) return "green";
  if (danger.includes(status)) return "red";
  if (active.includes(status)) return "blue";
  if (neutral.includes(status)) return "blueSmallNoHover";
  return "blueSmallNoHover";
}

/**
 * Reusable badge component for displaying workflow state.
 * Usage: <StateBadge status={entity.workflow_state} />
 */
export default function StateBadge({ status, property = "" }) {
  const { t } = useTranslation();
  const labelKey = getStateLabelKey(status);
  const label = t(labelKey);
  const variant = getStateVariant(status);

  const variantClassMap = {
    yellow: "bg-yellow-300 text-white px-4 py-2 rounded-lg",
    green: "bg-green-300 text-white px-4 py-2 rounded-lg",
    red: "bg-red-400 text-white px-4 py-2 rounded-lg",
    blue: "bg-blue-300 text-white px-4 py-2 rounded-lg",
    blueSmallNoHover: "bg-blue-300 text-gray-800 px-2 py-1 rounded-lg",
  };

  return (
    <span
      className={`${variantClassMap[variant] || variantClassMap.blueSmallNoHover} text-xs ${property}`}
    >
      {label}
    </span>
  );
}
