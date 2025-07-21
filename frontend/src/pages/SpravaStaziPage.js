import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import { useParams } from "react-router-dom";
import { useStudentPracticeAPI } from "@api/student_practice/student_pracitceAPI";
import PrihlaskaEntity from "@components/Prihlasky/PrihlaskaEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";
import PraxeDepartmentEntity from "@components/Praxe/PraxeDepartmentEntity";

export default function SpravaStaziPage() {
    const [approved, setApproved] = useState([]);
    const [toApprove, setToApprove] = useState([]);
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await nabidkaAPI.getNabidkyByUserDepartment();
                setApproved(res.approved_practices || []);
                setToApprove(res.to_approve_practices || []);
            } catch (error) {
                setApproved([]);
                setToApprove([]);
            }
        };
        fetchData();
    }, []);

    const handleView = (type, entity) => {
        if (type === "approved_practices") {
            navigate(`/nabidka/${entity.practice_id}`)
        }
        if (type === "to_approve_practices") {
            navigate(`/nabidka/${entity.practice_id}`)
        }
        
    }

    const handleClick = (type, entity) =>{
        // dodělat handle na přihlášené a manage -> změna stavu
        console.log("Click")
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Probíhající stáže
                    </Headings>
                </Container>
                <Container property={"mb-8"}>
                    {approved.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Žádné schválené stáže.
                        </Paragraph>
                    ) : (
                        approved.map((entity) => (
                            <PraxeDepartmentEntity 
                                key={entity.practice_id} 
                                entity={entity} 
                                type="approved"
                                onView={() => handleView("approved_practices", entity)}
                            />
                        ))
                    )}
                </Container>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Schvalovací kolečko
                    </Headings>
                </Container>
                <Container property={"mt-4 mb-8"}>
                    {toApprove.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Žádné stáže čekající na schválení.
                        </Paragraph>
                    ) : (
                        toApprove.map((entity) => (
                            <PraxeDepartmentEntity 
                                key={entity.practice_id} 
                                entity={entity} 
                                onView={() => handleView("to_approve_practices", entity)}
                                type="to_approve" />
                            ))
                    )}
                </Container>
            </Container>
        </Container>
    )
}