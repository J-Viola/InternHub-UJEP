import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import PopUpCon from "./PopUpCon";

jest.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key) => key }) }));

test("dialog closes with Escape and restores focus to opener", () => {
  const Harness = () => {
    const [open, setOpen] = React.useState(false);
    return <>
      <button onClick={() => setOpen(true)}>Open dialog</button>
      {open && <PopUpCon title="Dialog title" onClose={() => setOpen(false)} onSubmit={jest.fn()} onReject={jest.fn()} />}
    </>;
  };
  render(<Harness />);
  const opener = screen.getByRole("button", { name: "Open dialog" });
  opener.focus();
  fireEvent.click(opener);
  expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
});
