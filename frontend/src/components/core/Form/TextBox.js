import React, { useState, useEffect, useCallback } from "react";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";

export default function TextBox({id, label, required = false, placeholder, value, rows = 5, onChange, error = null}) {
    const [inputValue, setInputValue] = useState(value || "");

    useEffect(() => {
        setInputValue(value || "");
    }, [value]);
    
    // Měníme labelEntity na skutečný <label> element
    const labelEntity = label ? (
        <label htmlFor={id} className="block text-base font-medium text-gray-700">
            {label}
        </label>
    ) : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>

    const borderColor = error ? "border-red-500" : "border-gray-300";
    const inputClass = `w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 ${borderColor}`;
    
    const handleTextChange = useCallback((event) => {
        const newValue = event.target.value;
        setInputValue(newValue);
        
        if (onChange) {
            onChange({
                [id]: newValue
            });
        }
    }, [id, onChange]);
    
    return (
        <Container>
            <Container property="flex items-center">
                {labelEntity}
                {required && requiredLabel}
            </Container>
            <textarea 
                id={id}
                rows={rows}
                className={inputClass}
                placeholder={placeholder || ""}
                value={inputValue}
                onChange={handleTextChange}
            />
            {error && <Paragraph property="text-red-500 text-sm mt-1">{error}</Paragraph>}
        </Container>
    );
}
