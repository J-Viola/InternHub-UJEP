import React from "react";

/**
 * Maps workflow_state / progress_status values to Czech labels.
 * Central single source of truth — replaces ad-hoc statusToText/statusVariant patterns.
 *
 * Kanonické labely inzerce:
 * OPEN_FOR_APPLICATIONS → "Aktivní", CLOSED_FOR_APPLICATIONS → "Uzavřeno".
 * POZOR: Practice stavy (PENDING_CONTENT_APPROVAL..CLOSED_FOR_APPLICATIONS)
 * ≠ StudentPractice stavy (APPLIED..CONTENT_APPROVED) — toto je pro Practice.
 */
export function getStateLabel(status) {
  const keyMap = {
    // Integer values from django_enumfield / DRF
    0: "Čeká na schválení garanta",
    1: "Čeká na schválení organizací",
    2: "Přihláška na praxi odmítnuta",
    3: "Zasmluvněno",
    4: "Zahájeno",
    5: "Ukončeno",
    6: "Splněno",
    7: "Čeká na zasmluvnění",
    8: "Čeká na schválení dokumentů",
    9: "Dokumenty zamítnuty",
    10: "Čeká na schválení obsahu",
    11: "Zamítnutí obsahu",
    12: "Obsah praxe schválen",
    13: "Opravené dokumenty čekají na kontrolu",

    // String keys
    DRAFT: "Koncept",
    PENDING_CONTENT_APPROVAL: "Čeká na schválení obsahu",
    CONTENT_APPROVED: "Obsah praxe schválen",
    CONTENT_REJECTED: "Zamítnutí obsahu",
    OPEN_FOR_APPLICATIONS: "Aktivní",
    CLOSED_FOR_APPLICATIONS: "Uzavřeno",

    APPLIED: "Čeká na schválení garanta",
    PRELIMINARY_APPROVED: "Čeká na schválení organizací",
    REJECTED: "Přihláška na praxi odmítnuta",
    CONTRACTED: "Zasmluvněno",
    STARTED: "Zahájeno",
    ENDED: "Ukončeno",
    COMPLETED: "Splněno",
    CANCELLED: "Stornováno",

    AWAITING_CONTRACT: "Čeká na zasmluvnění",
    AWAITING_DOCUMENTS: "Čeká na schválení dokumentů",
    DOCUMENTS_REJECTED: "Dokumenty zamítnuty",
    DOCUMENTS_RESUBMITTED: "Opravené dokumenty čekají na kontrolu",
    AWAITING_CONTENT_APPROVAL: "Čeká na schválení obsahu",

    // Legacy / approval_status
    PENDING: "Čeká na schválení",
    APPROVED: "Schváleno",
    IN_PROGRESS: "Probíhá",
  };
  return (
    keyMap[status] || (status !== undefined && status !== null ? `state_badge.${status}` : "Neznámý")
  );
}

/**
 * Převede číselný workflow_state NABÍDKY (Practice) na název stavu.
 * Číselná mapa getStateLabel odpovídá stavům přihlášky, proto se čísla nabídky
 * musí před předáním do StateBadge přeložit.
 */
const PRACTICE_STATE_NAMES = [
  "PENDING_CONTENT_APPROVAL",
  "CONTENT_APPROVED",
  "CONTENT_REJECTED",
  "OPEN_FOR_APPLICATIONS",
  "CLOSED_FOR_APPLICATIONS",
];
export function practiceStateName(state) {
  return typeof state === "number" ? PRACTICE_STATE_NAMES[state] ?? state : state;
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
  const label = getStateLabel(status);
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
