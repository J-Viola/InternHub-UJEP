import React, { useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import { useSearchParams } from "react-router-dom";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams as useSetParams, useClearParams } from "@hooks/SearchParams"

export default function NabidkaPage() {
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const clearParams = useClearParams();
    const [searchParams] = useSearchParams();
    const search = searchParams.get("search");
    const [searchValue, setSearchValue] = useState(search || "");


    const handleSearchChange = (e) => {
        setSearchValue(e.target.value);
    };

    const handleSearchClear = () => {
        setSearchValue("");
    };

    const handleSearchSubmit = () => {
        if (searchValue) {
            const queryString = makeQuery({ search: searchValue });
            setParams(currentUrl, queryString);
        } else {
            clearParams(currentUrl);
        }
    };

    const entity = {
        "id": "1",
        "title": "Apple IOS Developer",
        "annotation": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Suspendisse nisl. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Nulla pulvinar eleifend sem. Curabitur sagittis hendrerit ante. Nullam sit amet magna in magna gravida vehicula. Fusce tellus odio, dapibus id fermentum quis, suscipit id erat. Ut tempus purus at lorem. Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Nullam dapibus fermentum ipsum.",
        "adress": "Praha, Česká republika"
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <FilterNabidka 
                    searchValue={searchValue}
                    onSearchChange={handleSearchChange}
                    onSearchClear={handleSearchClear}
                    onSearchSubmit={handleSearchSubmit}
                />
                
                <Container property="grid grid-cols-1 gap-4 mt-2">
                    <NabidkaEntity entity={entity}/>
                    <NabidkaEntity entity={entity}/>
                    <NabidkaEntity entity={entity}/>
                </Container>
            </Container>
        </Container>
    )
}