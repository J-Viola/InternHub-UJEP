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

    // BL-07/PBUG-BL07-08: sizeTag je STYL, ne HTML tag — 'h5-bold' musí
    // vygenerovat skutečný <h5>, jinak vznikne nevalidní <h5-bold>
    // (žádná heading role → a11y a testovatelnost trpí). Styl se zachová.
    const headingTag = sizeTag === 'h5-bold' ? 'h5' : (headingVariants[sizeTag] ? sizeTag : 'h4');

    return (
        React.createElement(
            headingTag,
            { className: `${headingVariants[sizeTag] || headingVariants.h4} ${property || ''}`.trim() },
            children
        )
    );
}
