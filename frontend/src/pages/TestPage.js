import Paragraph from "../components/core/Text/Paragraph";
import Headings from "../components/core/Text/Headings";
import ContainerForEntity from "../components/core/Container/ContainerForEntity";
import Container from "../components/core/Container/Container";
import Button from "../components/core/Button/Button";
import Nav from "../components/core/Nav";

function Test() {

  const handleClick = () => {
    console.log("Clicked")
  }

  return (
    <Container property="App">
      <header className="App-header">
        <Paragraph variant={"largeBold"}>Test par</Paragraph>
        <button className="bg-blue-500 hover:bg-blue-300 text-white font-bold py-2 px-4 rounded"
          onClick = {() => console.log("Tailwind je ready!!")}
        >
          <Paragraph variant={"baseBold"}>Ahoj</Paragraph>
        </button>
      </header>
        <Nav></Nav>
        <Headings sizeTag={"h1"} property={"text-red-600"}>Heading 1</Headings>
        <Headings sizeTag={"h2"}>Heading 2</Headings>
        <Headings sizeTag={"h3"}>Heading 3</Headings>
        <Headings sizeTag={"h4"}>Heading 4</Headings>

        <ContainerForEntity variant={"green"}>
          <Headings sizeTag={"h4"}>Heading 2</Headings>
        </ContainerForEntity>

        <Container property={"bg-blue-200"}>
          <Headings sizeTag={"h2"}>Heading 1</Headings>
        </Container>

        <Button text={"Zmáčkni mě"} property={"mt-4 ml-4"} variant = {"redSmall"} onClick={handleClick} icon={"cross"}/>
        
        <Button property={"mt-4"} onClick={handleClick}>
          <Paragraph>Ahoj</Paragraph>
        </Button>

    </Container>
  );
}

export default Test;
