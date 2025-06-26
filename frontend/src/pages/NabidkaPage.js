import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import { useSearchParams } from "react-router-dom";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams as useSetParams, useClearParams } from "@hooks/SearchParams"
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"

export default function NabidkaPage() {
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const clearParams = useClearParams();
    const [searchParams] = useSearchParams();
    const search = searchParams.get("search");
    const [searchValue, setSearchValue] = useState(search || "");

    const [data, setData] = useState(null);
    const nabidkaAPI = useNabidkaAPI();

    //fetch
    const fetchData = async () => {
        try {
            const params = search ? { title: search } : {}; //zatim pro debug
            const result = await nabidkaAPI.getNabidky(params);
            console.log("Fetching..")
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);
    

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
            fetchData();

        } else {
            clearParams(currentUrl);
        }
    };

    //DEBUG
    useEffect(() => {
        console.log(data);
    },[data])
    
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
                    {data && data.map((entity, index) => (
                        <NabidkaEntity key={entity.practice_id || index} entity={entity}/>
                    ))}
                </Container>
            </Container>
        </Container>
    )
}