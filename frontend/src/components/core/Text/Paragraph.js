import React from "react";

export default function Paragraph({ children, variant = "base", property, onClick, id, className }) {

    const variants = {
        baseBold: "font-bold text-base",
        base: "font-normal text-base",
        small: "font-normal text-sm",
        tiny: "font-normal text-xs",
        largeBold: "font-bold text-lg",
        large: "font-normal text-lg",
        red: "font-normal text-red-300",
        green: "font-normal text-green-300"
    };

    return (
        <p 
            id={id}
            className={`${variants[variant] || variants.base} ${property || ''} ${className || ''} ${onClick ? 'cursor-pointer' : ''}`}
            onClick={onClick}
        >
            {children}
        </p>
    );
}