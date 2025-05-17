import React from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";

export default function SearchBar({ value, onChange, onClear }) {
    const inputClass = `w-full py-1 px-2 text-black bg-facultyColLight rounded-lg border border-black placeholder-gray-800`;

    return (
        <Container property="relative inline-block w-full items-center justify-center">
            <input
                type={"text"}
                id={"search"} 
                className={inputClass} 
                placeholder={"Hledat..."} 
                value={value}
                onChange={onChange}
            />
            <Container property="absolute right-2 top-1/2 -translate-y-1/2">
                {value !== "" && <Button noVariant={true} icon={"cross"} iconColor="text-black" onClick={onClear}/>}
            </Container>
        </Container>
    )
}
