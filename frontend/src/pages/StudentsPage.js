import React, { useEffect, useState } from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import UserEntity from "@components/User/UserEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import BackButton from "@core/Button/BackButton";
import SearchBar from "@components/Filter/SearchBar";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_pracitceAPI";
import { useNavigate, useParams } from "react-router-dom";



export default function StudentPage() {
    const { getDepartmentStudents } = useDepartmentAPI();
    const [entities, setEntities] = useState([]);
    const [ filterValues, setFilterValue ] = useState({"name" : ""})
    const navigate = useNavigate()
    const { getStudentsByPracticeId } = useStudentPracticeAPI()
    const { id } = useParams();


    useEffect(() => {
        if (id) {
            console.log("Mám id", id);
            const fetchedStudents = getStudentsByPracticeId(id).then(fetchedStudents =>{
                setEntities(fetchedStudents);
            })
            return
        }
        getDepartmentStudents().then(res => {
            setEntities(res);
        });
    }, []);

    // podle approval status - pro katedry
    const getButtonDict = (approval_status, entity) => {
        const hasPractice = [
            {
                icon: "doc",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice.student_practice_id}`) // použij správný parametr
            },
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
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

    const getButtonDictStudentPractice = (entity) => {
        const buttonLayout = [
            {
                icon: "doc",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice_id}`) 
            },
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ]

        return buttonLayout

    }

    const handleProfileView = (entity) =>{
        navigate(`/profil/${entity?.user_id}`)
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

    const attributes = 
    !id ? {
        "Osobní číslo": "os_cislo", 
    } :
    {
        //"Název praxe": "practice_title",
        //"Katedra": "department_name",
        "Podání": "application_date",
        "Stav": "approval_status",
        "Hodiny": "hours_completed"
      }


    // Filtrování podle jména
    const filteredEntities = entities.filter(entity => {
        if (!filterValues.name) return "true";
        const search = filterValues.name.toLowerCase();
        
        return (
            (entity.student_full_name && entity.student_full_name.toLowerCase().includes(search)) ||
            (entity.first_name && entity.first_name.toLowerCase().includes(search)) ||
            (entity.last_name && entity.last_name.toLowerCase().includes(search)) ||
            (entity.name && entity.name.toLowerCase().includes(search)) ||
            (entity.surname && entity.surname.toLowerCase().includes(search))
        );
    });


    let titleGenerator = "";
    if (!id) {
      if (entities[0] && entities[0].department) {
        titleGenerator = ` ${entities[0].department}`;
      }
    } else {
      if (entities[0] && entities[0].practice_title) {
        titleGenerator = entities[0].practice_title;
      }
    }


    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        {id ? "Přihlášení - " : "Studenti - "}
                        {titleGenerator}
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
                            onClick={() => handleProfileView(entity)}
                            buttons={!id ? getButtonDict(entity.approved_practice?.approval_status, entity) : getButtonDictStudentPractice(entity)}
                        />
                    ))}
                </Container>
            </Container>
        </Container>
    )
}