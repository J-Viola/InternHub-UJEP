import React, {useState, useRef} from "react";
import JoditEditor from "jodit-react"
import Container from "../Container/Container";

export default function TextEditor({contentValue, handleText}) {
    const editor = useRef(null)

    const handleTextChange = (e) => {
        handleText(e);
    }
    
    return(
        <Container property={"editor-content"}>
            <JoditEditor ref={editor} value={contentValue} toolbarAdaptive={false} onChange={(e) => handleTextChange(e)}/>
        </Container>
    )
}