import React from "react";
import Container from "@core/Container/Container";
import SearchBar from "@components/Filter/SearchBar";
import Button from "@core/Button/Button";
import DropDown from "@core/Form/DropDown";
import { REGION_OPTIONS } from "@components/Nabidka/regions";
import { EMPLOYMENT_TYPE_OPTIONS } from "@components/Nabidka/employmentTypes";

const FILTER_FIELD_LABELS = {
    technologies: "Technologie (oddělené čárkou)",
    tools: "Nástroje (oddělené čárkou)",
    methodologies: "Metodiky (oddělené čárkou)",
    semester: "Semestr (ZS, LS)",
};

export default function FilterNabidka({
    filterValue,
    handleFilterChange,
    onSearchClear,
    onSearchSubmit,
    onClearAll,
    hasActiveFilters,
    locations,
    subjects
})

    {

    const durationOptions = [
        { value: "", label: "Všechny" },
        { value: "1", label: "1 semestr" },
        { value: "3", label: "3 měsíce" },
        { value: "6", label: "6 měsíců" },
    ];

    // BL-05 / RF-02a — typ úvazku (závazný číselník, guarantor-values.md §1).
    const employmentTypeOptions = [
        { value: "", label: "Všechny" },
        ...EMPLOYMENT_TYPE_OPTIONS.map((opt) => ({ value: opt.value, label: opt.label })),
    ];

    return (
        <Container property="w-full mb-8">
            {/* PRVNÍ ŘÁDEK - VYHLEDÁVÁNÍ */}
            <Container property="flex items-center justify-center mb-4">
                <SearchBar
                    id="title"
                    value={filterValue?.title}
                    placeholder={"Název"}
                    onChange={handleFilterChange}
                    onClear={() => onSearchClear("title")}
                />
                <Button
                    onClick={onSearchSubmit}
                    noVariant={true}
                    property={"ml-2 bg-facultyColLight px-4 py-1 border border-black rounded-lg transition-colors duration-200 hover:bg-facultyCol"}
                >
                    {"Hledat"}
                </Button>
            </Container>

            {/* FILTRY V JEDNOM ŘÁDKU */}
            <Container property="flex flex-row items-center justify-center gap-6 mb-4 inline-block">
                <Container property={"w-full mt-6"}>
                    <SearchBar
                        id="address"
                        value={filterValue?.address}
                        placeholder={"Adresa"}
                        onChange={(val) => handleFilterChange(null, "address", val.target.value, true)}
                        onClear={() => onSearchClear("address")}
                    />
                </Container>

                <Container property={"w-full mt-6"}>
                    <SearchBar
                        id="skills"
                        value={filterValue?.skills}
                        placeholder={"Dovednosti"}
                        onChange={(val) => handleFilterChange(null, "skills", val.target.value, true)}
                        onClear={() => onSearchClear("skills")}
                    />
                </Container>

                <DropDown
                    id="subject"
                    label={"Předmět:"}
                    value={filterValue?.subject}
                    placeholder={"Všechny"}
                    variant="facultyGreen"
                    options={subjects}
                    onChange={(dict) => handleFilterChange(null, "subject", dict.subject, true)}
                    property="w-32"
                />

                {/* FILTR KRAJE */}
                <Container property="w-full mt-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        {"Kraj"}:
                    </label>
                    <select
                        id="region"
                        value={filterValue?.region || ""}
                        onChange={(e) => {
                            const val = e.target.value;
                            if (!val) {
                                onSearchClear("region");
                            } else {
                                handleFilterChange(null, "region", val, true);
                            }
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">{"Všechny"}</option>
                        {REGION_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </Container>

                {/* FILTR LOKALITY */}
                <Container property="w-full mt-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        {"Lokalita"}:
                    </label>
                    <select
                        id="city"
                        value={filterValue?.city || ""}
                        onChange={(e) => {
                            const val = e.target.value;
                            if (!val) {
                                onSearchClear("city");
                            } else {
                                handleFilterChange(null, "city", val, true);
                            }
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">{"Všechny"}</option>
                        {(locations || []).map((loc) => (
                            <option key={loc} value={loc}>
                                {loc}
                            </option>
                        ))}
                    </select>
                </Container>

                {/* FILTR DÉLKY */}
                <Container property="w-full mt-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        {"Délka"}:
                    </label>
                    <select
                        id="duration"
                        value={filterValue?.duration || ""}
                        onChange={(e) => {
                            const val = e.target.value;
                            if (!val) {
                                onSearchClear("min_duration");
                                onSearchClear("max_duration");
                                onSearchClear("duration");
                            } else {
                                handleFilterChange(null, "min_duration", "1", true);
                                handleFilterChange(null, "max_duration", val, true);
                                handleFilterChange(null, "duration", val, true);
                            }
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        {durationOptions.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </Container>

                {/* FILTR ÚVAZKU — BL-05 / RF-02a (závazný číselník, guarantor-values.md §1) */}
                <Container property="w-full mt-6">
                    <label htmlFor="employment_type" className="block text-sm font-medium text-gray-700 mb-1">
                        {"Typ úvazku"}:
                    </label>
                    <select
                        id="employment_type"
                        value={filterValue?.employment_type || ""}
                        onChange={(e) => {
                            const val = e.target.value;
                            if (!val) {
                                onSearchClear("employment_type");
                            } else {
                                handleFilterChange(null, "employment_type", val, true);
                            }
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        {employmentTypeOptions.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </Container>

                {['technologies', 'tools', 'methodologies', 'semester'].map((field) => (
                    <Container key={field} property="w-full mt-4">
                        <label htmlFor={field} className="block text-sm font-medium text-gray-700 mb-1">
                            {FILTER_FIELD_LABELS[field]}
                        </label>
                        <input id={field} type="text" value={filterValue?.[field] || ""}
                            placeholder={field === 'semester' ? 'ZS, LS' : "Hodnoty oddělené čárkou"}
                            onChange={(event) => handleFilterChange(null, field, event.target.value, true)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm" />
                    </Container>
                ))}

                {/* FILTR KAPACITY */}
                <Container property="w-full mt-6 flex items-center gap-2">
                    <input
                        id="has_capacity"
                        type="checkbox"
                        checked={filterValue?.has_capacity === "true"}
                        onChange={(e) => {
                            if (e.target.checked) {
                                handleFilterChange(null, "has_capacity", "true", true);
                            } else {
                                onSearchClear("has_capacity");
                            }
                        }}
                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <label htmlFor="has_capacity" className="text-sm text-gray-700">
                        {"Pouze s volnou kapacitou"}
                    </label>
                </Container>
            </Container>

            <Container property="border-t border-gray-300 my-4"></Container>

            {/* CLEAR FILTERS */}
            {hasActiveFilters && (
                <Container property="flex justify-end mb-2">
                    <Button
                        variant="red"
                        property="text-sm px-4 py-1.5"
                        onClick={onClearAll}
                    >
                        {"Zrušit všechny filtry"}
                    </Button>
                </Container>
            )}

        </Container>
    )
}
