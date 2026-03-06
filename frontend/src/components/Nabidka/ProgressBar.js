import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";
import { useTranslation } from "react-i18next";

export default function ProgressPanel({
    subject,
    currentValueSingle,
    goalValueSingle,
    noteSingle,
    currentValueAll,
    goalValueAll,
    noteAll,
    title,
    property = ""
}) {
    const { t } = useTranslation();
    const progressPercentageSingle = goalValueSingle > 0 ? (currentValueSingle / goalValueSingle) * 100 : 0;
    const progressPercentageAll = goalValueAll > 0 ? (currentValueAll / goalValueAll) * 100 : 0;
    const fillColor = '#1CAA34';
    const emptyColor = '#e5e7eb';

    const displayTitle = title || t('progress.title');
    const displayNoteSingle = noteSingle || t('progress.note_single');
    const displayNoteAll = noteAll || t('progress.note_all');

    return (
        <ContainerForEntity property={"pl-8 pr-8"}>
            <Container property={`${property}`}>
                {/* Header */}
                {displayTitle && (
                    <Container property="mb-2">
                        <Headings sizeTag="h4" property="text-gray-800 mb-2">
                            {displayTitle}
                        </Headings>
                    </Container>
                )}

                {/* Progress Bar pro aktuální kartu */}
                {displayNoteSingle && (
                    <Paragraph property="mb-1 text-sm text-gray-700">
                        {`${displayNoteSingle} ${subject}`}
                    </Paragraph>
                )}
                <Container property="mb-2 m-4">
                    <div
                        style={{
                            width: '100%',
                            height: '0.75rem',
                            borderRadius: '9999px',
                            background: `linear-gradient(to right, ${fillColor} ${progressPercentageSingle}%, ${emptyColor} ${progressPercentageSingle}%)`,
                            transition: 'background 0.5s ease-in-out',
                        }}
                        className="mb-2"
                    />
                    {/* Progress Values - aktuální karta/kritérium */}
                    <Container property="flex justify-between items-center">
                        <Paragraph property="text-sm text-gray-600">
                            {currentValueSingle}h / {goalValueSingle}h
                        </Paragraph>
                        <Paragraph property="text-sm text-gray-600 font-medium">
                            {t('progress.criterion_fulfillment')}: {Math.round(progressPercentageSingle)}%
                        </Paragraph>
                    </Container>

                </Container>
            </Container>

            {/* CELKOVÝ PROGRESS NA VŠECH KARTÁCH */}

           {currentValueAll && goalValueAll && (
            <Container property={`${property}`}>
            {/* POZNÁMKA */}
            {displayNoteAll && (
                <Paragraph property="mb-1 text-sm text-gray-700">
                    {`${displayNoteAll} ${subject}`}
                </Paragraph>
            )}
                <Container property="mb-2 m-4">
                    <div
                        style={{
                            width: '100%',
                            height: '0.75rem',
                            borderRadius: '9999px',
                            background: `linear-gradient(to right, ${fillColor} ${progressPercentageAll}%, ${emptyColor} ${progressPercentageAll}%)`,
                            transition: 'background 0.5s ease-in-out',
                        }}
                        className="mb-2"
                    />
                    {/* Progress Values - aktuální karta/kritérium */}
                    <Container property="flex justify-between items-center">
                        <Paragraph property="text-sm text-gray-600">
                            {currentValueAll}h / {goalValueAll}h
                        </Paragraph>
                        <Paragraph property="text-sm text-gray-600 font-medium">
                            {t('progress.criterion_fulfillment')}: {Math.round(progressPercentageAll)}%
                        </Paragraph>
                    </Container>

                </Container>
            </Container>
            )}

        </ContainerForEntity>
    );
}
