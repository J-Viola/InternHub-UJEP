import React from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";
import Button from "@core/Button/Button";

/**
 * Component for displaying an empty state with an optional icon and call to action.
 */
const EmptyState = ({
    title,
    description,
    icon = "folder-open",
    actionText,
    onAction,
    property = ""
}) => {
    return (
        <Container property={`flex flex-col items-center justify-center py-16 px-4 text-center bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 ${property}`}>
            <Container property="bg-white p-6 rounded-full shadow-sm mb-6 text-gray-300">
                <Button icon={icon} noVariant={true} iconSize="48" pointer={false} hover={false} />
            </Container>

            <Headings sizeTag="h4" property="text-gray-900 font-bold mb-2">
                {title}
            </Headings>

            <Paragraph property="text-gray-500 max-w-md mb-8">
                {description}
            </Paragraph>

            {actionText && onAction && (
                <Button variant="primary" onClick={onAction} property="px-8">
                    {actionText}
                </Button>
            )}
        </Container>
    );
};

export default EmptyState;
