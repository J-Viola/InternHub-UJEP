import React, {useState, useEffect, useCallback} from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Headings from "@components/core/Text/Headings";
import LoginSwitch from "@login/LoginSwitch";
import Paragraph from "@components/core/Text/Paragraph";
import TextField from "@core/Form/TextField";
import { useNavigate } from "react-router-dom";

export default function LoginForm({handleSTAGLogin, handleOrganizationLogin}) { 
    // dodělat hook z parenta na informace z formuláře
    const [loginAccess, setLoginAccess] = useState({});
    const navigate = useNavigate();

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
                    id="email" 
                    onIconClick={handleButtonClick} 
                    icon="user" 
                    required={true} 
                    label="E-mail" 
                    placeholder="E-mail" 
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

                {loginAccess.switch == "STAG" ? (
                    <>
                        {/* STAG LOGIN */}
                        <Button 
                            property={"w-full items-center"}
                            onClick={handleSTAGLogin}
                        >
                            Přihlaste se             
                        </Button>
                    </>
                       

                ):(
                    <>
                        {/* ORGANIZACE LOGIN */}
                        <Button 
                            property={"w-full items-center"}
                            onClick={() => handleOrganizationLogin(loginAccess)}
                        >
                            Přihlaste se             
                        </Button>

                        <Button 
                            property={"w-full items-center mt-2"}
                            variant="yellow"
                            onClick={() => navigate("/registrace")}
                        >
                            Registrace             
                        </Button>
                    </>
                )
                
                }


            </Container>
        </Container>
    );
}

