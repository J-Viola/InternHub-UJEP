import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@core/Text/Headings"
import Button from "@core/Button/Button";
import { useUser } from "@hooks/UserProvider";
import { useTranslation } from "react-i18next";


function DocContainer({doc_info, handleDownload, handleUpload, handleReview, isProfessor}) {
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

    const getStatusLabel = (status) => {
        switch(status) {
            case 1: return { label: t('docs.status_approved'), color: 'text-green-600', bg: 'bg-green-50' };
            case 2: return { label: t('docs.status_rejected'), color: 'text-red-600', bg: 'bg-red-50' };
            default: return { label: t('docs.status_pending'), color: 'text-yellow-600', bg: 'bg-yellow-50' };
        }
    }

    const statusInfo = getStatusLabel(doc_info.status);

    return(
        <ContainerForEntity property={"mb-2 hover:shadow-md transition-shadow duration-200"}>
            <Container property={`flex flex-col w-full gap-4 p-5 rounded-lg border-l-4 ${statusInfo.bg} ${statusInfo.color.replace('text', 'border')}`}>
                <Container property="flex justify-between items-start">
                    <Headings sizeTag={"h4"} property="text-gray-800 font-bold">{renderTitle()}</Headings>
                    <Container property={`${statusInfo.bg.replace('50', '200')} ${statusInfo.color} px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider`}>
                        {statusInfo.label}
                    </Container>
                </Container>

                {doc_info.review_note && (
                    <Container property="p-3 bg-white bg-opacity-60 rounded-md text-sm border border-gray-100">
                        <Paragraph property="text-gray-600 leading-relaxed">
                            <strong className="text-gray-700 block mb-1 underline">{t('docs.note')}:</strong> {doc_info.review_note}
                        </Paragraph>
                    </Container>
                )}

                <Container property="flex flex-col gap-3 mt-auto">
                    {/*STÁHNOUT SOUBOR*/}
                    <Button 
                        onClick={() => handleDownload(doc_info.id)} 
                        property="w-full shadow-sm" 
                        disabled={!doc_info.id}
                        variant={doc_info.id ? "primary" : "secondary"}
                    >
                        {t('docs.download_file')}
                    </Button>
                    
                    {/*NAHRÁT SOUBOR - Student or not approved */}
                    {!isProfessor && (
                        <Button 
                            onClick={() => handleUpload(doc_info.id)} 
                            property="w-full shadow-sm" 
                            disabled={!doc_info.id}
                            variant="secondary"
                        >
                            {t('docs.upload_file')}
                        </Button>
                    )}

                    {/*PROFESSOR REVIEW ACTIONS*/}
                    {isProfessor && doc_info.id && (doc_info.type === 'contract' || doc_info.type === 'content') && (
                        <Container property="flex gap-2 pt-2 border-t border-gray-100">
                            <Button 
                                variant="greenSmall" 
                                onClick={() => handleReview(doc_info.id, 1)} 
                                property="flex-1 shadow-sm"
                                disabled={doc_info.status === 1}
                            >
                                {t('common.approve')}
                            </Button>
                            <Button 
                                variant="redSmall" 
                                onClick={() => handleReview(doc_info.id, 2)} 
                                property="flex-1 shadow-sm"
                                disabled={doc_info.status === 2}
                            >
                                {t('common.reject')}
                            </Button>
                        </Container>
                    )}
                </Container>
            </Container>
        </ContainerForEntity>
    )
}


export default function DocsPanel({ entity, docData, handleDownload, handleUpload, handleManage, handleReview }) {
    const { t } = useTranslation();
    const STATUS = entity.progress_status;
    const { user } = useUser();

    if (!Array.isArray(docData)) return null;

    const isAuthorizedForReview = user.isDepartmentUser() || user.isAdmin();

    return(
        <ContainerForEntity property={"pl-8 pr-8 mb-2"}>
            <Container property={"flex items-center gap-3 mb-4"}>
                <Paragraph>{t('docs.check_status')}:</Paragraph>
                {STATUS ?
                    <Container property="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-bold border border-green-200 shadow-sm">
                        {t('docs.checked')}
                    </Container>
                    :
                    <Container property="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-bold border border-red-200 shadow-sm">
                        {t('docs.not_checked')}
                    </Container>
                }

            </Container>
            <Headings sizeTag="h3">{t('docs.title')}</Headings>

            {/* CONTAINERY DOKUMENTŮ */}
            <Container property={"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mt-4"}>
                {docData.map((doc_info, index) => (
                    <DocContainer 
                        key={index} 
                        doc_info={doc_info} 
                        handleDownload={handleDownload} 
                        handleUpload={handleUpload}
                        handleReview={handleReview}
                        isProfessor={isAuthorizedForReview}
                    />
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
