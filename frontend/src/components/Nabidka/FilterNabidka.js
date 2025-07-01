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
                    id={"title"}
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


            {/* DRUHÝ ŘÁDEK - DALŠÍ FILTRY */}
            <Container property="flex items-center gap-4 mb-4 w-full">
                <Container property="flex-1">
                    {/*<DropDown
                        id="address"
                        label="Místo:"
                        value={filterValue?.address}
                        placeholder="Všechna místa"
                        variant="facultyGreen"
                        options={locations}
                        onChange={(dict) => handleFilterChange(null, "address", dict.address, true)}
                        property="w-full"
                    />*/}
                    <SearchBar 
                        id={"address"}
                        value={filterValue?.address}
                        placeholder={"Místo konání nabídky - např. Praha"}
                        onChange={handleFilterChange}
                        onClear={() => onSearchClear("address")}
                    />
                </Container>


                <Container property="w-64">
                    <DropDown
                        id="subject"
                        //label="Předmět:"
                        value={filterValue?.subject}
                        placeholder="Zvolte předmět"
                        variant="facultyGreen"
                        options={subjects}
                        onChange={(dict) => handleFilterChange(null, "subject", dict.subject, true)}
                        property={"w-full"}
                    />
                </Container>
            </Container>

            {/* ODDĚLOVAČ */}
            <Container property="border-t border-gray-300 my-4"></Container>
            
        </Container>
    )
}
