import React from "react";
import { useTranslation } from "react-i18next";

/**
 * Maps workflow_state / progress_status values to translation keys.
 * Central single source of truth — replaces ad-hoc statusToText/statusVariant patterns.
 *
 * Translations live in public/locales/{cs,en}/translation.json under "state_badge".
 */
export function getStateLabelKey(status) {
  const keyMap = {
    // Practice workflow states (integer values from django_enumfield)
    0: "state_badge.PENDING_CONTENT_APPROVAL",
    1: "state_badge.CONTENT_APPROVED",
    2: "state_badge.CONTENT_REJECTED",
    3: "state_badge.OPEN_FOR_APPLICATIONS",
    4: "state_badge.CLOSED_FOR_APPLICATIONS",
    // String fallbacks (for back-compat if any API still sends strings)
    DRAFT: "state_badge.DRAFT",
    PENDING_CONTENT_APPROVAL: "state_badge.PENDING_CONTENT_APPROVAL",
    CONTENT_APPROVED: "state_badge.CONTENT_APPROVED",
    CONTENT_REJECTED: "state_badge.CONTENT_REJECTED",
    OPEN_FOR_APPLICATIONS: "state_badge.OPEN_FOR_APPLICATIONS",
    CLOSED_FOR_APPLICATIONS: "state_badge.CLOSED_FOR_APPLICATIONS",
    // StudentPractice workflow states
    APPLIED: "state_badge.APPLIED",
    PRELIMINARY_APPROVED: "state_badge.PRELIMINARY_APPROVED",
    REJECTED: "state_badge.REJECTED",
    CONTRACTED: "state_badge.CONTRACTED",
    STARTED: "state_badge.STARTED",
    COMPLETED: "state_badge.COMPLETED",
    CANCELLED: "state_badge.CANCELLED",
    // Legacy / approval_status
    PENDING: "state_badge.PENDING",
    APPROVED: "state_badge.APPROVED",
    IN_PROGRESS: "state_badge.IN_PROGRESS",
  };
  return (
    keyMap[status] || (status ? `state_badge.UNKNOWN` : "state_badge.UNKNOWN")
  );
}

/**
 * Maps status to Button variant (color).
 */
export function getStateVariant(status) {
  const warning = [
    "PENDING",
    "PENDING_CONTENT_APPROVAL",
    "PRELIMINARY_APPROVED",
    "CLOSED_FOR_APPLICATIONS",
    0,
    4,
  ];
  const success = [
    "APPROVED",
    "CONTENT_APPROVED",
    "CONTRACTED",
    "COMPLETED",
    1,
  ];
  const danger = ["REJECTED", "CONTENT_REJECTED", "CANCELLED", 2];
  const active = ["OPEN_FOR_APPLICATIONS", "IN_PROGRESS", "STARTED", 3];
  const neutral = ["DRAFT", "APPLIED"];

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
