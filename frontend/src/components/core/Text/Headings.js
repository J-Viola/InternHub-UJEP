import React from 'react';

export default function Headings({ children, sizeTag = 'h4', property }) {
    
    const headingVariants = {
        'h5': "text-xl font-normal",
        'h5-bold': "text-xl font-bold",
        'h4': "text-2xl font-semibold",
        'h3': "text-4xl font-semibold",
        'h2': "text-5xl font-semibold",
        'h1': "text-7xl font-semibold"
    };

    return (
        React.createElement(
            sizeTag,
            { className: `${headingVariants[sizeTag] || headingVariants.h4} ${property || ''}`.trim() },
            children
        )
    );
}