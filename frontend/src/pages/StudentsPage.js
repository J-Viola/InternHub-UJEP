import React, { useEffect, useState, useCallback, useRef } from "react";
import Container from "@core/Container/Container";
import UserEntity from "@components/User/UserEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import BackButton from "@core/Button/BackButton";
import SearchBar from "@components/Filter/SearchBar";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import { useUserAPI } from "@api/user/userAPI";
import { useMessage } from "@hooks/MessageContext";
import Button from "@components/core/Button/Button";
import {useNabidkaAPI} from "../api/nabidka/nabidkaAPI";
import Pagination from "@core/Pagination";
import useDebounce from "@hooks/useDebounce";
import EmptyState from "@core/Feedback/EmptyState";
import NabidkaEntityInline from "@components/Nabidka/NabidkaEntityInline";
import PopUpCon from "@core/Container/PopUpCon";
import TextField from "@core/Form/TextField";

import getApiErrorMessage from "@utils/apiErrorUtils";
const PAGE_SIZE = 10;

export default function StudentPage() {
    const { getDepartmentStudents } = useDepartmentAPI();
    const [entities, setEntities] = useState([]);
    const [practice, setPractice] = useState();
    const [filterValues, setFilterValue] = useState({"name" : ""});
    const [selectedStudents, setSelectedStudents] = useState(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [count, setCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [invitationNabidky, setInvitationNabidky] = useState([]);
    const [selectedNabidkaForInvite, setSelectedNabidkaForInvite] = useState(null);
    const [invitationMessage, setInvitationMessage] = useState("");
    const navigate = useNavigate()
    const { getStudentsByPracticeId, createInvitation } = useStudentPracticeAPI()
    const { getNabidkaById, getOrganizationPractices } = useNabidkaAPI()
    const { id } = useParams();
    const [searchParams] = useSearchParams();
    const { user } = useUser();
    const { getAllStudents } = useUserAPI();
    const getAllStudentsRef = useRef(getAllStudents);
    getAllStudentsRef.current = getAllStudents;
    const { addMessage } = useMessage();


    // admin / org-without-view use server-side pagination + search
    const isPaginated = !!user && !id && (
        user.isAdmin() || (user.isOrganizationUser() && searchParams.get('view') !== 'true')
    );
    const totalPages = Math.ceil(count / PAGE_SIZE);

    // Delay BE requests until user stops typing (400 ms)
    const debouncedSearchName = useDebounce(filterValues.name, 400);

    // Fetch practices for invitation if needed
    useEffect(() => {
        if (showInviteModal && user.isOrganizationUser() && !id) {
            getOrganizationPractices().then(res => {
                // Backend might return {results: [], count: 0} or []
                const data = res.results !== undefined ? res.results : res;
                setInvitationNabidky(data || []);
            }).catch(err => {
                console.error("Error loading practices for invite:", err);
            });
        }
    }, [showInviteModal, user, id, getOrganizationPractices]);


    // Non-paginated modes: load once on route change
    useEffect(() => {
        if (isPaginated) return;
        const load = async () => {
            setLoading(true);
            setError(null);
            try {
                if (id) {
                    await Promise.all([loadStudentsByPractice(), loadPractice()]);
                    return;
                }
                if (user.isDepartmentUser()) {
                    await loadDepartmentStudents();
                } else if (user.isOrganizationUser()) {
                    // view=true: show department students
                    const res = await getDepartmentStudents();
                    setEntities(res);
                }
            } catch {
                setError("Nepodařilo se načíst studenty.");
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [id, searchParams.get('view')]);

    // Paginated modes: reload on page or search change
    const loadPagedStudents = useCallback(async (page, search) => {
        setLoading(true);
        setError(null);
        try {
            const res = await getAllStudentsRef.current({ page, pageSize: PAGE_SIZE, search });
            setEntities(res.results ?? []);
            setCount(res.count ?? 0);
        } catch {
            setError("Nepodařilo se načíst studenty.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!isPaginated) return;
        loadPagedStudents(currentPage, debouncedSearchName);
    }, [isPaginated, currentPage, debouncedSearchName, loadPagedStudents]);

    const loadPractice = async () => {
        const fetchedPractice = await getNabidkaById(id);
        setPractice(fetchedPractice);
        setSelectedNabidkaForInvite(fetchedPractice);
    };

    const loadStudentsByPractice = async () => {
        const fetchedStudents = await getStudentsByPracticeId(id);
        setEntities(fetchedStudents);
    };

    const loadDepartmentStudents = async () => {
        const res = await getDepartmentStudents();
        setEntities(res);
    };


    const getDepartmentButtons = (entity) => {
        const hasPractice = !!entity?.student_practice?.student_practice_id;

        const buttons = [
            {
                icon: "user",
                title: "Zobrazit profil",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        if (hasPractice) {
            buttons.unshift({
                icon: "doc",
                title: "Zobrazit kartu praxe",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice.student_practice_id}`)
            });
        }

        return buttons;
    };

    const getOrganizationButtons = (entity) => {
        const isSelected = selectedStudents.has(entity.user_id);
        const hasPractice = !!(entity?.student_practice_id || entity?.student_practice?.student_practice_id);

        const buttons = [
            {
                icon: isSelected ? "check" : "plus",
                title: isSelected ? "Zrušit výběr" : "Vybrat pro pozvánku",
                btnfunction: () => handleStudentSelection(entity.user_id, isSelected)
            },
            {
                icon: "user",
                title: "Zobrazit profil",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        // If it's an organization user viewing a specific practice's applications
        if (id && hasPractice) {
             buttons.unshift({
                icon: "doc",
                title: "Zobrazit kartu praxe",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice_id || entity?.student_practice?.student_practice_id}`)
            });
        }

        return buttons;
    };

    const getStudentPracticeButtons = (entity) => {
        const hasPractice = !!entity?.student_practice_id;
        const buttons = [
            {
                icon: "user",
                title: "Zobrazit profil",
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        if (hasPractice) {
            buttons.unshift({
                icon: "doc",
                title: "Zobrazit kartu praxe",
                btnfunction: () => navigate(`/karta-praxe/${entity?.student_practice_id}`)
            });
        }
        return buttons;
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
                ? { ["Osobní číslo"]: "os_cislo" }  // View mode
                : { ["Osobní číslo"]: "os_cislo", "": "department" };  // Normal mode
        }

        if (user.isAdmin()) {
            return {
                "Osobní číslo": "os_cislo",
                "": "department"
            };
        }

        if (!id) {
            return { ["Osobní číslo"]: "os_cislo" };  // Department users
        } else if (!user.isOrganizationUser()) {
            return {  // Student practice
                "Podání": "application_date",
                "Stav": "workflow_status",
                "Hodiny": "hours_completed"
            };
        }

        return { ["Osobní číslo"]: "os_cislo" };  // Fallback
    };


    const getTitle = () => {
        const viewParam = searchParams.get('view');

        if (id) {
            return `Přihlášení k praxi - ${practice ? practice.title : ''}`;
        }

        if (user.isDepartmentUser()) {
            return !isPaginated && entities[0] && entities[0].department
                ? `Studenti katedry - ${entities[0].department}`
                : "Studenti";
        }

        if (user.isOrganizationUser()) {
            return viewParam === 'true' ? "Přihlášení k praxi" : "Studenti";
        }

        return "Studenti";
    };


    // Paginated modes: BE handles search, no client-side filter needed
    const filteredEntities = isPaginated ? entities : entities.filter(entity => {
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

    const handlePageChange = (page) => {
        setCurrentPage(page);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleClear = () => {
        setFilterValue({ "name": "" });
        if (isPaginated) setCurrentPage(1);
    };

    const handleChange = (e) => {
        const { id, value } = e.target;
        setFilterValue(prev => ({ ...prev, [id]: value }));
        if (isPaginated) setCurrentPage(1);
    };

    const handleInvite = () => {
        if (selectedStudents.size > 0) {
            setShowInviteModal(true);
        }
    };

    const handleSendInvitations = async () => {
        const studentIds = Array.from(selectedStudents);
        const practiceId = id || selectedNabidkaForInvite?.practice_id;

        if (!practiceId) {
            addMessage("Vyberte, na jakou stáž má být pozvánka vázána", "E");
            return;
        }

        try {
            // Optional: we can send the message too if backend supports it,
            // but currently createInvitation only takes practiceId and studentIds.
            // Let's assume for now we just want to implement the UI as planned.
            const res = await createInvitation(practiceId, studentIds);
            if (res) {
                addMessage(`Pozvánka pro ${res.created} studentů vytvořena.`, "S");
                if (res.errors && res.errors.length > 0) {
                    addMessage(`Chyby: ${res.errors.join(", ")}`, "E");
                }
                setShowInviteModal(false);
                setSelectedStudents(new Set());
                setSelectedNabidkaForInvite(null);
                setInvitationMessage("");
            }
        } catch (error) {
            console.error("Chyba při vytváření pozvánky", error);
            addMessage(`Chyba při vytváření pozvánky: ${getApiErrorMessage(error, error.message)}`, "E");
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
                    {`Pozvat (${selectedStudents.size})`}
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

        return getDepartmentButtons(entity);
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
        <>
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
                    variant={"student"}
                    value={filterValues.name}
                    placeholder={"Hledat podle jména..."}
                    onChange={handleChange}
                    onClear={handleClear}
                />
            </Container>

            <Container property={"mt-4"}>
                {loading && (
                    <Paragraph property="text-center text-gray-500 py-8">{"Načítání studentů..."}</Paragraph>
                )}
                {!loading && error && (
                    <Paragraph property="text-center text-red-500 py-8">{error}</Paragraph>
                )}
                {!loading && !error && filteredEntities.length === 0 && (
                    <EmptyState
                        title={"Žádní studenti nebyli nalezeni."}
                        description={"Zkuste změnit vyhledávací dotaz."}
                        icon="user-slash"
                    />
                )}
                {!loading && !error && filteredEntities.map(entity => (
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
                {!loading && !error && isPaginated && (
                    <Pagination
                        currentPage={currentPage}
                        totalPages={totalPages}
                        onPageChange={handlePageChange}
                    />
                )}
            </Container>

            {showInviteModal && (
                <PopUpCon
                    onClose={() => setShowInviteModal(false)}
                    title={"Pozvat studenty na stáž"}
                    text={`Chystáte se pozvat ${selectedStudents.size} vybraných studentů na stáž.`}
                    onSubmit={handleSendInvitations}
                    onReject={() => setShowInviteModal(false)}
                    submitText={"Potvrdit"}
                    rejectText={"Zrušit"}
                    variant="blue"
                >
                    <Container property="mt-4 px-4 space-y-6 pb-4">
                        {!id && (
                            <Container>
                                <Headings sizeTag="h5" property="mb-3">
                                    {"Vyberte, na jakou stáž má být pozvánka vázána"}
                                </Headings>
                                <Container property="space-y-3 max-h-60 overflow-y-auto pr-2 border-b pb-4">
                                    {invitationNabidky.length > 0 ? (
                                        invitationNabidky.map((nabidka) => (
                                            <NabidkaEntityInline
                                                key={nabidka.practice_id}
                                                entity={nabidka}
                                                isSelected={selectedNabidkaForInvite?.practice_id === nabidka.practice_id}
                                                onClick={() => setSelectedNabidkaForInvite(nabidka)}
                                                onView={() => navigate(`/nabidka/${nabidka.practice_id}`)}
                                            />
                                        ))
                                    ) : (
                                        <Paragraph property="text-gray-500 italic">
                                            {"Načítání nabídek..."}
                                        </Paragraph>
                                    )}
                                </Container>
                            </Container>
                        )}

                        <Container>
                            <TextField
                                id="invitationMessage"
                                label={"Zpráva pro studenty (volitelné)"}
                                placeholder={"Zde můžete napsat krátkou zprávu pro studenty..."}
                                value={invitationMessage}
                                onChange={(val) => setInvitationMessage(val.invitationMessage)}
                            />
                        </Container>
                    </Container>
                </PopUpCon>
            )}
        </>
    );
}
