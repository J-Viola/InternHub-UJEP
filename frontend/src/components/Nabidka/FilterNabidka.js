import React from "react";
import Container from "@core/Container/Container";
import SearchBar from "@components/Filter/SearchBar";
import Button from "@core/Button/Button";
import DropDown from "@core/Form/DropDown";
import { useTranslation } from "react-i18next";
import { REGION_OPTIONS } from "@components/Nabidka/regions";

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
    const { t } = useTranslation();

    const durationOptions = [
        { value: "", label: t('offers.filter.all') },
        { value: "1", label: t('offers.filter.duration_1') },
        { value: "3", label: t('offers.filter.duration_3') },
        { value: "6", label: t('offers.filter.duration_6') },
    ];

    return (
        <Container property="w-full mb-8">
            {/* PRVNÍ ŘÁDEK - VYHLEDÁVÁNÍ */}
            <Container property="flex items-center justify-center mb-4">
                <SearchBar
                    id="title"
                    value={filterValue?.title}
                    placeholder={t('offers.filter.name')}
                    onChange={handleFilterChange}
                    onClear={() => onSearchClear("title")}
                />
                <Button
                    onClick={onSearchSubmit}
                    noVariant={true}
                    property={"ml-2 bg-facultyColLight px-4 py-1 border border-black rounded-lg transition-colors duration-200 hover:bg-facultyCol"}
                >
                    {t('common.search')}
                </Button>
            </Container>

            {/* FILTRY V JEDNOM ŘÁDKU */}
            <Container property="flex flex-row items-center justify-center gap-6 mb-4 inline-block">
                <Container property={"w-full mt-6"}>
                    <SearchBar
                        id="address"
                        value={filterValue?.address}
                        placeholder={t('offers.filter.address')}
                        onChange={(val) => handleFilterChange(null, "address", val.target.value, true)}
                        onClear={() => onSearchClear("address")}
                    />
                </Container>

                <Container property={"w-full mt-6"}>
                    <SearchBar
                        id="skills"
                        value={filterValue?.skills}
                        placeholder={t('profile.skills')}
                        onChange={(val) => handleFilterChange(null, "skills", val.target.value, true)}
                        onClear={() => onSearchClear("skills")}
                    />
                </Container>

                <DropDown
                    id="subject"
                    label={`${t('offers.filter.subject')}:`}
                    value={filterValue?.subject}
                    placeholder={t('offers.filter.all')}
                    variant="facultyGreen"
                    options={subjects}
                    onChange={(dict) => handleFilterChange(null, "subject", dict.subject, true)}
                    property="w-32"
                />

                {/* FILTR KRAJE */}
                <Container property="w-full mt-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        {t('offers.filter.region')}:
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
                        <option value="">{t('offers.filter.all')}</option>
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
                        {t('offers.filter.city')}:
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
                        <option value="">{t('offers.filter.all')}</option>
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
                        {t('offers.filter.duration')}:
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
                        {t('offers.filter.has_capacity')}
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
                        {t('offers.filter.clear_all')}
                    </Button>
                </Container>
            )}

        </Container>
    )
}
