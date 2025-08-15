import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import PopUpCon from "@core/Container/PopUpCon";
import { useAuth } from "@auth/Auth";
import UserEntity from "@components/User/UserEntity";
import { useParams } from "react-router-dom";
import { useUserAPI } from "@api/user/userAPI";
import { useNavigate } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import { useMessage } from "@hooks/MessageContext";
import TextField from "@core/Form/TextField";
import SearchBar from "@components/Filter/SearchBar";

export default function UserCRUDPage() {
    const { type } = useParams("type");
    
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [userType, setUserType] = useState(type === 'department_users' ? 'department' : 'org'); // 'org' nebo 'department'
    const [searchTerm, setSearchTerm] = useState('');
    const [activeFilters, setActiveFilters] = useState([]);
    const userAPI = useUserAPI();
    const { user } = useUser();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    const rolesTranslator = {"OWNER" : "Jednatel firmy", "INSERTER" : "Správce inzerátů"};
    const headings = {"org_users":"Účty organizací", 
        "department_users": "Uživatelské účty"};

    const translateRoles = (dataArr) => {
        return dataArr.map(entity => ({
            ...entity,
            roleText: rolesTranslator[entity.role] || entity.role
        }));
    };

    const fetchUsers = async () => {
        try {
            setLoading(true);
            let res;
            if (userType === 'org') {
                res = await userAPI.getOrganizationUsers(false);
            } else {
                // TODO: Implementovat API pro katederní uživatele
                res = await userAPI.getDepartmentUsers();
            }
            
            if (res) {
                setData(translateRoles(res));
            }
        } catch (error) {
            console.error("Chyba při načítání uživatelů:", error);
            addMessage('Chyba při načítání uživatelů', 'E');
            setData([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Nastavit userType podle URL parametru
        setUserType(type === 'department_users' ? 'department' : 'org');
    }, [type]);

    useEffect(() => {
        fetchUsers();
    }, [userType]);

    const handleCreateUser = () => {
        if (userType === 'org') {
            navigate(`/formular?type=org_users&action=create`);
        } else {
            // Katederní uživatelé se vytvářejí přes STAG
            addMessage('Katederní uživatelé se vytvářejí přes IS STAG', 'info');
        }
    };

    const handleEditUser = (entity) => {
        if (userType === 'org') {
            navigate(`/formular?type=org_users&action=edit&id=${entity.id}`);
        } else {
            // TODO: Implementovat editaci katederního uživatele
            addMessage('Katederní uživatelé se upravují přes IS STAG', 'info');
        }
    };

    const handleViewStages = (entity) => {
        // Navigace na stránku se stážemi pro danou organizaci
        navigate(`/praxe?organization=${entity.id}`);
    };

    const handleViewProfile = (entity) => {
        // Navigace na profil katederního uživatele
        navigate(`/profil/${entity.id}`);
    };

    const handleUserTypeChange = (newType) => {
        setUserType(newType);
    };

    const handleSearchChange = (e) => {
        setSearchTerm(e.target.value || '');
    };

    const handleSearchClear = () => {
        setSearchTerm('');
    };


    return (
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                
                {/* Filtr a vyhledávání */}
                <Container property={"mt-4 mb-6"}>
                    <Container property={"flex items-center gap-4 mb-4"}>
                        <SearchBar
                            id={"name"}
                            value={searchTerm}
                            placeholder={userType === 'org' ? "Zadejte název společnosti" : "Zadejte název katedry"}
                            onChange={handleSearchChange}
                            onClear={handleSearchClear}
                        />
                    </Container>
                </Container>

                <Container property={"flex items-center justify-between mb-6"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        {type ? (headings[type]) : ("Správa uživatelů")}
                    </Headings>
                </Container>

                {userType === 'org' && (
                    <Container>
                        <Button 
                            onClick={handleCreateUser}
                            icon={"plus"}
                        >
                            Založit účet
                        </Button>
                    </Container>
                )}

                <Container property={"mt-4 rounded-lg"}>
                    {loading ? (
                        <Paragraph>Načítání...</Paragraph>
                    ) : data.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Zatím nejsou žádní uživatelé k zobrazení.
                        </Paragraph>
                    ) : (
                        <Container property={"grid grid-cols-1 gap-4"}>
                            {data?.map(entity => (
                                <UserEntity
                                    key={entity.id}
                                    entity={entity}
                                    attributes={{"Role": "roleText"}}
                                    statusView={user.isOrganizationUser() ? false : true}
                                                                         buttons={
                                         userType === 'org' ? [
                                             {
                                                 icon: "edit",
                                                 btnfunction: () => handleEditUser(entity)
                                             }
                                         ] : [
                                             {
                                                 icon: "eye",
                                                 btnfunction: () => handleViewProfile(entity)
                                             }
                                         ]
                                     }
                                />
                            ))}
                        </Container>
                    )}
                </Container>
            </Container>


        </Container>
    );
}