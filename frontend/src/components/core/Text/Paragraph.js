import React from "react";

export default function Paragraph({ children, variant = "base", property, onClick, id }) {

    const variants = {
        baseBold: "font-bold text-base",
        base: "font-normal text-base",
        small: "font-normal text-sm",
        tiny: "font-normal text-xs",
        largeBold: "font-bold text-lg",
        large: "font-normal text-lg"
    };

    return (
        <p 
            id={id}
            className={`${variants[variant] || variants.base} ${property || ''} ${onClick ? 'cursor-pointer' : ''}`}
            onClick={onClick}
        >
            {children}
        </p>
    );
}