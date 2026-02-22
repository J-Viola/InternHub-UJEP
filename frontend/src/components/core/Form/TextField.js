import React, { useCallback, useState } from "react";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";

export default function TextField({id, property, label, placeholder, icon = false, required = false, value = "", onChange, type = "text", onIconClick, disabled = false, error = null}) {

    const [showPassword, setShowPassword] = useState(false);

    const labelEntity = label ? (
        <label htmlFor={id} className="block text-base font-medium text-gray-700">
            {label}
        </label>
    ) : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>
    const iconEntity = icon && <Button noVariant={true} icon={icon} iconColor={"text-black"} onClick={onIconClick}></Button>

    const borderColor = error ? "border-red-500" : "border-gray-300";
    const inputClass = `w-full ${icon ? "pl-10 pr-2" : "px-2"} py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 ${borderColor} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`;

    const handleTextChange = useCallback((event) => {
        if (onChange) {
            onChange({[id]: event.target.value});
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
                    name={id}
                    className={inputClass}
                    placeholder={placeholder || ""}
                    required={required}
                    aria-required={required}
                    aria-label={label || placeholder || id}
                    aria-invalid={!!error}
                    aria-describedby={error ? `${id}-error` : undefined}
                    value={value}
                    onChange={handleTextChange}
                    disabled={disabled}
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
            {error && <Paragraph id={`${id}-error`} property="text-red-500 text-sm mt-1" role="alert">{error}</Paragraph>}
        </Container>
    );
}
