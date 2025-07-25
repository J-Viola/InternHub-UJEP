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
import ProgressPanel from "@components/Nabidka/ProgressBar";
import { useDocumentsAPI } from "src/api/documents/documentsAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_pracitceAPI";


export default function PraxeDetailPage() {
    const { id } = useParams();
    const [ popUp, setPopUp ] = useState(false);
    const [ entity, setEntity ] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const studentpraticeAPI = useStudentPracticeAPI();
    const documentAPI = useDocumentsAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();

    // MOCK: Získání dat o dokumentech (nahraďte reálnými daty podle potřeby)
    const [docs, setDocs] = useState([]);

    const fetchData = async () => {
        try {
            console.log("Fetching nabídka with ID:", id);
            const result = await studentpraticeAPI.getStudentPracticeCard(id);
            console.log("result", result)
            setEntity(result);
            setDocs(result.student_practice_documents || []);
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

    // Handler pro stahování dokumentu
    const handleDownload = async (documentId) => {
        try {
            const blob = await documentAPI.downloadDocument(documentId);
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `dokument_${documentId}.docx`); // nebo použijte název z API
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
        } catch (error) {
            addMessage("Chyba při stahování dokumentu", "E");
        }
    };

    // Handler pro nahrávání dokumentu
    const handleUpload = async (documentId) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.doc,.docx';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('document', file);
            try {
                await documentAPI.uploadDocument(documentId, formData);
                addMessage("Dokument úspěšně nahrán", "S");
            } catch (error) {
                addMessage("Chyba při nahrávání dokumentu", "E");
            }
        };
        input.click();
    };

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

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                {/* DOCS PANEL */}
                {entity?.student_practice_status?.approval_status !== undefined &&
                 entity.student_practice_status.approval_status === 1 && (
                    <DocsPanel docData={docs} handleDownload={handleDownload} handleUpload={handleUpload}/>
                )}
                <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
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
                    {entity && entity.contact_user_info && (
                        <Container property={"editor-content mt-2"}>
                            <Headings sizeTag="h3" property="mb-4">Kontaktní osoba</Headings>
                            {entity.contact_user_info.username && (
                                <Paragraph property="mb-2">
                                    Uživatelské jméno: {entity.contact_user_info.username}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.first_name && (
                                <Paragraph property="mb-2">
                                    Jméno: {entity.contact_user_info.first_name}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.last_name && (
                                <Paragraph property="mb-2">
                                    Příjmení: {entity.contact_user_info.last_name}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.email && (
                                <Paragraph property="mb-2">
                                    Email: {entity.contact_user_info.email}
                                </Paragraph>
                            )}
                            {entity.contact_user_info.phone && (
                                <Paragraph property="mb-2">
                                    Telefon: {entity.contact_user_info.phone}
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

                {entity?.student_practice_status?.approval_status !== undefined &&
                 entity.student_practice_status.approval_status === 1 && (
                    <Container property={"mt-2"}>
                        <ProgressPanel
                            subject={entity.subject?.subject_code}
                            goalValueSingle={entity.subject?.hours_required}
                            currentValueSingle={entity.student_practice_status?.hours_completed}
                        />
                    </Container>
                )}
                  
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