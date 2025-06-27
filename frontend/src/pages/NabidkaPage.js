import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import { useSearchParams } from "react-router-dom";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams, useClearParams, useStripParams } from "@hooks/SearchParams"
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"

export default function NabidkaPage() {
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const clearParams = useClearParams();
    const stripUrlParams = useStripParams();
    const [searchParams] = useSearchParams();
    const [filterValue, setFilterValue] = useState({ title: "" })

    const [data, setData] = useState(null);
    const nabidkaAPI = useNabidkaAPI();

    //fetch
    const fetchData = async () => {
        try {
            // Načti všechny parametry z URL
            const urlParams = stripUrlParams(currentUrl);
            const params = {};
            
            if (urlParams) {
                // Parsuj parametry z URL
                const searchParams = new URLSearchParams(urlParams);
                searchParams.forEach((value, key) => {
                    if (value) params[key] = value;
                });
            }
            
            console.log("Fetching with params:", params);
            const result = await nabidkaAPI.getNabidky(params);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    useEffect(() => {
        fetchData();
    }, [searchParams]); 

    useEffect(() => {
        console.log("filter values", filterValue)
    }, [filterValue]);

    //DEBUG
    useEffect(() => {
        console.log(data);
    },[data])
        
    const handleFilterChange = (e) => {
        setFilterValue(prev => ({
            ...prev,
            [e.target.id]: e.target.value
        }));
    };

    const handleSearchClear = () => {
        setFilterValue(prev => ({
            ...prev,
            title: ""
        }));
    };

    const handleSearchSubmit = () => {
        const hasValues = Object.values(filterValue).some(value => value && value.trim() !== "");
    
        if (hasValues) {
            const queryString = makeQuery(filterValue);
            console.log("QueryString", queryString);
            setParams(currentUrl, queryString);
            fetchData(); // api call

        } else {
            clearParams(currentUrl);
        }
    };

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <FilterNabidka 
                    filterValue={filterValue}
                    handleFilterChange={handleFilterChange}
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