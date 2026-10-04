/**
 * Kraje ČR pro nabídky praxí.
 *
 * Hodnoty (kódy krajů) se posílají v payloadu nabídky (`Practice.region`)
 * i jako query parametr `region` v katalogovém filtru (`FilterNabidka`).
 * Labely jsou kanonické české názvy krajů.
 */
export const REGION_OPTIONS = [
    { value: "PHA", label: "Hlavní město Praha" },
    { value: "STC", label: "Středočeský kraj" },
    { value: "JHC", label: "Jihočeský kraj" },
    { value: "PLK", label: "Plzeňský kraj" },
    { value: "KVK", label: "Karlovarský kraj" },
    { value: "ULK", label: "Ústecký kraj" },
    { value: "LBK", label: "Liberecký kraj" },
    { value: "HKK", label: "Královéhradecký kraj" },
    { value: "PAK", label: "Pardubický kraj" },
    { value: "OLK", label: "Olomoucký kraj" },
    { value: "MSK", label: "Moravskoslezský kraj" },
    { value: "JHM", label: "Jihomoravský kraj" },
    { value: "ZLK", label: "Zlínský kraj" },
    { value: "VYS", label: "Kraj Vysočina" },
];
