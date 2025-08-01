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
import { useUser } from "@hooks/UserProvider";
import { useUserAPI } from "src/api/user/userAPI";
import Button from "@components/core/Button/Button";



export default function StudentPage() {
    const { getDepartmentStudents } = useDepartmentAPI();
    const [entities, setEntities] = useState([]);
    const [filterValues, setFilterValue] = useState({"name" : ""})
    const [selectedStudents, setSelectedStudents] = useState(new Set()); // Pro sledování vybraných studentů
    const navigate = useNavigate()
    const { getStudentsByPracticeId } = useStudentPracticeAPI()
    const { id } = useParams();
    const { user } = useUser();
    const { getAllStudents } = useUserAPI();


    useEffect(() => {
        if (id) {
            console.log("Mám id", id);
            getStudentsByPracticeId(id).then(fetchedStudents =>{
                setEntities(fetchedStudents);
            })
            return
        }
        if (user.isDepartmentUser()) {
            getDepartmentStudents().then(res => {
                setEntities(res);
            });
        }
        if (user.isOrganizationUser()) {
            getAllStudents().then(res => {
                setEntities(res.results);
            });
        }

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

    // Tlačítka pro organizační uživatele
    const getOrganizationButtonDict = (entity) => {
        const isSelected = selectedStudents.has(entity.user_id);
        
        return [
            {
                icon: isSelected ? "check" : "plus",
                btnfunction: () => {
                    if (isSelected) {
                        // Odebrat ze seznamu
                        setSelectedStudents(prev => {
                            const newSet = new Set(prev);
                            newSet.delete(entity.user_id);
                            return newSet;
                        });
                        //console.log("Odebrán ze seznamu:", entity.user_id);
                    } else {
                        // Přidat do seznamu
                        setSelectedStudents(prev => {
                            const newSet = new Set(prev);
                            newSet.add(entity.user_id);
                            return newSet;
                        });
                        //console.log("Přidán do seznamu:", entity.user_id);
                    }
                }
            },
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ]
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

    // Logika pro získání atributů podle typu uživatele a kontextu
    const getAttributes = () => {
        if (user.isOrganizationUser() && !id) {
            // Pro organizační uživatele - pouze osobní číslo
            return {
                "Osobní číslo": "os_cislo",
                "": "department"
            };
        }
        
        if (!id) {
            // Pro katedry - osobní číslo
            return {
                "Osobní číslo": "os_cislo"
            };
        } else if (!user.isOrganizationUser()) {
            // Pro přihlášení k praxi - podání, stav, hodiny
            return {
                "Podání": "application_date",
                "Stav": "approval_status",
                "Hodiny": "hours_completed"
            };
        }
        else {
            // falback
            return {
                "Osobní číslo": "os_cislo"

            };
        }
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


    // Logika pro generování titulu
    const getTitle = () => {
        if (id) {
            // Pokud máme ID praxe, zobrazíme přihlášení k praxi
            return `Přihlášení k praxi ${entities[0] && entities[0].practice_title}`;
        }
        
        if (user.isDepartmentUser()) {
            if (entities[0] && entities[0].department) {
                return `Studenti katedry - ${entities[0].department}`;
            }
            return "Studenti katedry";
        }
        
        if (user.isOrganizationUser()) {
            return "Studenti";
        }
        
        // Fallback
        return "Studenti";
    };


    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        {getTitle()}
                    </Headings>
                </Container>

                <Container property={"mb-4"}>
                    {user.isOrganizationUser() && (
                        <Button
                            onClick={() => {
                                const selectedIds = Array.from(selectedStudents);
                                if (selectedIds.length > 0) {
                                    // Získat jména vybraných studentů
                                    const selectedStudentsData = entities.filter(entity => 
                                        selectedIds.includes(entity.user_id)
                                    );
                                    const studentNames = selectedStudentsData.map(student => 
                                        student.student_full_name || 
                                        `${student.first_name || ''} ${student.last_name || ''}`.trim() ||
                                        student.name ||
                                        'Neznámý student'
                                    );
                                    
                                    const queryParams = new URLSearchParams({
                                        type: 'create',
                                        id: selectedIds.join(','),
                                        names: studentNames.join(',')
                                    });
                                    navigate(`/pozvanka?${queryParams.toString()}`);
                                }
                            }}
                            icon={"user-plus"}
                            disabled={selectedStudents.size === 0}
                        >
                            Pozvat ({selectedStudents.size})
                        </Button>
                    )}
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
                    {filteredEntities.map(entity => {
                        let entityStatus = "gray";
                        
                        if (user.isOrganizationUser() && selectedStudents.has(entity.user_id)) {
                            entityStatus = "green";
                        } else if (id) {
                            entityStatus = "gray";
                        }
                        
                         return (
                             <UserEntity
                                key={entity.user_id}
                                entity={entity}
                                attributes={getAttributes()}
                                status={entityStatus}
                                onClick={() => handleProfileView(entity)}
                                buttons={
                                    id ? getButtonDictStudentPractice(entity)
                                        : user.isOrganizationUser()
                                            ? getOrganizationButtonDict(entity)
                                            : getButtonDict(entity.approved_practice?.approval_status, entity)
                                 }
                                statusView={!user.isOrganizationUser()}
                             />
                         );
                    })}
                </Container>
             </Container>
         </Container>
     )
 }