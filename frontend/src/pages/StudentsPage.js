import React, { useEffect, useState } from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import UserEntity from "@components/User/UserEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import BackButton from "@core/Button/BackButton";
import SearchBar from "@components/Filter/SearchBar";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useNavigate } from "react-router-dom";



export default function StudentPage() {
    const { getDepartmentStudents } = useDepartmentAPI();
    const [entities, setEntities] = useState([]);
    const [ filterValues, setFilterValue ] = useState({"name" : ""})
    const navigate = useNavigate()

    useEffect(() => {
        getDepartmentStudents().then(res => {
            setEntities(res);
        });
    }, []);

    const getButtonDict = (approval_status, entity) => {
        const hasPractice = [
            {
                icon: "eye",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`) // použij správný parametr
            },
            {
                icon: "user",
                btnfunction: () => console.log("Karta")
            }
        ]
    
        const hasNotPractice = [
            {
                icon: "user",
                btnfunction: () => console.log("Karta")
            }
        ]

        if (approval_status === 1) {
            return hasPractice
        }
        else {
            return hasNotPractice
        }
    }


    const handleClear = () => {
        setFilterValue({
            "name" : ""
        })
    }
    
    const handleChange = (e) => {
        const { id, value } = e.target;
        setFilterValue(prev => ({
            ...prev,
            [id]: value
        }));
    }

    const attributes = {
        "Osobní číslo": "os_cislo", 
    }

    // Filtrování podle jména
    const filteredEntities = entities.filter(entity => {
        if (!filterValues.name) return "true";
        const search = filterValues.name.toLowerCase();
        
        return (
            (entity.first_name && entity.first_name.toLowerCase().includes(search)) ||
            (entity.last_name && entity.last_name.toLowerCase().includes(search)) ||
            (entity.name && entity.name.toLowerCase().includes(search)) ||
            (entity.surname && entity.surname.toLowerCase().includes(search))
        );
    });

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Studenti
                        {entities[0] && entities[0].department && ` - ${entities[0].department}`}
                    </Headings>

                </Container>
                <Container property={"mt-auto"}>
                    <SearchBar
                        id={"name"}
                        value={filterValues.name}
                        placeholder={"Hledat podle jména..."}
                        onChange={handleChange}
                        onClear={handleClear}
                    />
                </Container>
                <Container property={"mt-4"}>
                    {filteredEntities.map(entity => (
                        <UserEntity
                            key={entity.user_id}
                            entity={entity}
                            attributes={attributes}
                            buttons={getButtonDict(entity.approved_practice?.approval_status, entity)}
                        />
                    ))}
                </Container>
            </Container>
        </Container>
    )
}