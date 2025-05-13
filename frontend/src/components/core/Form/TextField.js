import React, { useState, useCallback } from "react";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";

export default function TextField({id, property, label, placeholder, icon = false, required = false, value, onChange, type = "text", onIconClick}) {
    
    const [inputValue, setInputValue] = useState((value && id) ? {[id]: value} : {[id]: ""});
    const [showPassword, setShowPassword] = useState(false);

    const labelEntity = label ? <Paragraph>{label}</Paragraph> : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>
    const iconEntity = icon && <Button noVariant={true} icon={icon} iconColor={"text-black"} onClick={onIconClick}></Button>

    const inputClass = `w-full ${icon ? "pl-10 pr-2" : "px-2"} py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2`;
    
    const handleTextChange = useCallback((event) => {
        const { value } = event.target;
        
        // vytvoření nového slovníku s aktuální hodnotou
        const newDict = {
            [id]: value
        };
        
        // aktualizace interního stavu
        setInputValue(newDict);
        
        // předání nového slovníku rodičovské komponentě
        if (onChange) {
            onChange(newDict);
        }
    }, [id, onChange]);

    const togglePasswordVisibility = useCallback(() => {
        setShowPassword(prev => !prev);
    }, []);
    
    return (
        <Container property={property}>
            <Container property="flex items-center">
                {labelEntity}
                {required && requiredLabel}
            </Container>
            <Container property="relative">
                <input
                    type={type === "password" ? (showPassword ? "text" : "password") : type}
                    id={id} 
                    className={inputClass} 
                    placeholder={placeholder || ""} 
                    required={required}
                    value={inputValue[id] || ""}
                    onChange={handleTextChange}
                />
                {/* Variantas heslem */}
                {type === "password" && (
                    <Container property="absolute right-2 top-1/2 -translate-y-1/2">
                        <Button 
                            noVariant={true} 
                            icon={showPassword ? "eye-slash" : "eye"} 
                            iconColor={"text-black"} 
                            onClick={togglePasswordVisibility}
                        />
                    </Container>
                )}
                {icon && (
                    <Container property="absolute left-2 top-1/2 -translate-y-1/2">
                        {iconEntity}
                    </Container>
                )}
            </Container>
        </Container>
    );
}
