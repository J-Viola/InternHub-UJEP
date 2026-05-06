import React from "react";
import Container from "@core/Container/Container";
import Paragraph from "@core/Text/Paragraph";

const LoadingState = ({ message }) => {
    return (
        <Container property="flex flex-col items-center justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4" />
            <Paragraph property="text-gray-500">{message}</Paragraph>
        </Container>
    );
};

export default LoadingState;
