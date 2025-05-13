import React, {useState, useCallback, useEffect} from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Paragraph from "@components/core/Text/Paragraph";

export default function LoginSwitch({getLoginType}) {
    const logTypes = ["STAG", "Department"]

    // Barevné varianty stavů
    const selectedCol = "text-blue-800"
    const basicCol = "text-blue-300"

    const [colorTypes, setColors] = useState([
        {"STAG": basicCol},
        {"Department": basicCol}
    ])
    
    const [selectedType, setSelectedType] = useState({"switch": logTypes[0]}) /* INIT bude stag */

    const handleColorChange = useCallback((id) => {
        const newColors = colorTypes.map(item => {
            const key = Object.keys(item)[0];
            return { [key]: key === id ? selectedCol : basicCol };
        });
        setColors(newColors);
    }, [colorTypes]);

    const handleSwitch = useCallback((event) => {
        const clickedId = event.target.id;
        const newState = {"switch": clickedId};
        
        // Lokální stav
        setSelectedType(newState);
        
        // Callback s novou hodnotou
        getLoginType(newState);
        
        // Aktualizujeme barvy
        handleColorChange(clickedId);
    }, [getLoginType, handleColorChange]);

    useEffect(() => {
        handleColorChange(selectedType.switch);
        getLoginType(selectedType);
    }, []);

    return(
        <>
            <Container property={"w-full flex flex-row items-center justify-start gap-2 mb-4"} >
                <Container>
                    <Paragraph id="STAG" variant={"largeBold"} property={colorTypes[0]["STAG"]} onClick={handleSwitch}>STAG</Paragraph>
                </Container>

                <Container>
                    <Paragraph id="/" variant={"largeBold"}>/</Paragraph>
                </Container>

                <Container>
                    <Paragraph id="Department" variant={"largeBold"} property={colorTypes[1]["Department"]} onClick={handleSwitch}>Jsem firma</Paragraph>
                </Container>
            </Container>
        </>
    )
}