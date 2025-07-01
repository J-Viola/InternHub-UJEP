import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Nav from "@core/Nav";
import Paragraph from "@components/core/Text/Paragraph";
import { Image } from "@components/core/Image";


export default function ProfilPage() {

    const dummy_profile = {
        "id": 1,
        "username": "f20b0539p",
        "email": "f20b0539p@students.zcu.cz",
        "title_before": "Bc.",
        "first_name": "Jan",
        "last_name": "Novák",
        "title_after": "",
        "phone": "+420 123 456 789",
        "date_joined": "2023-09-01T00:00:00Z",
        "is_active": true,
        "profile_picture": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAADMElEQVR4nOzVwQnAIBQFQYXff81RUkQCOyDj1YOPnbXWPmeTRef+/3O/OyBjzh3CD95BfqICMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMO0TAAD//2Anhf4QtqobAAAAAElFTkSuQmCC",
        "field_of_study": "Informatika",
        "year_of_study": 3,
        "stag_f_number": 20200539,
        "resume": "Zkušenosti s programováním v JavaScript, React, Node.js. Praxe v IT firmě během letních prázdnin.",
        "additional_info": "Zajímám se o webový vývoj a umělou inteligenci. Aktivní člen studentského klubu.",
        "date_of_birth": "2002-05-15",
        "place_of_birth": "Praha",
        "street": "Nerudova",
        "street_number": "15",
        "zip_code": "11800",
        "city": "Praha",
        "specialization": "Webové technologie",
        "role": "ST",
        "role_name": "Student",
        "faculty": "FF",
        "os_cislo": "F20B0539P",
        "skills": ["JavaScript", "React", "Node.js", "Python", "SQL", "Git", "Docker", "TypeScript"]
    }
    
    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                    <BackButton/>
                    <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-8 items-center">
                        
                        {/* PROFILE PIC */}
                        <Container property="w-md rounded-lg flex items-center justify-center">
                            <Image
                                src={dummy_profile?.profile_picture}
                                alt={`${dummy_profile?.first_name} ${dummy_profile?.last_name}`}
                                objectFit="cover"
                                height={"100px"}
                                width={"100px"}
                                borderRadius={"50%"}
                            />
                        </Container>

                        {/* USER NAME */}
                        <Headings sizeTag={"h3"} property={"mt-0"}>
                            {dummy_profile?.title_before} {dummy_profile?.first_name} {dummy_profile?.last_name} {dummy_profile?.title_after}
                        </Headings>

                    </Container>

                    <Container property={"w-full mt-2 grid-cols-1"}>

                        {/* NĚCO O MĚ */}
                        <Container property="p-1 space-y-1 mb-4">
                            <Headings sizeTag={"h4"}>Něco o mě</Headings>
                            <Paragraph>
                                {dummy_profile?.additional_info}
                            </Paragraph>
                        </Container>

                        {/* OSOBNÍ ÚDAJE */}
                        <Container property="p-1 space-y-1 mb-4">
                            <Headings sizeTag={"h4"}>Osobní údaje</Headings>
                            <Paragraph>
                                <strong>Email:</strong> {dummy_profile?.email}<br/>
                                <strong>Telefon:</strong> {dummy_profile?.phone}<br/>
                                <strong>Datum narození:</strong> {dummy_profile?.date_of_birth}<br/>
                                <strong>Místo narození:</strong> {dummy_profile?.place_of_birth}<br/>
                                <strong>Adresa:</strong> {dummy_profile?.street} {dummy_profile?.street_number}, {dummy_profile?.zip_code} {dummy_profile?.city}<br/>
                                <strong>Studijní obor:</strong> {dummy_profile?.field_of_study} ({dummy_profile?.year_of_study}. ročník)<br/>
                                <strong>Specializace:</strong> {dummy_profile?.specialization}
                            </Paragraph>
                        </Container>

                        {/* SKILLS */}
                        <Container property="p-1 space-y-1">
                            <Headings sizeTag={"h4"}>Skills</Headings>
                            <Container property={"flex flex-wrap gap-2"}>
                                {dummy_profile?.skills?.map((skill, index) => (
                                    <Button key={index} pointer={false} variant="blueSmallNoHover">
                                        {skill}
                                    </Button>
                                ))}
                            </Container>
                        </Container>

                    </Container>

                    {/* BUTTONS */}
                    <Container property={"flex w-full mt-2 mb-4 justify-end"}>
                        <Button
                            icon={"edit"}
                            property="w-md mt-4" 
                            onClick={() => console.log("Upravit profil!!!")}
                        >
                            Upravit profil
                        </Button>
                    </Container>

                </ContainerForEntity>
            </Container>

        </Container>
    )
}