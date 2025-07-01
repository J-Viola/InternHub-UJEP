import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Nav from "@core/Nav";
import Paragraph from "@components/core/Text/Paragraph";
import { Image } from "@components/core/Image";
import { useParams } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import { useNavigate } from "react-router-dom";


export default function ProfilPage() {
    const { id } = useParams()
    const { user } = useUser();
    const navigate = useNavigate();

    const  [ userProfile, setUserProfile ] = useState({});
    
    const dummy_profiles = [
        {
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
        },
        {
            "id": 2,
            "username": "f21a1234k",
            "email": "f21a1234k@students.zcu.cz",
            "title_before": "Bc.",
            "first_name": "Anna",
            "last_name": "Svobodová",
            "title_after": "",
            "phone": "+420 987 654 321",
            "date_joined": "2021-09-01T00:00:00Z",
            "is_active": true,
            "profile_picture": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAADMElEQVR4nOzVwQnAIBQFQYXff81RUkQCOyDj1YOPnbXWPmeTRef+/3O/OyBjzh3CD95BfqICMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMK0CMO0TAAD//2Anhf4QtqobAAAAAElFTkSuQmCC",
            "field_of_study": "Aplikovaná matematika",
            "year_of_study": 2,
            "stag_f_number": 20211234,
            "resume": "Zkušenosti s matematickým modelováním, statistickou analýzou a programováním v Python a R. Účast na matematických soutěžích.",
            "additional_info": "Zajímám se o data science, strojové učení a matematické modelování. Členka matematického kroužku a dobrovolnice v organizaci matematických soutěží pro středoškoláky.",
            "date_of_birth": "2003-08-22",
            "place_of_birth": "Brno",
            "street": "Kounicova",
            "street_number": "8",
            "zip_code": "60200",
            "city": "Brno",
            "specialization": "Data Science a Matematické modelování",
            "role": "ST",
            "role_name": "Student",
            "faculty": "FF",
            "os_cislo": "F21A1234K",
            "skills": ["Python", "R", "MATLAB", "SQL", "Machine Learning", "Statistics", "Data Analysis", "LaTeX", "Git", "Jupyter Notebooks"]
        }
    ]


    const fetchUser = async() => {
        // PŘEDĚLAT NA API
        if (id) {
            const foundUser = dummy_profiles.find(u => u.id === parseInt(id));
            setUserProfile(foundUser || dummy_profiles[0]);
        } else if (user && user.id) {
            const foundUser = dummy_profiles.find(u => u.id === parseInt(user.id));
            setUserProfile(foundUser || dummy_profiles[0]);
        } else {
            setUserProfile(dummy_profiles[0]); // Výchozí uživatel
        }
    }

    
    useEffect(() => {
        fetchUser();
    }, [id, user])
    
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
                                src={userProfile?.profile_picture}
                                alt={`${userProfile?.first_name} ${userProfile?.last_name}`}
                                objectFit="cover"
                                height={"100px"}
                                width={"100px"}
                                borderRadius={"50%"}
                            />
                        </Container>

                        {/* USER NAME */}
                        <Headings sizeTag={"h3"} property={"mt-0"}>
                            {userProfile?.title_before} {userProfile?.first_name} {userProfile?.last_name} {userProfile?.title_after} {id ? id : "NEMÁM id, čtu usera"}
                        </Headings>

                    </Container>

                    <Container property={"w-full mt-2 grid-cols-1"}>

                        {/* NĚCO O MĚ */}
                        <Container property="p-1 space-y-1 mb-4">
                            <Headings sizeTag={"h4"}>Něco o mě</Headings>
                            <Paragraph>
                                {userProfile?.additional_info}
                            </Paragraph>
                        </Container>

                        {/* OSOBNÍ ÚDAJE */}
                        <Container property="p-1 space-y-1 mb-4">
                            <Headings sizeTag={"h4"}>Osobní údaje</Headings>
                            <Paragraph>
                                <strong>Email:</strong> {userProfile?.email}<br/>
                                <strong>Telefon:</strong> {userProfile?.phone}<br/>
                                <strong>Datum narození:</strong> {userProfile?.date_of_birth}<br/>
                                <strong>Místo narození:</strong> {userProfile?.place_of_birth}<br/>
                                <strong>Adresa:</strong> {userProfile?.street} {userProfile?.street_number}, {userProfile?.zip_code} {userProfile?.city}<br/>
                                <strong>Studijní obor:</strong> {userProfile?.field_of_study} ({userProfile?.year_of_study}. ročník)<br/>
                                <strong>Specializace:</strong> {userProfile?.specialization}
                            </Paragraph>
                        </Container>

                        {/* SKILLS */}
                        <Container property="p-1 space-y-1">
                            <Headings sizeTag={"h4"}>Skills</Headings>
                            <Container property={"flex flex-wrap gap-2"}>
                                {userProfile?.skills?.map((skill, index) => (
                                    <Button key={index} pointer={false} variant="blueSmallNoHover">
                                        {skill}
                                    </Button>
                                ))}
                            </Container>
                        </Container>

                    </Container>

                    {/* BUTTONS - přidat pravidlo podle role */}
                    <Container property={"flex w-full mt-2 mb-4 justify-end"}>
                        <Button
                            icon={"edit"}
                            property="w-md mt-4" 
                            onClick={() => navigate(`/profil/edit/${id ? id : ""}`)}
                        >
                            Upravit profil
                        </Button>
                    </Container>

                </ContainerForEntity>
            </Container>

        </Container>
    )
}