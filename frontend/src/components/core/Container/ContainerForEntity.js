import React from "react";

export default function ContainerForEntity({id, children, property, onClick, variant = "gray"}) {

    const defaultClass = "border border-black rounded-[10px]"

    const variants = {
        "yellow": "bg-[#fef3c7] " + defaultClass,
        "gray": "bg-[#f9fafb] " + defaultClass,
        "red": "bg-red-50 " + defaultClass,
        "green": "bg-green-50 " + defaultClass,
        "blue": "bg-[#cffafe] " + defaultClass,
        "white": "bg-white " + defaultClass,
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
