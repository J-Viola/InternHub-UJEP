import React, { useState } from "react";
import { Link } from "react-router-dom";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import { FaAngleDown, FaAngleUp, FaBars, FaTimes } from "react-icons/fa";
import Button from "@core/Button/Button";


const USER = {
    "name": "Aleš",
    "faculty": "PřF"
}

function SubMenu({ items, title }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <Container property="relative inline-block" onMouseEnter={() => setIsOpen(true)} onMouseLeave={() => setIsOpen(false)}>
            <Button property="text-white hover:text-gray-200 transition-colors" noVariant={true}>
                <Container property={"flex items-center gap-1"}>
                    {title}
                    {!isOpen ? (<FaAngleDown size="12" className="text-white" />) : (<FaAngleUp size="12" className="text-white" />)}
                </Container>
            </Button>
            {isOpen && (
                <Container property="absolute bg-facultyCol px-2 py-2 shadow-lg rounded-md min-w-[150px] max-w-[200px] z-50">
                    {Object.entries(items).map(([key, value]) => (
                        <Link 
                            key={key} 
                            to={value} 
                            className="block text-white hover:text-gray-200 mt-2 transition-colors"
                        >
                            {key}
                        </Link>
                    ))}
                </Container>
            )}
        </Container>
    );
}

function LinkNav({navigationDict, isMobile = false}) {
    return (
        <Container property={`${isMobile ? "flex flex-col items-start gap-4" : "flex items-center gap-8"}`}>
            {Object.entries(navigationDict).map(([key, value]) => {
                if (typeof value === 'object' && Object.keys(value).length > 1) {
                    return <SubMenu key={key} title={key} items={value} />;
                } else {
                    return (
                        <Link key={key} to={value} className="text-white hover:text-gray-200 transition-colors">
                            {key}
                        </Link>
                    );
                }
            })}
        </Container>
    );
}

function Nav({user=USER}) {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    
    const navigationDict = {
        "Nabídka praxí": "/nabidka",
        "Účet": "/",
        "Praxe": "/praxe",
        "TEST STRÁNEK": {
            "SprInPrihlaseni": "/SprInPrihlaseni",
            "VytStáže": "/VytNabidku"
        },
        "Formuláře": {
            "StudentForm": "/ProfileForm",
            "Studenti": "/Students"
        },
        "Profil": "/profil",
    };

    return(
        <>
        <Container property={"w-full bg-facultyCol"}>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"}>
                <Container property={"flex items-center justify-between h-16"}>
                    {/* Logo */}
                    <Container property={"flex items-center"}>
                        <Headings sizeTag="h4" property={"text-white"}>InternHub</Headings>
                    </Container>

                    {/* Desktop Menu */}
                    <Container property={"hidden md:flex items-center"}>
                        <LinkNav navigationDict={navigationDict} />
                    </Container>

                    {/* Mobile menu button */}
                    <Container property={"md:hidden"}>
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