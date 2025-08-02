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
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import { useUserAPI } from "src/api/user/userAPI";
import Button from "@components/core/Button/Button";

export default function StudentPage() {
    const { getDepartmentStudents } = useDepartmentAPI();
    const [entities, setEntities] = useState([]);
    const [filterValues, setFilterValue] = useState({"name" : ""})
    const [selectedStudents, setSelectedStudents] = useState(new Set());
    const navigate = useNavigate()
    const { getStudentsByPracticeId } = useStudentPracticeAPI()
    const { id } = useParams();
    const [searchParams] = useSearchParams();
    const { user } = useUser();
    const { getAllStudents } = useUserAPI();


    useEffect(() => {
        if (id) {
            loadStudentsByPractice();
            return;
        }
        
        if (user.isDepartmentUser()) {
            loadDepartmentStudents();
        } else if (user.isOrganizationUser()) {
            loadOrganizationStudents();
        }
    }, [searchParams]);

    const loadStudentsByPractice = () => {
        console.log("Mám id", id);
        getStudentsByPracticeId(id).then(fetchedStudents => {
            setEntities(fetchedStudents);
        });
    };

    const loadDepartmentStudents = () => {
        getDepartmentStudents().then(res => {
            setEntities(res);
        });
    };

    const loadOrganizationStudents = () => {
        const viewParam = searchParams.get('view');
        
        if (viewParam === 'true') {
            // View mode - pouze přihlášené studenty
            getDepartmentStudents().then(res => {
                setEntities(res);
            });
        } else {
            // Normal mode - všechny studenty
            getAllStudents().then(res => {
                setEntities(res.results);
            });
        }
    };


    const getDepartmentButtons = (approval_status, entity) => {
        const hasPractice = [
            {
                icon: "doc",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice.student_practice_id}`)
            },
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];
        
        const hasNotPractice = [
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        return approval_status === 1 ? hasPractice : hasNotPractice;
    };

    const getOrganizationButtons = (entity) => {
        const isSelected = selectedStudents.has(entity.user_id);
        
        return [
            {
                icon: isSelected ? "check" : "plus",
                btnfunction: () => handleStudentSelection(entity.user_id, isSelected)
            },
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];
    };

    const getStudentPracticeButtons = (entity) => {
        return [
            {
                icon: "doc",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice_id}`)
            },
            {
                icon: "user",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];
    };

    const handleStudentSelection = (userId, isSelected) => {
        setSelectedStudents(prev => {
            const newSet = new Set(prev);
            if (isSelected) {
                newSet.delete(userId);
            } else {
                newSet.add(userId);
            }
            return newSet;
        });
    };


    const getAttributes = () => {
        const viewParam = searchParams.get('view');
        
        if (user.isOrganizationUser() && !id) {
            return viewParam === 'true' 
                ? { "Osobní číslo": "os_cislo" }  // View mode
                : { "Osobní číslo": "os_cislo", "": "department" };  // Normal mode
        }
        
        if (!id) {
            return { "Osobní číslo": "os_cislo" };  // Department users
        } else if (!user.isOrganizationUser()) {
            return {  // Student practice
                "Podání": "application_date",
                "Stav": "approval_status", 
                "Hodiny": "hours_completed"
            };
        }
        
        return { "Osobní číslo": "os_cislo" };  // Fallback
    };


    const getTitle = () => {
        const viewParam = searchParams.get('view');
        
        if (id) {
            return `Přihlášení k praxi ${entities[0] && entities[0].practice_title}`;
        }
        
        if (user.isDepartmentUser()) {
            return entities[0] && entities[0].department 
                ? `Studenti katedry - ${entities[0].department}`
                : "Studenti katedry";
        }
        
        if (user.isOrganizationUser()) {
            return viewParam === 'true' ? "Přihlášení k praxi" : "Studenti";
        }
        
        return "Studenti";
    };


    const filteredEntities = entities.filter(entity => {
        if (!filterValues.name) return true;
        const search = filterValues.name.toLowerCase();
        
        return (
            (entity.student_full_name && entity.student_full_name.toLowerCase().includes(search)) ||
            (entity.first_name && entity.first_name.toLowerCase().includes(search)) ||
            (entity.last_name && entity.last_name.toLowerCase().includes(search)) ||
            (entity.name && entity.name.toLowerCase().includes(search)) ||
            (entity.surname && entity.surname.toLowerCase().includes(search))
        );
    });


    const handleProfileView = (entity) => {
        navigate(`/profil/${entity?.user_id}`);
    };

    const handleClear = () => {
        setFilterValue({ "name": "" });
    };
    
    const handleChange = (e) => {
        const { id, value } = e.target;
        setFilterValue(prev => ({
            ...prev,
            [id]: value
        }));
    };

    const handleInvite = () => {
        const selectedIds = Array.from(selectedStudents);
        if (selectedIds.length > 0) {
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
    };


    const renderInviteButton = () => {
        const viewParam = searchParams.get('view');
        if (!user.isOrganizationUser() || viewParam === 'true') return null;

        return (
            <Container property={"mb-4"}>
                <Button
                    onClick={handleInvite}
                    icon={"user-plus"}
                    disabled={selectedStudents.size === 0}
                >
                    Pozvat ({selectedStudents.size})
                </Button>
            </Container>
        );
    };

    const renderEntityButtons = (entity) => {
        if (id) {
            return getStudentPracticeButtons(entity);
        }
        
        if (user.isOrganizationUser() && searchParams.get('view') !== 'true') {
            return getOrganizationButtons(entity);
        }
        
        return getDepartmentButtons(entity.approved_practice?.approval_status, entity);
    };

    const renderEntityStatus = (entity) => {
        if (user.isOrganizationUser() && selectedStudents.has(entity.user_id)) {
            return "green";
        }
        return "gray";
    };

    const renderEntityStatusView = () => {
        return !user.isOrganizationUser() || searchParams.get('view') === 'true';
    };


    return (
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        {getTitle()}
                    </Headings>
                </Container>

                {renderInviteButton()}

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
                            attributes={getAttributes()}
                            status={renderEntityStatus(entity)}
                            onClick={() => handleProfileView(entity)}
                            buttons={renderEntityButtons(entity)}
                            statusView={renderEntityStatusView()}
                        />
                    ))}
                </Container>
            </Container>
        </Container>
    );
}