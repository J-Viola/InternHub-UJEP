/**
 * Odvození stavu StudentPractice workflow pro UI (BL-04).
 *
 * A-12 (okamžité storno studentem) a C19-B/T2c (repair loop) jsou backendové
 * stavy, které FE potřebuje zobrazit bez zásahu do designu.
 */

/**
 * Je praxe stornovaná studentem a garant storno ještě nevzal na vědomí (A-12)?
 *
 * Storno studentem je okamžité a nevratné (`is_cancelled=true`); příznak
 * `cancellation_requested_at` ho odlišuje od stornování nabídky/garantem a
 * `cancellation_resolved_at` značí „vzato na vědomí“. Dokud chybí, backend
 * blokuje studentovi podání nové žádosti.
 */
export function isCancellationPending(entity) {
    if (!entity?.is_cancelled) return false;
    return Boolean(entity.cancellation_requested_at) && !entity.cancellation_resolved_at;
}

/**
 * Student může praxi stornovat jen ze stavu CONTRACTED; z APPLIED /
 * PRELIMINARY_APPROVED má vlastní akci „stáhnout přihlášku“ (withdraw).
 * Storno je nevratné (RF-16) a okamžité (BDD UC05 AC-02).
 */
export function canRequestCancellation(entity, user) {
    if (!entity?.student_practice_status || !user?.isStudent?.()) return false;
    if (entity.is_cancelled) return false;
    return entity.student_practice_status.workflow_status === "CONTRACTED";
}

/**
 * Kdo smí vzít storno na vědomí (A-12): garant katedry (VY/VK) nebo
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
