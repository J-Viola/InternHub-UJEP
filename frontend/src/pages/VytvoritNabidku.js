import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Button from "@core/Button/Button";
import TextField from "@core/Form/TextField";
import TextBox from "@core/Form/TextBox";
import DropDown from "@core/Form/DropDown";
import CustomDatePicker from "@core/Form/DatePicker";
import VytvoritNabidkuForm from "@components/Forms/VytvoritNabidkuForm";


export default function VytvoritNabidku() {

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    <VytvoritNabidkuForm/>
                </Container>

            </Container>
        </Container>
    )
}