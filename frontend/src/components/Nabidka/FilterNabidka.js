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
                    Hledat
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
            
            <Container property="border-t border-gray-300 my-4"></Container>
            
        </Container>
    )
}
