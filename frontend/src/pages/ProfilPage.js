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
import { useStudentAPI } from "@api/student/studentAPI";


export default function ProfilPage() {
    const { id } = useParams()
    const { user } = useUser();
    const navigate = useNavigate();
    const students = useStudentAPI();
    const  [ userProfile, setUserProfile ] = useState({});
    

    const fetchUser = async() => {
        if (id) {
            const res = await students.getStudentById(id)
            console.log("res", res);
            setUserProfile(res);
        } if (user && user.id) {
            const res = await students.getStudentById(user.id)
            console.log("res", res);
            setUserProfile(res);
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
