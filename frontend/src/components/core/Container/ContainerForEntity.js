import React from "react";

export default function ContainerForEntity({id, children, property, onClick, variant = "gray"}) {

    const defaultClass = "border border-black rounded-lg p-2"

    const variants = {
        "yellow": "bg-yellow-100 " + defaultClass,
        "gray": "bg-gray-50 " + defaultClass,
        "red": "bg-red-50 " + defaultClass,
        "green": "bg-green-50 " + defaultClass,
    }

    return(
        <div 
            className={`${variants[variant]} ${property || ""} ${onClick ? "cursor-pointer" : ""}`}
            id={id}
            onClick={onClick}
        >
            {children}
        </div>
    )
}