/**
 * Zobrazí chybovou hlášku z apiClient normalizované chyby (BL-04 / FE-002,
 * kapacita na apply/reapply cestě).
 *
 * apiClient nastavuje:
 *  - error.code       = error_code ze serveru (např. CAPACITY_FULL), jinak
 *                       "DRF_ERROR" pokud server poslal `detail`, jinak
 *                       "UNKNOWN_ERROR" / "SERVER_UNREACHABLE" / "NETWORK_ERROR"
 *  - error.details    = `details` ze serveru
 *  - error.responseData = celý payload odpovědi
 *
 * Pořadí:
 *  1) český text ze serveru (`details` / `responseData.detail`)
 *  2) kontextový fallback stránky
 *  3) obecná hláška
 *
 * Tokeny velkými písmeny (CAPACITY_FULL) se nezobrazují; místo nich se použije
 * fallback stránky.
 */
const TOKEN_RE = /^[A-Z][A-Z0-9_]+$/;

export function getApiErrorMessage(error, fallbackMessage) {
    const serverDetail =
        (typeof error?.details === "string" && error.details) ||
        (typeof error?.details?.detail === "string" && error.details.detail) ||
        (typeof error?.responseData?.detail === "string" && error.responseData.detail) ||
        null;

    if (serverDetail && !TOKEN_RE.test(serverDetail)) {
        return serverDetail;
    }

    if (fallbackMessage) return fallbackMessage;

    return "Došlo k neočekávané chybě serveru.";
}

export default getApiErrorMessage;
