import React from "react";
import Container from "@core/Container/Container";
import SearchBar from "@components/Filter/SearchBar";
import Button from "@core/Button/Button";
import DropDown from "@core/Form/DropDown";

export default function FilterNabidka({ filterValue, handleFilterChange, onSearchClear, onSearchSubmit }) {
    return (
        <Container property="w-full mb-8">
            {/* PRVNÍ ŘÁDEK - VYHLEDÁVÁNÍ */}
            <Container property="flex items-center justify-center mb-4">
                <SearchBar 
                    value={filterValue?.title}
                    onChange={handleFilterChange}
                    onClear={onSearchClear}
                />
                <Button 
                    onClick={onSearchSubmit} 
                    noVariant={true} 
                    property={"ml-2 bg-facultyColLight px-4 py-1 border border-black rounded-lg transition-colors duration-200 hover:bg-facultyCol"}
                >
                    Hledat
                </Button>
            </Container>

            {/* DRUHÝ ŘÁDEK - DALŠÍ FILTRY */}
            <Container property="flex justify-center gap-8 inline-block">
                <DropDown
                    id="location"
                    label="Místo:"
                    placeholder="Všechna místa"
                    variant="facultyGreen"
                    options={[
                        { value: "praha", label: "Praha" },
                        { value: "brno", label: "Brno" },
                        { value: "ostrava", label: "Ostrava" }
                    ]}
                    onChange={(value) => console.log("Location filter:", value)}
                    property="w-32"
                />

                <DropDown
                    id="availability"
                    label="Dostupnost:"
                    placeholder="Všechny"
                    variant="facultyGreen"
                    options={[
                        { value: "available", label: "Dostupné" },
                        { value: "limited", label: "Omezené" },
                        { value: "full", label: "Plné" }
                    ]}
                    onChange={(value) => console.log("Availability filter:", value)}
                    property="w-32"
                />

                <DropDown
                    id="subject"
                    label="Předmět:"
                    placeholder="Všechny"
                    variant="facultyGreen"
                    options={[
                        { value: "available", label: "Dostupné" },
                        { value: "limited", label: "Omezené" },
                        { value: "full", label: "Plné" }
                    ]}
                    onChange={(value) => console.log("Subject filter:", value)}
                    property="w-32"
                />

            </Container>
        </Container>
    )
}
