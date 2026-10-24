/**
 * Odvození stavu StudentPractice workflow pro UI (BL-04).
 *
 * C02-A/C03-A (cancellation request) a C19-B/T2c (repair loop) jsou backendové
 * stavy, které FE potřebuje zobrazit bez zásahu do designu.
 */

/**
 * Je podána nevyřízená žádost o storno (C02-A)?
 *
 * Preferovaná cesta jsou explicitní pole `cancellation_requested_at` +
 * `cancellation_resolved_at`, která modeluje backend (BL-03). Tyto sloupce
 * zatím žádný serializer nevydává (hlášeno jako backend gap BL-04), proto
 * fallback: `cancellation_reason` vyplněné + `is_cancelled=false` +
 * `cancelled_at` prázdné = žádost o storno podána a ještě nerozhodnuta.
 *
 * Po rozhodnutí „zamítnout“ zůstává `cancellation_reason` zaplněné, dokud
 * backend nevydá `cancellation_resolved_at` — do té doby UI ukazuje pending
 * state konzervativně a server odmítne druhé rozhodnutí čistým 400.
 */
export function isCancellationPending(entity) {
    if (!entity) return false;
    if (entity.is_cancelled) return false;

    if (
        Object.prototype.hasOwnProperty.call(entity, "cancellation_requested_at") &&
        entity.cancellation_requested_at !== null &&
        entity.cancellation_requested_at !== undefined
    ) {
        return (
            entity.cancellation_resolved_at === null ||
            entity.cancellation_resolved_at === undefined
        );
    }

    // Fallback bez explicitních polí (viz hlášený backend gap)
    return Boolean(entity.cancellation_reason) && !entity.cancelled_at;
}

/**
 * Studen může požádat o storno jen z aktivních stavů, které backend
 * připouští pro vlastníka (APPLIED / PRELIMINARY_APPROVED / CONTRACTED).
 * APPLIED/PRELIMINARY mají vlastní akci „stáhnout přihlášku“ (withdraw),
 * proto UI nabízí žádost o storno až ze Zasmluvněno (CONTRACTED).
 */
export function canRequestCancellation(entity, user) {
    if (!entity?.student_practice_status || !user?.isStudent?.()) return false;
    if (isCancellationPending(entity)) return false;
    return entity.student_practice_status.workflow_status === "CONTRACTED";
}

/**
 * Kdo smí rozhodnout o žádosti o storno (T2d): garant katedry (VY/VK) nebo
 * admin. Odpovídá backendovému IsGarantForStudentPractice + superuser;
 * objektovou kontrolu katedry vždy provádí server.
 */
export function canResolveCancellation(user) {
    if (!user) return false;
    return Boolean(user.isDepartmentUser?.() || user.isAdmin?.());
}

/**
 * Kdo smí rozhodnout o review-pending stavu DOCUMENTS_RESUBMITTED (C19-B/T2c):
 * garant/škola (VY/VK) nebo admin — shodné s DocsPanel rolí pro review.
 */
export function canReviewResubmittedDocuments(user) {
    if (!user) return false;
    return Boolean(user.isDepartmentUser?.() || user.isAdmin?.());
}

/**
 * Kdo smí provést terminální REJECTED z opravného cyklu (T2c/R44):
 * výhradně administrátor (server vynucuje is_superuser/is_staff + důvod).
 */
export function canTerminalReject(user) {
    if (!user) return false;
    return Boolean(user.isAdmin?.());
}

export default {
    isCancellationPending,
    canRequestCancellation,
    canResolveCancellation,
    canReviewResubmittedDocuments,
    canTerminalReject,
};
