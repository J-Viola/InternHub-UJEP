import React from "react";
import Container from "@core/Container/Container";
import SearchBar from "@components/Filter/SearchBar";
import Button from "@core/Button/Button";
import DropDown from "@core/Form/DropDown";
import { useTranslation } from "react-i18next";

export default function FilterNabidka({
    filterValue,
    handleFilterChange,
    onSearchClear,
    onSearchSubmit,
    locations,
    subjects
})

    {
    const { t } = useTranslation();
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
            </Container>

            <Container property="border-t border-gray-300 my-4"></Container>

        </Container>
    )
}
