import React, { useEffect, useState, useCallback } from "react";
import Container from "@core/Container/Container";
import UserEntity from "@components/User/UserEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import BackButton from "@core/Button/BackButton";
import SearchBar from "@components/Filter/SearchBar";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import { useUserAPI } from "src/api/user/userAPI";
import Button from "@components/core/Button/Button";
import {useNabidkaAPI} from "../api/nabidka/nabidkaAPI";
import Pagination from "@core/Pagination";
import useDebounce from "@hooks/useDebounce";
import { useTranslation } from "react-i18next";

const PAGE_SIZE = 10;

export default function StudentPage() {
    const { t } = useTranslation();
    const { getDepartmentStudents } = useDepartmentAPI();
    const [entities, setEntities] = useState([]);
    const [practice, setPractice] = useState();
    const [filterValues, setFilterValue] = useState({"name" : ""});
    const [selectedStudents, setSelectedStudents] = useState(new Set());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [count, setCount] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const navigate = useNavigate()
    const { getStudentsByPracticeId } = useStudentPracticeAPI()
    const { getNabidkaById } = useNabidkaAPI()
    const { id } = useParams();
    const [searchParams] = useSearchParams();
    const { user } = useUser();
    const { getAllStudents } = useUserAPI();


    // admin / org-without-view use server-side pagination + search
    const isPaginated = !!user && !id && (
        user.isAdmin() || (user.isOrganizationUser() && searchParams.get('view') !== 'true')
    );
    const totalPages = Math.ceil(count / PAGE_SIZE);

    // Delay BE requests until user stops typing (400 ms)
    const debouncedSearchName = useDebounce(filterValues.name, 400);

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
                setError(t('students.load_error'));
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
            const res = await getAllStudents({ page, pageSize: PAGE_SIZE, search });
            setEntities(res.results ?? []);
            setCount(res.count ?? 0);
        } catch {
            setError(t('students.load_error'));
        } finally {
            setLoading(false);
        }
    }, [getAllStudents, t]);

    useEffect(() => {
        if (!isPaginated) return;
        loadPagedStudents(currentPage, debouncedSearchName);
    }, [isPaginated, currentPage, debouncedSearchName, loadPagedStudents]);

    const loadPractice = async () => {
        const fetchedPractice = await getNabidkaById(id);
        setPractice(fetchedPractice);
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
                title: t('students.view_profile'),
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        if (hasPractice) {
            buttons.unshift({
                icon: "doc",
                title: t('students.view_practice_card'),
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
                title: isSelected ? t('students.deselect') : t('students.select_for_invite'),
                btnfunction: () => handleStudentSelection(entity.user_id, isSelected)
            },
            {
                icon: "user",
                title: t('students.view_profile'),
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        // If it's an organization user viewing a specific practice's applications
        if (id && hasPractice) {
             buttons.unshift({
                icon: "doc",
                title: t('students.view_practice_card'),
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
                title: t('students.view_profile'),
                btnfunction: () => navigate(`/profil/${entity?.user_id}`)
            }
        ];

        if (hasPractice) {
            buttons.unshift({
                icon: "doc",
                title: t('students.view_practice_card'),
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
                ? { [t('students.personal_number')]: "os_cislo" }  // View mode
                : { [t('students.personal_number')]: "os_cislo", "": "department" };  // Normal mode
        }

        if (user.isAdmin()) {
            return {
                [t('students.personal_number')]: "os_cislo",
                "": "department"
            };
        }

        if (!id) {
            return { [t('students.personal_number')]: "os_cislo" };  // Department users
        } else if (!user.isOrganizationUser()) {
            return {  // Student practice
                [t('students.applied_on')]: "application_date",
                [t('common.status')]: "workflow_status",
                [t('students.hours')]: "hours_completed"
            };
        }

        return { [t('students.personal_number')]: "os_cislo" };  // Fallback
    };


    const getTitle = () => {
        const viewParam = searchParams.get('view');

        if (id) {
            return `${t('students.applicants_title')} - ${practice ? practice.title : ''}`;
        }

        if (user.isDepartmentUser()) {
            return !isPaginated && entities[0] && entities[0].department
                ? `${t('students.dept_students_title')} - ${entities[0].department}`
                : t('students.title');
        }

        if (user.isOrganizationUser()) {
            return viewParam === 'true' ? t('students.applicants_title') : t('students.title');
        }

        return t('students.title');
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
                    {t('students.invite_selected', { count: selectedStudents.size })}
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
                    value={filterValues.name}
                    placeholder={t('students.search_placeholder')}
                    onChange={handleChange}
                    onClear={handleClear}
                />
            </Container>

            <Container property={"mt-4"}>
                {loading && (
                    <Paragraph property="text-center text-gray-500 py-8">{t('students.loading')}</Paragraph>
                )}
                {!loading && error && (
                    <Paragraph property="text-center text-red-500 py-8">{error}</Paragraph>
                )}
                {!loading && !error && filteredEntities.length === 0 && (
                    <Paragraph property="text-center text-gray-500 py-8">{t('students.no_results')}</Paragraph>
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
        </>
    );
}
