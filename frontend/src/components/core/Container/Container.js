import React from "react";


export default function Container({id, children, property, onMouseEnter, onMouseLeave, onClick}) {
    
    return(
        <div 
            id={id}
            className={`${property || ""}`} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave} onClick={onClick}
        >
        {children}
        
        </div>
    )
}