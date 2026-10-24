/**
 * Překlad chybových hlášek z apiClient normalizované chyby (BL-04 / FE-002,
 * kapacita na apply/reapply cestě).
 *
 * apiClient nastavuje:
 *  - error.code       = error_code ze serveru (např. CAPACITY_FULL), jinak
 *                       "DRF_ERROR" pokud server poslal `detail`, jinak
 *                       "UNKNOWN_ERROR" / "SERVER_UNREACHABLE" / "NETWORK_ERROR"
 *  - error.details    = `details` ze serveru (capacity chyby vracejí `detail`,
 *                       proto je zde často null)
 *  - error.responseData = celý payload odpovědi
 *
 * Pořadí:
 *  1) konkrétní překlad pro error.code (kromě generických kódů)
 *  2) serverový `detail`/`details` — token s vlastním překladem
 *     (KAPACITA_NAPLNENA, CAPACITY_FULL, …) nebo česká věta ze serveru
 *  3) fallback klíč stránky
 *  4) překlad pro error.code (i generický), jinak UNKNOWN_ERROR
 *
 * `lookup` řeší i testovací mocky t(), které vracejí klíč — chybějící
 * překlad se pozná podle toho, že výsledek == klíč.
 */
const GENERIC_CODES = new Set(["DRF_ERROR", "UNKNOWN_ERROR", "VALIDATION_ERROR"]);

export function getApiErrorMessage(error, t, fallbackKey) {
    const code = error?.code || "UNKNOWN_ERROR";

    const lookup = (key) => {
        try {
            const value = t(key);
            return value && value !== key ? value : null;
        } catch {
            return null;
        }
    };

    const forCode = lookup(`api_errors.${code}`);
    if (forCode && !GENERIC_CODES.has(code)) {
        return forCode;
    }

    const serverDetail =
        (typeof error?.details === "string" && error.details) ||
        (typeof error?.responseData?.detail === "string" && error.responseData.detail) ||
        null;

    if (serverDetail) {
        const forDetail = lookup(`api_errors.${serverDetail}`);
        if (forDetail) return forDetail;
        // česká věta ze serveru (obsahuje mezery) — zobrazit přímo
        if (/\s/.test(serverDetail)) return serverDetail;
    }

    // kontextový fallback stránky před generickým překladem kódu
    const fallback = lookup(fallbackKey);
    if (fallback) return fallback;

    if (forCode) return forCode;

    return lookup("api_errors.UNKNOWN_ERROR") || fallbackKey || "UNKNOWN_ERROR";
}

export default getApiErrorMessage;
