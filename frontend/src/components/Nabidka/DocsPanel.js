import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@core/Text/Headings"
import Button from "@core/Button/Button";
import { useUser } from "@hooks/UserProvider";
import Icon from "@components/core/Icon/Icon";
import EmptyState from "@core/Feedback/EmptyState";


function DocContainer({doc_info, handleDownload, handleUpload, handleReview, isProfessor}) {

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

    const getStatusLabel = (status) => {
        switch(status) {
            case 1: return { label: "Schváleno", color: 'text-green-600', bg: 'bg-green-50' };
            case 2: return { label: "Vráceno k opravě", color: 'text-red-600', bg: 'bg-red-50' };
            default: return { label: "Čeká na kontrolu", color: 'text-yellow-600', bg: 'bg-yellow-50' };
        }
    }

    const statusInfo = getStatusLabel(doc_info.status);

    const formatUploadedAt = (isoString) => {
        if (!isoString) return null;
        const date = new Date(isoString);
        if (isNaN(date.getTime())) return null;
        return date.toLocaleDateString('cs-CZ');
    };

    return(
        <ContainerForEntity property={"mb-2 hover:shadow-md transition-shadow duration-200"}>
            <Container property={`flex flex-col w-full gap-4 p-5 rounded-lg border-l-4 ${statusInfo.bg} ${statusInfo.color.replace('text', 'border')}`}>
                <Container property="flex justify-between items-start">
                    <Headings sizeTag={"h4"} property="text-gray-800 font-bold">{renderTitle()}</Headings>
                    <Container property="flex items-center gap-2 flex-wrap justify-end">
                        {doc_info.late_submission && (
                            <Container property="bg-red-500 text-white px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider">
                                {"Odevzdáno po termínu"}
                            </Container>
                        )}
                        <Container property={`${statusInfo.bg.replace('50', '200')} ${statusInfo.color} px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider`}>
                            {statusInfo.label}
                        </Container>
                    </Container>
                </Container>

                {doc_info.uploaded_at && (
                    <Paragraph property="text-sm text-gray-500">
                        {"Nahráno"}: {formatUploadedAt(doc_info.uploaded_at)}
                    </Paragraph>
                )}

                {doc_info.review_note && (
                    <Container property="p-3 bg-white bg-opacity-60 rounded-md text-sm border border-gray-100">
                        <Paragraph property="text-gray-600 leading-relaxed">
                            <strong className="text-gray-700 block mb-1 underline">{"Poznámka"}:</strong> {doc_info.review_note}
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
                        {"Stáhnout soubor"}
                    </Button>

                    {/*NAHRÁT SOUBOR - Student or not approved */}
                    {!isProfessor && (
                        <Button
                            onClick={() => handleUpload(doc_info.id)}
                            property="w-full shadow-sm"
                            disabled={!doc_info.id}
                            variant="secondary"
                        >
                            {"Nahrát soubor"}
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
                                {"Schválit"}
                            </Button>
                            <Button
                                variant="redSmall"
                                onClick={() => handleReview(doc_info.id, 2)}
                                property="flex-1 shadow-sm"
                                disabled={doc_info.status === 2}
                            >
                                {"Zamítnout"}
                            </Button>
                        </Container>
                    )}
                </Container>
            </Container>
        </ContainerForEntity>
    )
}


export default function DocsPanel({ entity, docData, handleDownload, handleUpload, handleManage, handleReview }) {
    const STATUS = entity.progress_status;
    const { user } = useUser();

    if (!Array.isArray(docData)) return null;

    const isAuthorizedForReview = user.isDepartmentUser() || user.isAdmin();

    return(
        <ContainerForEntity property={"pl-8 pr-8 mb-2"}>
            {/* INFORMATIONAL BANNER FOR STUDENTS */}
            {user.isStudent() && entity?.student_practice_status?.workflow_status === "APPROVED" && STATUS === 0 && (
                <Container property="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6 rounded-r-lg shadow-sm flex items-start gap-3">
                    <Icon name="info-circle" size={20} color="text-blue-500" property="mt-0.5" />
                    <Paragraph property="text-blue-800 font-medium">
                        {"Vaše praxe byla schválena, ale může začít až po nahrání a schválení smlouvy a náplně praxe."}
                    </Paragraph>
                </Container>
            )}

            <Container property={"flex items-center gap-3 mb-4"}>
                <Paragraph>{"Kontrola dokumentu"}:</Paragraph>
                {STATUS ?
                    <Container property="bg-green-100 text-green-700 px-3 py-1 rounded-full text-sm font-bold border border-green-200 shadow-sm">
                        {"PROBĚHLA"}
                    </Container>
                    :
                    <Container property="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm font-bold border border-red-200 shadow-sm">
                        {"NEPROBĚHLA"}
                    </Container>
                }

            </Container>
            <Headings sizeTag="h3">{"Dokumenty"}</Headings>

            {/* CONTAINERY DOKUMENTŮ / EMPTY STATE */}
            {docData.length === 0 ? (
                <Container property="py-8">
                    <EmptyState
                        title={"Žádné dokumenty k dispozici"}
                        description={"Pro tuto praxi zatím nebyly vygenerovány nebo nahrány žádné dokumenty."}
                        icon="file-circle-xmark"
                    />
                </Container>
            ) : (
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
            )}

            <Container property={"w-full mt-2 mb-2 flex justify-end"}>
                {/* KONTROLA DOKUMENTŮ . debug -> pro studenta */}
                {(user.isDepartmentUser() || user.isAdmin()) && (
                    <Button variant={"yellow"}
                        onClick={() => {
                        handleManage();

                    }}>
                        {"Kontrola dokumentů"}
                    </Button>
                )}
            </Container>
        </ContainerForEntity>
    )
}
