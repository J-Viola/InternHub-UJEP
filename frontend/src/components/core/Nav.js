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
import NotificationBell from "@components/core/NotificationBell";

const ROLE_LABELS = {
  ST: "Student",
  VY: "Vyučující",
  VK: "Vedoucí katedry",
  OWNER: "Majitel organizace",
  INSERTER: "Referent organizace",
  admin: "Administrátor",
};

// submenu render
function SubMenu({ items, title }) {
  const [isOpen, setIsOpen] = useState(false);
  const { user } = useUser();
  const location = useLocation();

  return (
    <Container
      property="relative inline-block"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <Button
        property="text-white hover:text-gray-200 transition-colors"
        noVariant={true}
      >
        <Container property={"flex items-center gap-1"}>
          {title}
          {!isOpen ? (
            <FaAngleDown size="12" className="text-white" />
          ) : (
            <FaAngleUp size="12" className="text-white" />
          )}
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
function LinkNav({ navigationDict, isMobile = false }) {
  const location = useLocation();

  return (
    <Container
      property={`${isMobile ? "flex flex-col items-start gap-4" : "flex items-center gap-6"}`}
    >
      {Object.entries(navigationDict).map(([key, value]) => {
        if (typeof value === "object" && Object.keys(value).length > 1) {
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
  const [navigationDict, setNaviagation] = useState({});
  const navigate = useNavigate();

  const studentDict = {
    "Nabídka praxí": "/nabidka",
    "Moje stáže": "/praxe",
    "Moje přihlášky": "/moje-prihlasky",
    "Vytvořit individuální praxi": "/vytvorit-externi-praxi",
    "Profil": "/profil",
    "Odhlásit se": "/logout",
  };

  const ownerDict = {
    "Správa organizace": {
      "Uživatelské účty organizace": "/users/org_users",
      "Účet organizace": "/formular?type=org_form&action=edit",
      "Stáže": "/praxe",
      "Přihlášky": "/prihlasky",
      "Odeslané pozvánky": "/pozvanky-list",
    },
    "Nabídka praxí": "/nabidka",
    "Studentské účty": "/students",
    "Odhlásit se": "/logout",
  };

  const inserterDict = {
    "Správa organizace": {
      "Uživatelské účty organizace": "/users/org_users",
      "Účet organizace": "/formular?type=org_form&action=edit",
      "Stáže": "/praxe",
      "Přihlášky": "/prihlasky",
      "Odeslané pozvánky": "/pozvanky-list",
    },
    "Nabídka praxí": "/nabidka",
    "Studentské účty": "/students",
    "Odhlásit se": "/logout",
  };

  const departmentDict = {
    "Uživatelé": {
      "Školní uživatelé": "/users/department_users",
    },
    "Studentské účty": "/students",
    "Předměty": "/subjects",
    "Správa stáží": "/sprava-stazi",
    "Přihlášky": "/prihlasky",
    "Nabídka praxí": "/nabidka",
    "Odhlásit se": "/logout",
  };

  const professorDict = {
    "Studentské účty": "/students",
    "Předměty": "/subjects",
    "Nabídka praxí": "/nabidka",
    "Správa stáží": "/sprava-stazi",
    "Přihlášky": "/prihlasky",
    "Odhlásit se": "/logout",
  };

  const adminDict = {
    "Správa systému": {
      "Katedry": "/departments",
      "Společnosti": "/companies",
    },
    "Správa stáží": {
      "Přihlášky": "/prihlasky",
      "Nabídka praxí": "/nabidka",
      "Schvalovací kolečko": "/sprava-stazi",
      "Pozvánky od firem": "/pozvanky-list",
    },
    "Uživatelé": {
      "Firemní uživatelé": "/users/org_users",
      "Školní uživatelé": "/users/department_users",
      "Studentské účty": "/students",
    },
    "Odhlásit se": "/logout",
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
  }, [user]);

  const handleLogoClick = () => {
    navigate("/nabidka");
  };

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:text-blue-700 focus:p-2 focus:rounded focus:shadow-lg"
      >
        {"Přeskočit na hlavní obsah"}
      </a>
      <Container property={"w-full bg-facultyCol"}>
        <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"}>
          <Container property={"flex items-center justify-between h-16"}>
            {/* Logo */}
            <Container
              property={"flex items-center cursor-pointer"}
              onClick={handleLogoClick}
            >
              <Headings sizeTag="h4" property={"text-white"}>
                InternHub
              </Headings>
            </Container>

            {/* Desktop Menu */}
            <nav
              aria-label={"Hlavní navigace"}
              className="w-full flex hidden md:flex justify-end mr-8"
            >
              <LinkNav navigationDict={navigationDict} />
            </nav>

            {/* User Info */}
            <Container property={"hidden md:flex items-center gap-4"}>
              {user && user.isLoggedIn && user.isLoggedIn() && (
                <NotificationBell />
              )}
              {user.hasData() && (
                <Container
                  property={"bg-white bg-opacity-20 px-1 rounded text-xs"}
                >
                  {user.hasData() && (
                    <Container
                      property={
                        "flex flex-col items-end gap-1 text-white text-sm"
                      }
                    >
                      <Container property={"flex items-center gap-2"}>
                        <FaUser />
                        <Paragraph property={"text-white text-sm"}>
                          {user.email}
                        </Paragraph>
                        <Paragraph property={"text-white text-sm"}>
                          {ROLE_LABELS[user.role] || user.role}
                        </Paragraph>
                      </Container>
                      {/* INFO o katedře uživatele */}
                      {user.isDepartmentMg() && user.department && (
                        <Paragraph property={"text-white text-xs opacity-75"}>
                          {typeof user.department === "string"
                            ? user.department
                            : user.department?.name ||
                              "Neznámá katedra"}
                        </Paragraph>
                      )}
                    </Container>
                  )}
                </Container>
              )}
            </Container>

            {/* Mobile menu button */}
            <Container property={"md:hidden flex items-center gap-4"}>
              <Button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                property="text-white hover:text-gray-200"
                noVariant={true}
                title={"Přepnout menu"}
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
          <nav
            aria-label={"Hlavní navigace"}
            className="md:hidden"
          >
            <Container property={"px-2 pt-2 pb-3 space-y-1 sm:px-3"}>
              <LinkNav navigationDict={navigationDict} isMobile={true} />
            </Container>
          </nav>
        )}
      </Container>
    </>
  );
}

export default Nav;
