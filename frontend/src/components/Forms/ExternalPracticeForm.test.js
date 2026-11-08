import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import ExternalPracticeForm from "./ExternalPracticeForm";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";

jest.mock("@api/ARES/aresJusticeAPI");
jest.mock("@hooks/useApi", () => ({ useApi: () => ({}) }));
jest.mock("@hooks/useDebounce", () => (value) => value);
jest.mock("@core/Form/TextField", () => ({ id, value, onChange, label }) => <input aria-label={id} value={value || ""} onChange={(e) => onChange({ [id]: e.target.value })} />);
jest.mock("@core/Form/DropDown", () => () => null);
jest.mock("@core/Form/TextBox", () => () => null);
jest.mock("@core/Form/DatePicker", () => () => null);
jest.mock("@core/Container/Container", () => ({ children }) => <div>{children}</div>);
jest.mock("@core/Text/Headings", () => ({ children }) => <h2>{children}</h2>);
jest.mock("@components/core/Text/Paragraph", () => ({ children, ...props }) => <p {...props}>{children}</p>);

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};

describe("ExternalPracticeForm file and ARES race guards", () => {
  const lookup = jest.fn();
  const baseProps = { formData: {}, handleChange: jest.fn(), handleSubmit: jest.fn(), subjects: [] };
  beforeEach(() => { jest.clearAllMocks(); useAresAPI.mockReturnValue({ getEntityByICO: lookup }); });

  test("valid file A then invalid B clears A and blocks submit", () => {
    const fileA = new File(["valid"], "details.pdf", { type: "application/pdf" });
    const handleChange = jest.fn();
    const handleSubmit = jest.fn();
    const { rerender } = render(<ExternalPracticeForm {...baseProps} formData={{ external_details_file: fileA }} handleChange={handleChange} handleSubmit={handleSubmit} />);
    const fileInput = screen.getByLabelText(/Dokument s detaily praxe/);
    const invalidFile = new File(["bad"], "details.exe", { type: "application/octet-stream" });
    fireEvent.change(fileInput, { target: { files: [invalidFile] } });
    expect(handleChange).toHaveBeenCalledWith({ external_details_file: null });
    rerender(<ExternalPracticeForm {...baseProps} formData={{ external_details_file: null }} handleChange={handleChange} handleSubmit={handleSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Vytvořit praxi" }));
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  test("oversized replacement clears the previously selected file", () => {
    const handleChange = jest.fn();
    const priorFile = new File(["ok"], "prior.pdf", { type: "application/pdf" });
    render(<ExternalPracticeForm {...baseProps} formData={{ external_details_file: priorFile }} handleChange={handleChange} />);
    const input = screen.getByLabelText(/Dokument s detaily praxe/);
    const huge = new File(["x"], "huge.pdf", { type: "application/pdf" });
    Object.defineProperty(huge, "size", { value: 11 * 1024 * 1024 });
    fireEvent.change(input, { target: { files: [huge] } });
    expect(handleChange).toHaveBeenCalledWith({ external_details_file: null });
  });

  test("slow old ICO response cannot overwrite newer response", async () => {
    const first = deferred();
    const second = deferred();
    lookup.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const handleChange = jest.fn();
    const { rerender } = render(<ExternalPracticeForm {...baseProps} formData={{ ico: "11111111" }} handleChange={handleChange} />);
    rerender(<ExternalPracticeForm {...baseProps} formData={{ ico: "22222222" }} handleChange={handleChange} />);
    second.resolve({ obchodniJmeno: "Novější firma", sidlo: { textovaAdresa: "Nová adresa" } });
    await waitFor(() => expect(handleChange).toHaveBeenCalledWith(expect.objectContaining({ employer_name: "Novější firma" })));
    first.resolve({ obchodniJmeno: "Stará firma", sidlo: { textovaAdresa: "Stará adresa" } });
    await Promise.resolve();
    expect(handleChange).not.toHaveBeenCalledWith(expect.objectContaining({ employer_name: "Stará firma" }));
  });

  test.each([404, 503])("ARES %s clears any previous prefills", async (status) => {
    lookup.mockRejectedValue({ response: { status } });
    const handleChange = jest.fn();
    render(<ExternalPracticeForm {...baseProps} formData={{ ico: "12345678", employer_name: "Stará firma", address: "Stará adresa" }} handleChange={handleChange} />);
    await waitFor(() => expect(handleChange).toHaveBeenCalledWith({ employer_name: "", address: "", ares_locked: false }));
  });
});
