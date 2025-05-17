import React, {useState, useRef, useEffect} from "react";
import TextEditor from "@components/core/Text/TextEditor";
import HTMLReactParser from "html-react-parser";
import Container from "@core/Container/Container";

export default function TextEditorPage() {

    const [content, setContent] = useState("")

    const handleTextChange = (e) => {
        setContent(e);
    }

    useEffect(() => {
        console.log("Textový editor", content)
    },[content])


    return(
        <>
            <TextEditor contentValue={content} handleText={handleTextChange} />
            <p>{content}</p>
            <Container property={"editor-content"}>{HTMLReactParser(content)}</Container>
            
        </>
        
    )
}