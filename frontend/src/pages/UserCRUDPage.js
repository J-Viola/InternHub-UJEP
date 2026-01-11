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
import DropDown from "@core/Form/DropDown";

export default function UserCRUDPage() {
    const { type } = useParams("type");
    
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [userType, setUserType] = useState(type === 'department_users' ? 'department' : 'org'); // 'org' nebo 'department'
    const [searchTerm, setSearchTerm] = useState('');
    const [activeFilters, setActiveFilters] = useState([]);
    const [selectedCompanies, setSelectedCompanies] = useState([]);
    const [companySelectValue, setCompanySelectValue] = useState("");
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
            id: entity.id || entity.user_id,
            roleText: rolesTranslator[entity.role] || entity.role
        }));
    };

    const fetchUsers = async () => {
        try {
            setLoading(true);
            let res;
            if (userType === 'org') {
                res = await userAPI.getOrganizationUsers(false);
                //TO:DO - udělat api pro admina (není přiřazen k organizaci)
                

            } else {
                res = await userAPI.getAllDepartmentProfessors();
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
            navigate(`/formular?type=department_users&action=edit&id=${entity.id}`);
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

    // vyhledávání podle typu uživatele
    const searchFiltered = !searchTerm
        ? data
        : data.filter(entity => {
            const q = searchTerm.toLowerCase();
            if (userType === 'org') {
                return (
                    (entity.name && entity.name.toLowerCase().includes(q))
                );
            }
            // department users
            return (
                (entity.department && entity.department.toLowerCase().includes(q)) ||
                (Array.isArray(entity.subjects) && entity.subjects.some(s => (s.subject_name || '').toLowerCase().includes(q))) ||
                (entity.first_name && entity.first_name.toLowerCase().includes(q)) ||
                (entity.last_name && entity.last_name.toLowerCase().includes(q))
            );
        });

    // Group by employer_name pro org uživatele
    const groupedByEmployer = (userType === 'org' ? (searchFiltered || []) : []).reduce((acc, item) => {
        const name = item.employer_name || "Neznámá firma";
        (acc[name] = acc[name] || []).push(item);
        return acc;
    }, {});

    const allCompanyNames = Object.keys(groupedByEmployer);
    const displayCompanyNames = userType === 'org'
        ? (selectedCompanies.length ? selectedCompanies.filter((n) => allCompanyNames.includes(n)) : allCompanyNames)
        : [];

    const onCompanySelect = (dict) => {
        const name = dict?.company;
        if (!name) return;
        if (!selectedCompanies.includes(name)) setSelectedCompanies([...selectedCompanies, name]);
        // reset dropdown to placeholder
        setCompanySelectValue("");
    };

    const onRemoveCompany = (name) => setSelectedCompanies(selectedCompanies.filter((n) => n !== name));
    const availableOptions = allCompanyNames.filter((n) => !selectedCompanies.includes(n));
    return (
        <>
            <BackButton/>
            
            {/* Filtr a vyhledávání */}
            <Container property={"mt-4 mb-6"}>
                <Container property={"flex items-center gap-4 mb-4"}>
                    <SearchBar
                        id={"name"}
                        value={searchTerm}
                        placeholder={userType === 'org' ? "Zadejte jméno uživatele" : "Zadejte jméno, předmět, název katedry"}
                        onChange={handleSearchChange}
                        onClear={handleSearchClear}
                    />
                </Container>
                {userType === 'org' && (
                    <Container property={"flex items-center gap-3"}>
                        <DropDown
                            id="company"
                            variant="facultyGreen"
                            placeholder="Vyberte organizaci pro filtrování"
                            value={companySelectValue}
                            onChange={onCompanySelect}
                            options={availableOptions.map((name) => ({ label: name, value: name }))}
                        />
                        <Container property={"flex items-center flex-wrap gap-2"}>
                            {selectedCompanies.map((name) => (
                                <Button key={name} icon={"cross"} iconColor="text-black" variant="secondary" onClick={() => onRemoveCompany(name)}>
                                    {name}
                                </Button>
                            ))}
                        </Container>
                    </Container>
                )}
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
                    userType === 'org' ? (
                        displayCompanyNames.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">Žádné výsledky.</Paragraph>
                        ) : (
                            <Container property={"space-y-6"}>
                                {displayCompanyNames.map((name) => (
                                    <Container key={name}>
                                        <Headings sizeTag={"h4"}>{name}</Headings>
                                        <Container property={"flex flex-col gap-4 mt-2"}>
                                            {(groupedByEmployer[name] || []).map((entity) => (
                                                <UserEntity
                                                    key={entity.id}
                                                    entity={entity}
                                                    attributes={{ "Role": "roleText" }}
                                                    statusView={false}
                                                    buttons={[
                                                        {
                                                            icon: "edit",
                                                            btnfunction: () => handleEditUser(entity)
                                                        }
                                                    ]}
                                                />
                                            ))}
                                        </Container>
                                    </Container>
                                ))}
                            </Container>
                        )
                    ) : (
                        <Container property={"flex flex-col gap-4"}>
                            {searchFiltered?.map(entity => (
                                <UserEntity
                                    key={entity.id}
                                    entity={entity}
                                    attributes={{ "Katedra": "department", "Předmět": "subjects[0].subject_name" }}
                                    statusView={false}
                                    buttons={[
                                        {
                                            icon: "edit",
                                            btnfunction: () => handleEditUser(entity)
                                        }
                                    ]}
                                />
                            ))}
                        </Container>
                    )
                )}
            </Container>
        </>
    );
}