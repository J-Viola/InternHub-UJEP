import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useParams } from "react-router-dom";
import Button from "@core/Button/Button";
import DocsPanel from "@components/Nabidka/DocsPanel";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useUser } from "@hooks/UserProvider";
import { Image } from "@components/core/Image"
import { useMessage } from "@hooks/MessageContext";
import ProgressPanel from "@components/Nabidka/ProgressBar";
import { useDocumentsAPI } from "src/api/documents/documentsAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";


export default function PraxeDetailPage() {
    const { id } = useParams();
    const [ popUp, setPopUp ] = useState(false);
    const [ docsPopUp, setDocsPopUp ] = useState(false);
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
            const result = await studentpraticeAPI.getStudentPracticeCard(id);
            setEntity(result);
            setDocs(result.student_practice_documents || []);
        } catch (error) {
            addMessage("Chyba při načítání karty praxe", "E");
        }
    };

    useEffect(() => {
        if (id) {
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

    const handleDocsPopUp = () => {
        setDocsPopUp(!docsPopUp);
    }

    const handleApply = async() => {
        try {
            const res = await nabidkaAPI.applyNabidka({
                "practice" : id
            })
            if (res) {
                addMessage("Přihláška byla úspěšně podána", "S")
                handlePopUp()
                fetchData();
            }
        } catch (error) {
            if (error.response?.data?.detail) {
                addMessage(error.response.data.detail, "E");
            } else {
                addMessage("Došlo k chybě při podání přihlášky.", "E");
            }
        }
    }

    const handleApprove = async () => {
        try {
            await studentpraticeAPI.updateStudentPracticeStatus(id, "approve");
            addMessage("Přihláška schválena", "S");
            fetchData();
            setPopUp(false);
        } catch (error) {
            addMessage("Chyba při schvalování", "E");
        }
    }

    const handleReject = async () => {
        try {
            await studentpraticeAPI.updateStudentPracticeStatus(id, "reject");
            addMessage("Přihláška zamítnuta", "S");
            fetchData();
            setPopUp(false);
        } catch (error) {
            addMessage("Chyba při zamítání", "E");
        }
    }

    return(
        <>
            <BackButton/>

            {/* INFORMACE O STUDENTOVI, JEHOŽ KARTA JE OTEVŘENA */}
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8 mb-2 mt-4"}>
                <Headings sizeTag={"h3"} property={""}>Student</Headings>
                <Paragraph property={"mt-2"}>
                    {entity?.student_practice_status?.student_info?.full_name}
                </Paragraph>
                <Paragraph>
                    {`Osobní číslo: ${entity?.student_practice_status?.student_info?.os_cislo}`}
                </Paragraph>
                <Paragraph>
                    {`Email: ${entity?.student_practice_status?.student_info?.email}`}
                </Paragraph>

            </ContainerForEntity>

            {/* DOCS PANEL */}
            {entity?.student_practice_status?.approval_status !== undefined &&
                entity.student_practice_status.approval_status === 1 && (
                <DocsPanel entity={entity} docData={docs} handleDownload={handleDownload} handleUpload={handleUpload} handleManage={handleDocsPopUp}/>
            )}


            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-4">

                    {/* LOGO */}
                    <Container property="w-32 h-32 rounded-lg p-4 flex items-center justify-center">
                        <Image
                            src={entity?.image_base64}
                            alt={entity?.title}
                            objectFit="cover"
                        />
                    </Container>

                    {/* TITLE */}
                    <Container>
                        <Headings sizeTag={"h4"} property={""}>{entity?.title}</Headings>
                        <Container property={"flex flex-row gap-2 mt-2"}>
                            <Button variant="blueSmallNoHover" pointer={false} property="w-fit">Místo konání: {entity?.employer?.address}</Button>
                            <Button variant="blueSmallNoHover" pointer={false} property="w-fit">{entity?.start_date} - {entity?.end_date}</Button>
                        </Container>
                    </Container>

                </Container>
                {/* DESCRIPTION */}
                <Container property={"editor-content mt-2"}>
                    <Headings sizeTag="h3" property="mb-2">Popis pozice</Headings>
                    <Paragraph>{entity?.description}</Paragraph>
                </Container>

                {/* RESPONSIBILITY */}
                <Container property={"editor-content mt-4"}>
                    <Headings sizeTag="h3" property="mb-2">Náplň práce</Headings>
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

                    {/* TLAČÍTKA PRO SPRÁVU - DEPARTMENT A ORGANIZATION USERS */}
                    {user && (user.isDepartmentUser() || user.isOrganizationUser()) && (
                        <Container property="flex gap-4 justify-end">
                            <Button variant={"primary"} icon={"gear"} onClick={handlePopUp}>Spravovat</Button>
                        </Container>
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

            {/* PODÁNÍ PŘIHLÁŠKY - STUDENT */}
            {popUp && user && user.isStudent() && (
                <PopUpCon
                    useCustomContainer={true}
                    onClose={handlePopUp}
                    title={"Přihláška"}
                    text={"Opravdu si přejete podat přihlášku?"}
                    onSubmit={handleApply}
                    onSubmitText="Podat"
                    onReject={handlePopUp}
                    onRejectText="Zrušit"
                />
            )}

            {/* SCHVALOVÁNÍ PŘIHLÁŠKY - UČITEL/ORGANIZACE */}
            {popUp && user && (user.isDepartmentUser() || user.isOrganizationUser()) && (
                <PopUpCon
                    onClose={handlePopUp}
                    title={"Správa přihlášky"}
                    text={`Chcete schválit nebo zamítnout přihlášku studenta ${entity?.student_practice_status?.student_info?.full_name}?`}
                    onSubmit={handleApprove}
                    onSubmitText="Schválit"
                    onReject={handleReject}
                    onRejectText="Zamítnout"
                />
            )}

            {/* KONTROLA DOKUMENTŮ */}
            {docsPopUp && (
                <PopUpCon
                    useCustomContainer={true}
                    onClose={handleDocsPopUp}
                    title={"Kontrola dokumentů"}
                    text={"Proces není definován"}
                />
            )}
        </>
    )
}
