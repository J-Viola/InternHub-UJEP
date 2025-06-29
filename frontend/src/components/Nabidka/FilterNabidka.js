import React from "react";
import Container from "@core/Container/Container";
import SearchBar from "@components/Filter/SearchBar";
import Button from "@core/Button/Button";
import DropDown from "@core/Form/DropDown";

export default function FilterNabidka({ 
    filterValue, 
    handleFilterChange, 
    onSearchClear, 
    onSearchSubmit, 
    locations, 
    subjects 
}) 
    
    {
    return (
        <Container property="w-full mb-8">
            {/* PRVNÍ ŘÁDEK - VYHLEDÁVÁNÍ */}
            <Container property="flex items-center justify-center mb-4">
                <SearchBar 
                    value={filterValue?.title}
                    placeholder={"Název"}
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
            <Container property="flex justify-center gap-16 inline-block">
                <DropDown
                    id="address"
                    label="Místo:"
                    value={filterValue?.address}
                    placeholder="Všechna místa"
                    variant="facultyGreen"
                    options={locations}
                    onChange={(dict) => handleFilterChange(null, "address", dict.address, true)}
                    property="w-full"
                />

                <DropDown
                    id="subject"
                    label="Předmět:"
                    value={filterValue?.subject}
                    placeholder="Všechny"
                    variant="facultyGreen"
                    options={subjects}
                    onChange={(dict) => handleFilterChange(null, "subject", dict.subject, true)}
                    property="w-32"
                />

            </Container>

            {/* ODDĚLOVAČ */}
            <Container property="border-t border-gray-300 my-4"></Container>
            
        </Container>
    )
}
