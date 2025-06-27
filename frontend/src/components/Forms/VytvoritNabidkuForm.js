import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import {makeQuery} from "@hooks/SearchParams";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";


export default function VytvoritNabidkuForm() {
  const nabidkaAPI = useNabidkaAPI();

  // State for all form fields
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [spravceInzeratu, setSpravceInzeratu] = useState("");
  const [predmet, setPredmet] = useState("");
  const [nazev, setNazev] = useState("");
  const [popisStaze, setPopisStaze] = useState("");
  const [odpovednostStaze, setOdpovednostStaze] = useState("");

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    const data = {
      start_date: startDate.startDate,
      end_date: endDate.endDate,
      employer_id:spravceInzeratu.spravceInzeratu,
      subject_id:predmet.predmet,
      name:nazev.nazev,
      description:popisStaze.popisStaze,
      responsibilities:odpovednostStaze.odpovednostStaze,
    };
    console.log(data);
    await nabidkaAPI.createNabidka(data);
  };

  return (
    <>
      <Container property={"grid gap-2 grid-cols-2"}>
        <CustomDatePicker
          id={"startDate"}
          selected={startDate}
          label={"Čas období od"}
          required={true}
          onChange={setStartDate}
        />

        <CustomDatePicker
          id={"endDate"}
          selected={endDate}
          label={"Čas období do"}
          required={true}
          onChange={setEndDate}
        />

        <DropDown
          id={"spravceInzeratu"}
          required={true}
          label={"Správce inzerátu"}
          icon={"user"}
          options={[
            { value: "1", label: "volba1" },
            { value: "2", label: "volba2" }
          ]}
          onChange={setSpravceInzeratu}
        />

        <DropDown
          id={"predmet"}
          required={true}
          label={"Přiřazený předmět"}
          icon={"book"}
          options={[
            { value: "1", label: "volba1" },
            { value: "2", label: "volba2" }
          ]}
          onChange={setPredmet}
        />
      </Container>

      <Container property={"w-full gap-2 mt-2 flex-cols"}>
        <TextField
          id={"nazev"}
          required={true}
          label={"Název"}
          placeholder={"Název stáže"}
          onChange={setNazev}
        />

        <TextBox
          id={"popisStaze"}
          required={true}
          label={"Popis stáže"}
          placeholder={"Napište popis stáže"}
          onChange={setPopisStaze}
        />

        <TextBox
          id={"odpovednostStaze"}
          required={true}
          label={"Odpovědnost stáže"}
          placeholder={"Popište odpovědnost stáže"}
          onChange={setOdpovednostStaze}
        />
      </Container>

      {/* PROSTOR PRO TLAČÍKO */}
      <Container property={"flex w-full justify-end ml-auto"}>
        <Button
          property={"mt-2 px-16"}
          onClick={handleFormSubmit}
        >
          Vytvořit
        </Button>
      </Container>
    </>
  );
}
