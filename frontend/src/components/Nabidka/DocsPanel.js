import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Nav from "@components/core/Nav";
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@core/Text/Headings"
import Button from "@core/Button/Button";
import { useUser } from "@hooks/UserProvider";
import handleToDoAlert from "@utils/ToDoAlert"


function DocContainer({doc_info, handleDownload, handleUpload}) {

    const renderTitle = () => {
        if(doc_info.type === "contract") {
            return "Návrh smlouvy"
        }
        else if(doc_info.type === "content") {
            return "Náplň stáže"
        }
        else if(doc_info.type === "feedback") {
            return "Zpětná vazba"
        }
    }
    return(
        <ContainerForEntity property={"mb-2"}>
            <Container property={"flex flex-col w-full gap-4 p-4 bg-gray-50 rounded-lg"}>
                <Headings sizeTag={"h4"}>{renderTitle()}</Headings>
                {/*STÁHNOUT SOUBOR*/}
                <Button onClick={() => handleDownload(doc_info.id)} property={"w-full"} disabled={!doc_info.id}>
                    Stáhnout soubor
                </Button>
                {/*NAHRÁT SOUBOR*/}
                <Button onClick={() => handleUpload(doc_info.id)} property={"w-full"} disabled={!doc_info.id}>
                    Nahrát soubor
                </Button>

            </Container>
        </ContainerForEntity>
    )
}


export default function DocsPanel({ entity, docData, handleDownload, handleUpload, handleManage }) {

    const STATUS = entity.progress_status;
    const { user } = useUser();

    if (!Array.isArray(docData)) return null;

    return(
        <ContainerForEntity property={"pl-8 pr-8 mb-2"}>
            <Container property={"flex flex-cols gap-1 inline-block"}>
                <Paragraph>Kontrola dokumentu:</Paragraph>
                {STATUS ? 
                <Paragraph property={"text-green-600"}>PROBĚHLA</Paragraph>
                :
                <Paragraph property={"text-red-600"}>NEPROBĚHLA</Paragraph>
                }
                 
            </Container>
            <Headings sizeTag="h3">Dokumenty</Headings>

            {/* CONTAINERY DOKUMENTŮ */}
            <Container property={"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mt-4"}>
                {docData.map((doc_info, index) => (
                    <DocContainer key={index} doc_info={doc_info} handleDownload={handleDownload} handleUpload={handleUpload} />
                ))}
            </Container>

            <Container property={"w-full mt-2 mb-2 flex justify-end"}>
                {/* KONTROLA DOKUMENTŮ . debug -> pro studenta */}
                {user.isDepartmentMg() && (
                    <Button variant={"yellow"} 
                        onClick={() => {
                        handleManage();

                    }}>
                        Kontrola dokumentů
                    </Button>
                )}
            </Container>
        </ContainerForEntity>
    )
}