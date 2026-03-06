import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@core/Text/Headings"
import Button from "@core/Button/Button";
import { useUser } from "@hooks/UserProvider";
import { useTranslation } from "react-i18next";


function DocContainer({doc_info, handleDownload, handleUpload}) {
    const { t } = useTranslation();

    const renderTitle = () => {
        if(doc_info.type === "contract") {
            return t('docs.contract_draft')
        }
        else if(doc_info.type === "content") {
            return t('docs.internship_content')
        }
        else if(doc_info.type === "feedback") {
            return t('docs.feedback')
        }
    }
    return(
        <ContainerForEntity property={"mb-2"}>
            <Container property={"flex flex-col w-full gap-4 p-4 bg-gray-50 rounded-lg"}>
                <Headings sizeTag={"h4"}>{renderTitle()}</Headings>
                {/*STÁHNOUT SOUBOR*/}
                <Button onClick={() => handleDownload(doc_info.id)} property={"w-full"} disabled={!doc_info.id}>
                    {t('docs.download_file')}
                </Button>
                {/*NAHRÁT SOUBOR*/}
                <Button onClick={() => handleUpload(doc_info.id)} property={"w-full"} disabled={!doc_info.id}>
                    {t('docs.upload_file')}
                </Button>

            </Container>
        </ContainerForEntity>
    )
}


export default function DocsPanel({ entity, docData, handleDownload, handleUpload, handleManage }) {
    const { t } = useTranslation();
    const STATUS = entity.progress_status;
    const { user } = useUser();

    if (!Array.isArray(docData)) return null;

    return(
        <ContainerForEntity property={"pl-8 pr-8 mb-2"}>
            <Container property={"flex flex-cols gap-1 inline-block"}>
                <Paragraph>{t('docs.check_status')}</Paragraph>
                {STATUS ?
                <Paragraph property={"text-green-600"}>{t('docs.checked')}</Paragraph>
                :
                <Paragraph property={"text-red-600"}>{t('docs.not_checked')}</Paragraph>
                }

            </Container>
            <Headings sizeTag="h3">{t('docs.title')}</Headings>

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
                        {t('docs.doc_check')}
                    </Button>
                )}
            </Container>
        </ContainerForEntity>
    )
}
