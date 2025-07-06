import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";

export default function ProgressPanel({ 
    currentValueSingle = 100, 
    goalValueSingle = 500, 
    noteSingle = "Plnění aktuální karty v rámci kritéria předmětu: XXX",
    currentValueAll =200,
    goalValueAll = 500,
    noteAll = "Plnění všech probíhajících karet v rámci kritéria předmětu: XXX",
    title = "Průběh",
    property = ""
}) {
    const progressPercentageSingle = goalValueSingle > 0 ? (currentValueSingle / goalValueSingle) * 100 : 0;
    const progressPercentageAll = goalValueAll > 0 ? (currentValueAll / goalValueAll) * 100 : 0;
    const fillColor = '#1CAA34'; 
    const emptyColor = '#e5e7eb';
    
    return (
        <ContainerForEntity>
            <Container property={`${property}`}>
                {/* Header */}
                {title && (
                    <Container property="mb-2">
                        <Headings sizeTag="h4" property="text-gray-800 mb-2">
                            {title}
                        </Headings>
                    </Container>
                )}

                {/* Progress Bar pro aktuální kartu */}
                {noteSingle && (
                    <Paragraph property="mb-1 text-sm text-gray-700">
                        {noteSingle}
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
                            Naplnění kritéria: {Math.round(progressPercentageSingle)}%
                        </Paragraph>
                    </Container>
                    
                </Container>
            </Container>

            {/* CELKOVÝ PROGRESS NA VŠECH KARTÁCH */}
            <Container property={`${property}`}>
                {/* POZNÁMKA */}
                {noteAll && (
                    <Paragraph property="mb-1 text-sm text-gray-700">
                        {noteAll}
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
                            Naplnění kritéria: {Math.round(progressPercentageAll)}%
                        </Paragraph>
                    </Container>
                    
                </Container>
            </Container>
        </ContainerForEntity>
    );
}