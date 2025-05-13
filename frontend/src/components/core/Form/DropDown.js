import React, { useState, useCallback } from "react";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";

export default function DropDown({id, property, label, placeholder, icon = false, required = false, value, onChange, options = [], onIconClick}) {
    const [selectedValue, setSelectedValue] = useState((value && id) ? {[id]: value} : {[id]: ""});

    const labelEntity = label ? <Paragraph>{label}</Paragraph> : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>
    const iconEntity = icon && <Button noVariant={true} pointer={false} icon={icon} iconColor={"text-black"} onClick={onIconClick}></Button>

    const selectClass = `w-full ${icon ? "pl-10 pr-2" : "px-2"} py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2`;
    
    const handleSelectChange = useCallback((event) => {
        const { value } = event.target;
        
        const newDict = {
            [id]: value
        };
        
        setSelectedValue(newDict);
        
        if (onChange) {
            onChange(newDict);
        }
    }, [id, onChange]);
    
    return (
        <Container property={property}>
            <Container property="flex items-center">
                {labelEntity}
                {required && requiredLabel}
            </Container>
            <Container property="relative">
                <select
                    id={id}
                    className={selectClass}
                    required={required}
                    value={selectedValue[id] || ""}
                    onChange={handleSelectChange}
                >
                    <option value="" disabled>{placeholder || "Vyberte možnost"}</option>
                    {options.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
                {icon && (
                    <Container property="absolute left-2 top-1/2 -translate-y-1/2">
                        {iconEntity}
                    </Container>
                )}
            </Container>
        </Container>
    );
}