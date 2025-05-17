import React, {useState, useEffect, useCallback} from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Headings from "@components/core/Text/Headings";
import LoginSwitch from "@login/LoginSwitch";
import Paragraph from "@components/core/Text/Paragraph";
import TextField from "@core/Form/TextField";

export default function LoginForm({handleSTAGLogin}) {
    // dodělat hook z parenta na informace z formuláře
    const [loginAccess, setLoginAccess] = useState({});

    const handleAccess = useCallback((newValues) => {
        setLoginAccess(prevState => ({
            ...prevState,
            ...newValues
        }));
        
    }, []);

    useEffect(() => {
        console.log("LoginAccess", loginAccess);
    }, [loginAccess]);

    const handleButtonClick = () => {
        console.log("ButtonClick");
    }
    
    return (
        <Container property="min-h-screen flex items-center justify-center p-0 mx-auto">
            <Container property="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
                <LoginSwitch getLoginType={handleAccess}/>
                <Headings sizeTag="h4" property="text-center">Přihlášení</Headings>
                
               { loginAccess.switch !== "STAG" ? (
                <>
                <TextField 
                    id="name" 
                    onIconClick={handleButtonClick} 
                    icon="user" 
                    required={true} 
                    label="Přihlašovácí jméno" 
                    placeholder="Jméno" 
                    property="m-4"
                    onChange={handleAccess}
                />
                <TextField 
                    id="password"
                    type="password"
                    onIconClick={handleButtonClick} 
                    icon="lock" 
                    required={true} 
                    label="Heslo" 
                    placeholder="*****" 
                    property="m-4"
                    onChange={handleAccess}
                />
                </>
                ):
                (
                    <Container property="m-4">
                        <Paragraph property="text-center mb-16">Přihlášení pomocí systému STAG příslušné univerzity.</Paragraph>
                    </Container>
                )
                }

                <Button 
                    property={"w-full items-center"}
                    onClick={handleSTAGLogin}
                >
                    Přihlaste se             
                </Button>
            </Container>
        </Container>
    );
}

