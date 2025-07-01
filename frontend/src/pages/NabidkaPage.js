import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import NabidkaEntity from "@components/Nabidka/NabidkaEntity";
import { useSearchParams } from "react-router-dom";
import FilterNabidka from "@components/Nabidka/FilterNabidka";
import { makeQuery, useCurrentUrl, useSetParams, useFullUrl, useClearParams, useStripParams } from "@hooks/SearchParams"
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useCodeListAPI } from "@api/code_list/code_listAPI";


export default function NabidkaPage() {
    const currentUrl = useCurrentUrl();
    const setParams = useSetParams();
    const fullUrl = useFullUrl();
    const clearParams = useClearParams();
    const stripUrlParams = useStripParams();
    const [ searchParams ] = useSearchParams();
    const [ filterValue, setFilterValue ] = useState({ title: "" });
    const [ filterOptions, setFilterOptions ] = useState({});
    const [data, setData] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const codelist = useCodeListAPI();

    const [ uniqueLocations, setLocations ] = useState([])
    const [ uniqueSubjects, setSubjects ] = useState([])


    const initParamLoad = () => {
        console.log("full url", fullUrl);
        const urlParams = stripUrlParams(fullUrl);
        console.log("URL params", urlParams);
        
        if (urlParams && Object.keys(urlParams).length > 0) {
            console.log("Mám params data");
            setFilterValue(urlParams);
            console.log("FILTER DATA Z PARAMS", urlParams);
            fetchDataWithParams(urlParams);
        } else {
            setFilterValue({});
            fetchData();
        }
    }

    const initFilterOptions = async() =>{
        const locations = await codelist.getUniqueLocations();
        console.log("Locations", locations)
        setLocations(locations);

        const subjects = await codelist.getUniqueSubjects();
        console.log("Subjects", subjects)
        setSubjects(subjects);

    }

    //fetch s parametry
    const fetchDataWithParams = async (params) => {
        try {
            console.log("Fetching with URL params:", params);
            const result = await nabidkaAPI.getNabidky(params);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    //fetch s aktuálními filtry
    const fetchData = async () => {
        try {
            console.log("Fetching with current filters:", filterValue);
            const result = await nabidkaAPI.getNabidky(filterValue);
            setData(result);
        } catch (error) {
            console.error("Chyba při načítání nabídek:", error);
        }
    };

    useEffect(() => {
        initParamLoad();
        initFilterOptions();
    }, []); 

    useEffect(() => {
        console.log("filter values", filterValue);
    }, [filterValue]);

    //DEBUG
    useEffect(() => {
        console.log(data);
    },[data])
        
    const handleFilterChange = (e, id, value, directValue = false) => {
        setFilterValue(prev => {
            const newValue = directValue ? value : e.target.value;
            const key = directValue ? id : e.target.id;
            const updatedFilter = { ...prev };
            
            if (newValue === "" || newValue === null || newValue === undefined) {
                delete updatedFilter[key];
            } else {
                updatedFilter[key] = newValue;
            }
            return updatedFilter;
        });
    };

    const handleSearchClear = (field_id) => {
        setFilterValue(prev => {
            const updatedFilter = { ...prev };
            
            if (field_id === "title") {
                updatedFilter.title = "";
            } 
            if (field_id === "address") {
                updatedFilter.address = "";
            }
            
            return updatedFilter;
        });
    };

    const handleSearchSubmit = () => {
        const queryString = makeQuery(filterValue);
        console.log("QueryString", queryString);
        setParams(currentUrl, queryString);
        fetchData(); // api call
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
                    locations={uniqueLocations}
                    subjects={uniqueSubjects}
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