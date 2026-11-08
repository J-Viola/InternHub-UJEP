import React from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import { FiSearch } from "react-icons/fi";

export default function SearchBar({ id = "title", value, placeholder, onChange, onClear, variant = "default" }) {

    const isStudent = variant === "student";

    const inputClass = isStudent
        ? "w-full h-11 px-10 text-black bg-[#cffafe] rounded-[10px] border-none focus:ring-0 outline-none transition-all placeholder-black/60 text-center font-medium text-base"
        : "w-full py-2 px-10 text-black bg-white rounded-lg border border-gray-300 focus:border-facultyCol outline-none transition-colors placeholder-gray-400 shadow-sm";

    return (
        <Container property="relative inline-block w-full items-center justify-center">
            {!isStudent && (
                <Container property="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
                    <FiSearch size={18} />
                </Container>
            )}
            <input
                type={"text"}
                id={id}
                className={inputClass}
                placeholder={placeholder ? placeholder : "Hledat"}
                aria-label={placeholder ? placeholder : "Hledat"}
                value={value || ""}
                onChange={onChange}
            />
            <Container property="absolute right-4 top-1/2 -translate-y-1/2">
                {value !== "" && (
                    <Button
                        title={"Vymazat"}
                        noVariant={true}
                        icon={"cross"}
                        iconColor="text-black"
                        iconSize="24"
                        onClick={onClear}
                    />
                )}
            </Container>
        </Container>
    )
}
