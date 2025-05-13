import React, { useState } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Nav from "@components/core/Nav";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import { useParams } from "react-router-dom";
import HTMLReactParser from "html-react-parser";
import Button from "@core/Button/Button";
import DocsPanel from "@components/Nabidka/DocsPanel";
import PopUpCon from "@core/Container/PopUpCon";

export default function NabidkaDetailPage() {
    const { id } = useParams();
    const [popUp, setPopUp] = useState(false);

    const handlePopUp = () => {
        setPopUp(!popUp);
    }

    const onSubmit = () => {
        console.log("Přihláška podána");
    }

    const onReject = () => {
        console.log("Přihláška odmítnuta");
    }

    //PODLE USERA ZE SESSION UKÁŽU PŘÍSLUŠNOU PODOBU TÉTO STRÁNKY 
    // (udělat variantu volné nabídky a následně probíhající/spravované podle API callu před vypsáním (status - je moje přiřazení?))

    const entity = {
        "id": "1",
        "title": "Apple IOS Developer",
        "time": "1.1.2025 - 30.5.2025",
        "annotation": '<ul><li><strong>DASDASDASDASDASD</strong></li><li><em>ASDASDASDAas</em></li><li><img src="https://media.makeameme.org/created/asdasd-asdasdasd-0nsn5i.jpg" class="sFlh5c FyHeAf iPVvYb" style="max-width: 600px; width: 600px; height: 399px; margin: 0px;" alt="asdasd asdasdasd - Satisfied Seal Meme Generator" aria-hidden="false"></li></ul><h1><br></h1><h2>Lorem ipsum dolor sit amet, </h2><p><br></p><p><br></p><p>consectetuer adipiscing elit. Etiam posuere lacus quis dolor. Donec vitae arcu. Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Nullam at arcu a est sollicitudin euismod. Nam sed tellus id magna elementum tincidunt. Cras elementum. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Morbi leo mi, nonummy eget tristique non, rhoncus non leo. In sem justo, commodo ut, suscipit at, pharetra vitae, orci. Morbi leo mi, nonummy eget tristique non, rhoncus non leo. Nunc tincidunt ante vitae massa. Morbi imperdiet, mauris ac auctor dictum, nisl ligula egestas nulla, et sollicitudin sem purus in lacus. Mauris elementum mauris vitae tortor. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Aliquam erat volutpat.</p><p><br></p>',
        "adress": "Praha, Česká republika"
    }


    //
    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                {/* PODLE PŘÍZNAKU */}
                <DocsPanel/>
                <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                    {/*<BackButton/>*/}
                    <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-4">
                            
                        {/* LOGO */}
                        <Container property="w-md bg-blue-600 rounded-lg p-4 flex items-center justify-center">
                            <Headings sizeTag="h4" property="text-white">
                                {"LOGO"}
                            </Headings>
                        </Container>

                        {/* TITLE */}
                        <Container>
                            <Headings sizeTag={"h4"} property={""}>{entity.title} | {id}</Headings>
                            <Container property={"flex flex-row gap-2"}>
                                <Button variant="blueSmallNoHover" pointer={false} property="w-fit">Místo konání: {entity.adress}</Button>
                                <Button variant="blueSmallNoHover" pointer={false} property="w-fit">{entity.time}</Button>
                            </Container>
                        </Container>

                    </Container>
                    {/* ANNOTATION */}
                    <Container property={"editor-content mt-2"}>
                        {HTMLReactParser(entity.annotation)}
                    </Container>

                    <Container property={"grid grid-cols-1 gap-8"}>
                        <Button className="col-start-1 justify-self-end" onClick={handlePopUp}>Podat přihlášku</Button>
                    </Container>
                </ContainerForEntity>
                
            </Container>

            {popUp && (
                <PopUpCon 
                    onClose={handlePopUp} 
                    title="Přihláška" 
                    text={"Opravdu si přejete podat přihlášku?"}
                    onSubmit={onSubmit}
                    onReject={onReject}
                ></PopUpCon>
            )}
        </Container>
    )
} 