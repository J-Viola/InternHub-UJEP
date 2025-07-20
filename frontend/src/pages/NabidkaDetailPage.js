import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Nav from "@components/core/Nav";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useParams } from "react-router-dom";
import HTMLReactParser from "html-react-parser";
import Button from "@core/Button/Button";
import DocsPanel from "@components/Nabidka/DocsPanel";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useUser } from "@hooks/UserProvider";
import { Image } from "@components/core/Image"
import { useMessage } from "@hooks/MessageContext";

export default function NabidkaDetailPage() {
    const { id } = useParams();
    const [ popUp, setPopUp ] = useState(false);
    const [ entity, setEntity ] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();

    const fetchData = async () => {
        try {
            console.log("Fetching nabídka with ID:", id);
            const result = await nabidkaAPI.getNabidkaById(id);
            console.log("result", result)
            setEntity(result);
        } catch (error) {
            console.error("Chyba při načítání nabídky:", error);
        }
    };

    useEffect(() => {
        if (id) {
            console.log("id", id)
            fetchData();
        }
    }, [id]);


    const handlePopUp = () => {
        setPopUp(!popUp);
    }

    const onSubmit = async() => {
        const res = await nabidkaAPI.applyNabidka({
            "practice" : id
        })
        if (res) {
            addMessage("Přihláška byla úspěšně podána", "S")
            handlePopUp(!popUp)
        }
    }

    const onReject = () => {
        console.log("Přihláška odmítnuta");
    }

    //
    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                {/* DOCS PANEL */}
                {entity?.student_practice_status?.approval_status !== undefined &&
                 entity.student_practice_status.approval_status === 1 && (
                    <DocsPanel/>
                )}
                <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                    {/*<BackButton/>*/}
                    <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-4">
                            
                        {/* LOGO */}
                        <Container property="w-32 h-32 rounded-lg p-4 flex items-center justify-center">
                            <Headings sizeTag="h4" property="text-white">
                                <Image
                                    src={entity?.image_base64}
                                    alt={entity?.title}
                                    objectFit="cover"
                                />
                            </Headings>
                        </Container>

                        {/* TITLE */}
                        <Container>
                            <Headings sizeTag={"h4"} property={""}>{entity?.title}</Headings>
                            <Container property={"flex flex-row gap-2 mt-2"}>
                                <Button variant="blueSmallNoHover" pointer={false} property="w-fit">Místo konání: {entity?.employer.address}</Button>
                                <Button variant="blueSmallNoHover" pointer={false} property="w-fit">{entity?.start_date} - {entity?.end_date}</Button>
                            </Container>
                        </Container>

                    </Container>
                    {/* DESCRIPTION */}
                    <Container property={"editor-content mt-2"}>
                        <Paragraph>{entity?.description}</Paragraph>
                    </Container>

                    {/* RESPONSIBILITY */}
                    <Container property={"editor-content mt-2"}>
                        <Paragraph>{entity?.responsibilities}</Paragraph>
                    </Container>

                    {/* CONTACT USER INFO */}
                    {entity.contact_user_info && (
                        <Container property={"editor-content mt-2"}>
                            <Headings sizeTag="h3" property="mb-4">Kontaktní osoba</Headings>
                            {entity.contact_user_info.username && (
                                <Paragraph property="mb-2">
                                    <span className="font-semibold">Uživatelské jméno:</span> {entity.contact_user_info.username}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.first_name && (
                                <Paragraph property="mb-2">
                                    <span className="font-semibold">Jméno:</span> {entity.contact_user_info.first_name}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.last_name && (
                                <Paragraph property="mb-2">
                                    <span className="font-semibold">Příjmení:</span> {entity.contact_user_info.last_name}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.email && (
                                <Paragraph property="mb-2">
                                    <span className="font-semibold">Email:</span> {entity.contact_user_info.email}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.phone && (
                                <Paragraph property="mb-2">
                                    <span className="font-semibold">Telefon:</span> {entity.contact_user_info.phone}
                                </Paragraph>
                            )}
                        </Container>
                    )}
                    <Container property={"grid grid-cols-1 gap-8 mt-4"}>
                        {/* TLAČÍTKO PRO PODÁNÍ PŘIHLÁŠKY */}
                        {user && user.role === "ST" && (!entity?.student_practice_status || entity.student_practice_status.approval_status !== 1) && (
                            <Button property="col-start-1 justify-self-end w-full" onClick={handlePopUp}>Podat přihlášku</Button>
                        )}

                        {user && user.role === "VY" && (
                            <Button variant={"red"} property={"col-start-1 justify-self-end"} onClick={handlePopUp}>Spravovat</Button>
                        )}
                    </Container>
                </ContainerForEntity>
                
            </Container>

            {/* PODÁNÍ PŘIHLÁŠKY */}
            {popUp && (
                <PopUpCon 
                    onClose={handlePopUp} 
                    title= {"Přihláška"} 
                    text={"Opravdu si přejete podat přihlášku?"}
                    onSubmit={onSubmit}
                    onReject={onReject}
                ></PopUpCon>
            )}

        </Container>
    )
} 