import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Nav from "@components/core/Nav";
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@core/Text/Headings"
import Button from "@core/Button/Button";


function DocContainer({doc_type}) {
    return(
        <ContainerForEntity property={"mb-2"}>
            <Container property={"flex flex-col w-full gap-4 p-4 bg-gray-50 rounded-lg"}>
                <Headings sizeTag={"h4"}>{doc_type.title}</Headings>
                {/*STÁHNOUT SOUBOR*/}
                <Button onClick={() => console.log(doc_type.download_api)} property={"w-full"} disabled={!doc_type.download_api}>
                    Stáhnout soubor
                </Button>
                {/*NAHRÁT SOUBOR*/}
                <Button onClick={() => console.log(doc_type.upload_api)} property={"w-full"} disabled={!doc_type.upload_api}>
                    Nahrát soubor
                </Button>
            </Container>
        </ContainerForEntity>
    )
}


export default function DocsPanel() {
    // udělat podle rolí jednotlivé layouty souborů a vlastnosti tlačítek (to načtu podle user => bud pres prop, nebo načtu hook)
    const doc_types = [
        {
            "title": "Návrh smlouvy",
            "download_api": "localhost:8000/api/docs/download/navrh_smlouvy",
            //"upload_api": "TADY BUDE FUNKCE NA VÝBĚR SOUBORU A PAK API CALL"
        
        },
        {
            "title": "Náplň stáže",
            "download_api": "localhost:8000/api/docs/download/napln_staze",
            "upload_api": "TADY BUDE FUNKCE NA VÝBĚR SOUBORU A PAK API CALL"
        
        },
        {
            "title": "Zpětná vazba",
            //"download_api": "localhost:8000/api/docs/download/zpetna_vatba",
            "upload_api": "TADY BUDE FUNKCE NA VÝBĚR SOUBORU A PAK API CALL"
        
        }
    ]

    // zatim
    const STATUS = true;

    return(
        <ContainerForEntity property={"mb-2"}>
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
                {doc_types.map((doc_type, index) => (
                    <DocContainer key={index} doc_type={doc_type} />
                ))}
            </Container>
        </ContainerForEntity>
    )
}