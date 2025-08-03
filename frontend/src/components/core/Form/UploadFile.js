import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";
import { useState, useRef } from "react";
import { Image } from "@core/Image";

export default function UploadFile({
    id, 
    previewOn = false, 
    property = "", 
    label, 
    onChange, 
    onIconClick, 
    icon = "upload", 
    accept, 
    iconPointer = false,
    iconColor = "text-gray-900"
}) {

    const baseClass = `flex flex-row items-center w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 hover:bg-gray-200 gap-2 ${property}`;
    const fileInputRef = useRef(null);
    const [preview, setPreview] = useState(null);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const objectUrl = URL.createObjectURL(file);
            setPreview(objectUrl);
            if (onChange) {
                onChange(file);
            } else {
                console.log('UploadFile - onChange není definován, vybraný soubor:', file);
            }
        }
    }

    const handleClick = () => {
        if (onIconClick) {
            onIconClick();
        } else {
            console.log('UploadFile - onIconClick není definován');
        }
        fileInputRef.current?.click();
    }

    return (
        <Container property={baseClass} onClick={handleClick}>
            <label htmlFor={id} className="flex items-center gap-2 cursor-pointer" onClick={handleClick}>
                <Button property={"cursor-pointer"} noVariant={true} icon={icon} iconColor={iconColor} pointer={iconPointer}></Button>
                <Paragraph property={"text-gray-900"}>{label}</Paragraph>
            </label>
            <input 
                ref={fileInputRef}
                type="file" 
                id={id} 
                className="hidden" 
                onChange={handleFileChange} 
                accept={accept} 
            />
            {previewOn && preview && (
                <Container property={"mt-2 justify-center ml-auto"}>
                    <Image 
                        src={preview} 
                        alt={"Preview"} 
                        width={"200"} 
                        height={"200"} 
                        objectFit={"contain"}
                        property={"max-w-[200px] max-h-[200px]"}
                    />
                </Container>

            )}
        </Container>
    )
}