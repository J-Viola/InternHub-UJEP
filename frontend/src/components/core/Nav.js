import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import { FaAngleDown, FaAngleUp, FaBars, FaTimes } from "react-icons/fa";
import Button from "@core/Button/Button";
import { useNavigate } from "react-router-dom";
import Paragraph from "./Text/Paragraph";
import { useUser } from "@hooks/UserProvider";
import { FaUser } from "react-icons/fa";
import LanguageSwitcher from "./LanguageSwitcher";
import { useTranslation } from "react-i18next";

// submenu render
function SubMenu({ items, title }) {
    const [ isOpen, setIsOpen ] = useState(false);
    const { user } = useUser();
    const location = useLocation();

    return (
        <Container property="relative inline-block" onMouseEnter={() => setIsOpen(true)} onMouseLeave={() => setIsOpen(false)}>
            <Button property="text-white hover:text-gray-200 transition-colors" noVariant={true}>
                <Container property={"flex items-center gap-1"}>
                    {title}
                    {!isOpen ? (<FaAngleDown size="12" className="text-white" />) : (<FaAngleUp size="12" className="text-white" />)}
                </Container>
            </Button>
            {isOpen && (
                <Container property="absolute bg-facultyCol px-2 py-2 shadow-lg rounded-md min-w-[300px] max-w-[350px] z-50">
                    {Object.entries(items).map(([key, value]) => (
                        <Link
                            key={key}
                            to={value}
                            className={`block mt-2 transition-colors ${
                                location.pathname === value
                                    ? "text-gray-200 font-semibold"
                                    : "text-white hover:text-gray-200"
                            }`}
                        >
                            {key}
                        </Link>
                    ))}
                </Container>
            )}
        </Container>
    );
}

// linknav render
function LinkNav({navigationDict, isMobile = false}) {
    const location = useLocation();

    return (
        <Container property={`${isMobile ? "flex flex-col items-start gap-4" : "flex items-center gap-6"}`}>
            {Object.entries(navigationDict).map(([key, value]) => {
                if (typeof value === 'object' && Object.keys(value).length > 1) {
                    return <SubMenu key={key} title={key} items={value} />;
                } else {
                    return (
                        <Link
                            key={key}
                            to={value}
                            className={`transition-colors ${
                                location.pathname === value
                                    ? "text-gray-200 border-b-2 border-gray-200"
                                    : "text-white hover:text-gray-200"
                            }`}
                        >
                            {key}
                        </Link>
                    );
                }
            })}
        </Container>
    );
}

function Nav({}) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const { user } = useUser();
    const [ navigationDict, setNaviagation ] = useState({});
    const navigate = useNavigate();
    const { t } = useTranslation();

    const studentDict = {
        [t('nav.internship_offers')]: "/nabidka",
        [t('nav.my_internships')]: "/praxe",
        [t('nav.profile')]: "/profil",
        [t('nav.logout')]: "/logout",
    };

    const ownerDict = {
        [t('nav.org_management')] : {
            [t('nav.org_accounts')] : "/users/org_users",
            [t('nav.org_account')] : "/formular?type=org_form&action=edit",
            [t('nav.internships')] : "/praxe",
            [t('nav.applications')] : "/prihlasky",
            [t('nav.sent_invitations')] : "/pozvanky-list",
        },
        [t('nav.internship_offers')]: "/nabidka",
        [t('nav.students')]: "/students",
        [t('nav.logout')]: "/logout",
    };

    const inserterDict = {
        [t('nav.org_management')] : {
            [t('nav.org_accounts')] : "/users/org_users",
            [t('nav.org_account')] : "/formular?type=org_form&action=edit",
            [t('nav.internships')] : "/praxe",
            [t('nav.applications')] : "/prihlasky",
            [t('nav.sent_invitations')] : "/pozvanky-list",
        },
        [t('nav.internship_offers')]: "/nabidka",
        [t('nav.students')]: "/students",
        [t('nav.logout')]: "/logout",
    };

    const departmentDict = {
        [t('nav.students')] : "/students",
        [t('nav.subjects')] : "/subjects",
        [t('nav.internship_management')] : "/sprava-stazi",
        [t('nav.internship_offers')] : "/nabidka",
        [t('nav.logout')] : "/logout",
    }

    const professorDict = {
        [t('nav.students')] : "/students",
        [t('nav.subjects')] : "/subjects",
        [t('nav.internship_offers')] : "/nabidka",
        [t('nav.internship_management')] : "/sprava-stazi",
        [t('nav.logout')] : "/logout",
    }

    const adminDict = {
        [t('nav.system_management')] : {
            [t('nav.departments')] : "/departments",
            [t('nav.companies')] : "/companies",
        },
        [t('nav.internship_management')] : {
            [t('nav.applications')] : "/prihlasky",
            [t('nav.internship_offers')]: "/nabidka",
            [t('nav.approval_process')] : "/sprava-stazi",
            [t('nav.company_invitations')] : "/pozvanky-list",
        },
        [t('nav.users')] : {
            [t('nav.company_users')]: "/users/org_users",
            [t('nav.school_users')]: "/users/department_users",
            [t('nav.students')]: "/students",
        },
        [t('nav.logout')]: "/logout",
    };

    useEffect(() => {
        // Pokud není uživatel autentizovaný, navigaci vyčistíme
        if (!user || !user.isAuthenticated) {
            setNaviagation({});
            return;
        }

        if (user.isOwner()) {
            setNaviagation(ownerDict);
        } else if (user.isStudent()) {
            setNaviagation(studentDict);
        } else if (user.isDepartmentMg()) {
            setNaviagation(departmentDict);
        } else if (user.isInserter()) {
            setNaviagation(inserterDict);
        } else if (user.isProfessor()) {
            setNaviagation(professorDict);
        } else if (user.isAdmin()) {
            setNaviagation(adminDict);
        } else {
            // Fallback pro neznámou roli – žádná navigace
            setNaviagation({});
        }
    }, [user, t]); // dependency na 't' pro aktualizaci při změně jazyka

    const handleLogoClick = () => {
        navigate("/nabidka");
    };

    return(
        <>
        <Container property={"w-full bg-facultyCol"}>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"}>
                <Container property={"flex items-center justify-between h-16"}>
                    {/* Logo */}
                    <Container
                        property={"flex items-center cursor-pointer"}
                        onClick={handleLogoClick}
                    >
                        <Headings sizeTag="h4" property={"text-white"}>InternHub</Headings>
                    </Container>

                    {/* Desktop Menu */}
                    <Container property={"w-full flex hidden md:flex justify-end mr-8"}>
                        <LinkNav navigationDict={navigationDict} />
                    </Container>

                    {/* Language Switcher & User Info */}
                    <Container property={"hidden md:flex items-center gap-4"}>
                        <LanguageSwitcher />
                        {user.hasData() && <Container property={"bg-white bg-opacity-20 px-1 rounded text-xs"}>
                            {user.hasData() && (
                                <Container property={"flex flex-col items-end gap-1 text-white text-sm"}>
                                    <Container property={"flex items-center gap-2"}>
                                        <FaUser/>
                                        <Paragraph property={"text-white text-sm"}>
                                            {user.email}
                                        </Paragraph>
                                        <Paragraph property={"text-white text-sm"}>
                                            {t(`profile.roles.${user.role}`, { defaultValue: user.role })}
                                        </Paragraph>
                                    </Container>
                                    {/* INFO o katedře uživatele */}
                                    {user.isDepartmentMg() && user.department && (
                                        <Paragraph property={"text-white text-xs opacity-75"}>
                                            {typeof user.department === 'string' ? user.department : user.department?.name || t('invitations.unknown_dept')}
                                        </Paragraph>
                                    )}
                                </Container>
                            )}
                        </Container>}
                    </Container>

                    {/* Mobile menu button */}
                    <Container property={"md:hidden flex items-center gap-4"}>
                        <LanguageSwitcher />
                        <Button
                            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                            property="text-white hover:text-gray-200"
                            noVariant={true}
                        >
                            {isMobileMenuOpen ? (
                                <FaTimes size={24} />
                            ) : (
                                <FaBars size={24} />
                            )}
                        </Button>
                    </Container>
                </Container>
            </Container>

            {/* Mobile Menu */}
            {isMobileMenuOpen && (
                <Container property={"md:hidden"}>
                    <Container property={"px-2 pt-2 pb-3 space-y-1 sm:px-3"}>
                        <LinkNav navigationDict={navigationDict} isMobile={true} />
                    </Container>
                </Container>
            )}
        </Container>
        </>
    );
}

export default Nav;
