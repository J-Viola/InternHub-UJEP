import React, { useState, useCallback, useEffect } from "react";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";

export default function DropDown({id, property, label, placeholder, icon = false, required = false, value, onChange, options = [], onIconClick, hover = false,  variant = "default", disableDefault = false, disabled = false}) {
    const [selectedValue, setSelectedValue] = useState((value && id) ? {[id]: value} : {[id]: ""});

    // Synchronizace default value
    useEffect(() => {
        if (value !== undefined) {
            setSelectedValue({[id]: value});
        }
    }, [value, id]);

    const labelEntity = label ? <Paragraph>{label}</Paragraph> : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>
    const iconEntity = icon && <Button noVariant={true} hover={false} pointer={false} icon={icon} iconColor={"text-black"} onClick={onIconClick}></Button>

    const variants = {
        default: "w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 border-gray-300",
        facultyGreen: `w-full px-2 py-1 text-base text-black bg-facultyColLight rounded-lg border border-black ${hover ? "hover:bg-facultyCol transition-colors duration-200" : ""}`,
        blue: "w-full px-2 py-1 text-base text-white bg-blue-500 rounded-lg border-2 border-blue-500 hover:bg-blue-600 transition-colors duration-200",
        red: "w-full px-2 py-1 text-base text-white bg-red-500 rounded-lg border-2 border-red-500 hover:bg-red-600 transition-colors duration-200"
    };

    const selectClass = `${variants[variant] || variants.default} ${icon ? "pl-10 pr-2" : "px-2"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`;
    
    const handleSelectChange = useCallback((event) => {
        if (disabled) return;
        
        const { value } = event.target;
        
        const newDict = {
            [id]: value
        };
        
        setSelectedValue(newDict);
        
        if (onChange) {
            onChange(newDict);
        }
    }, [id, onChange, disabled]);
    
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
                    disabled={disabled}
                    value={selectedValue[id] || ""}
                    onChange={handleSelectChange}
                >
                    <option value="" disabled={disableDefault}>{placeholder || "Vyberte možnost"}</option>
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