// BL-05 / RF-02a — „typ úvazku" (employment type) filtr katalogu nabídek.
//
// ZÁVAZNÝ číselník dle rozhodnutí garantů/vlastníka 2026-10-11
// (audit/2026-10-04/lanes/guarantor-values.md §1, C21-A): numerická osa
// „Úvazek 0,5" / „Úvazek 1,0". PLACEHOLDER kódy (`placeholder_*`) byly
// staženy; hodnoty `value` odpovídají backendovému EMPLOYMENT_TYPE_CHOICES
// v backend/practices/models.py (uložené hodnoty normalizuje datová
// migrace 0014_practice_employment_type_codes). Další hodnoty se
// nepřidávají bez nového garantského rozhodnutí.
export const EMPLOYMENT_TYPE_OPTIONS = [
    { value: "uvazek_0_5", labelKey: "offers.filter.employment_type_part_time" },
    { value: "uvazek_1_0", labelKey: "offers.filter.employment_type_full_time" },
];
