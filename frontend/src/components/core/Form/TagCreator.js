import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Paragraph from "@components/core/Text/Paragraph";

export default function TagCreator({
  label = "Skills",
  placeholder = "Zadejte skill...",
  value = [],
  onChange,
  disabled = false,
}) {
  const [input, setInput] = useState("");
  const [skills, setSkills] = useState(
    value && Array.isArray(value.skills) && value.skills.length > 0
      ? value.skills
      : ["Zde přidej svoje skills!"]
  );
  const [editIndex, setEditIndex] = useState(null);
  const [editValue, setEditValue] = useState("");

useEffect(() => {
  console.log(skills)
}, [skills])

  const makeDict = () => {
    const output = {"skills": [skills]}
    return output
  }

  const handleAdd = () => {
    if (!input.trim()) return;
    const newSkills = [...skills, input.trim()];
    setSkills(newSkills);
    setInput("");
    if (onChange) onChange(makeDict());
  };

  const handleDelete = (idx) => {
    const newSkills = skills.filter((_, i) => i !== idx);
    setSkills(newSkills);
    if (onChange) onChange(newSkills);
  };

  const handleEdit = (idx) => {
    setEditIndex(idx);
    setEditValue(skills[idx]);
  };

  const handleEditSave = (idx) => {
    if (!editValue.trim()) return;
    const newSkills = skills.map((s, i) => (i === idx ? editValue.trim() : s));
    setSkills(newSkills);
    setEditIndex(null);
    setEditValue("");
    if (onChange) onChange(newSkills);
  };

  const handleEditCancel = () => {
    setEditIndex(null);
    setEditValue("");
  };

  return (
    <Container property="w-full">
      {label && <Paragraph property="mb-1 font-semibold">{label}</Paragraph>}
      <Container property="flex gap-2 mb-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="px-2 py-1 border rounded w-full"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleAdd();
          }}
        />
        <Button
          icon="plus"
          variant="blueSmallNoHover"
          onClick={handleAdd}
          disabled={disabled || !input.trim()}
        />
      </Container>
      <Container property="flex flex-wrap gap-2">
        {skills.map((skill, idx) => (
          <Container key={idx} property="flex items-center gap-1">
            {editIndex === idx ? (
              <>
                <input
                  type="text"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  className="px-2 py-1 border rounded"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleEditSave(idx);
                    if (e.key === "Escape") handleEditCancel();
                  }}
                  autoFocus
                />
                <Button
                  icon="check"
                  variant="blueSmallNoHover"
                  onClick={() => handleEditSave(idx)}
                  property="ml-1"
                />
                <Button
                  icon="cross"
                  variant="red"
                  onClick={handleEditCancel}
                  property="ml-1"
                />
              </>
            ) : (
              <>
                <Button
                  pointer={false}
                  variant="blueSmallNoHover"
                  property="mr-1"
                >
                  {skill}
                </Button>
                <Button
                  icon="edit"
                  variant="blueSmallNoHover"
                  onClick={() => handleEdit(idx)}
                  property="ml-1"
                />
                <Button
                  icon="cross"
                  variant="red"
                  onClick={() => handleDelete(idx)}
                  property="ml-1"
                />
              </>
            )}
          </Container>
        ))}
      </Container>
    </Container>
  );
} 