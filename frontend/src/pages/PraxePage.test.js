import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PraxePage from "./PraxePage";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useUser } from "@hooks/UserProvider";
import { useMessage } from "@hooks/MessageContext";
import User from "@auth/UserObj";

jest.mock("src/api/nabidka/nabidkaAPI");
jest.mock("src/api/student_practice/student_practiceAPI");
jest.mock("@hooks/UserProvider");
jest.mock("@hooks/MessageContext");
jest.mock("@core/Button/BackButton", () => () => <button />);

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

const orgUser = () => {
  const user = new User();
  user.setUser({ role: "OWNER", user_id: 1, username: "org", email: "org@test.cz" });
  return user;
};

const studentUser = () => {
  const user = new User();
  user.setUser({ role: "ST", user_id: 2, username: "stud", email: "stud@ujep.cz" });
  return user;
};

const offer = (id, workflow_state) => ({
  practice_id: id,
  title: `Nabidka ${id}`,
  approval_status: 0,
  workflow_state,
  available_positions: 1,
});

beforeEach(() => {
  mockNavigate.mockClear();
  useMessage.mockReturnValue({ addMessage: jest.fn() });
  useStudentPracticeAPI.mockReturnValue({ manageEmployerInvitation: jest.fn() });
});

describe("PraxePage - tlačítko Upravit (F-6)", () => {
  // API vrací workflow_state jako číslo: 0 PENDING_CONTENT_APPROVAL, 2 CONTENT_REJECTED,
  // 3 OPEN_FOR_APPLICATIONS, 4 CLOSED_FOR_APPLICATIONS.
  test.each([
    [0, true],
    [2, true],
    ["PENDING_CONTENT_APPROVAL", true],
    ["CONTENT_REJECTED", true],
    [1, false],
    [3, false],
    [4, false],
  ])("workflow_state %p → editace povolena: %p", async (state, editable) => {
    useUser.mockReturnValue({ user: orgUser() });
    useNabidkaAPI.mockReturnValue({
      getOrganizationPractices: jest.fn().mockResolvedValue({ results: [offer(7, state)], count: 1 }),
    });

    render(
      <MemoryRouter>
        <PraxePage />
      </MemoryRouter>,
    );

    const editButton = await screen.findByLabelText("internships.edit_internship");
    const isDisabled = editButton.disabled === true || editButton.getAttribute("aria-disabled") === "true";
    expect(isDisabled).toBe(!editable);
  });
});

describe("PraxePage - karta přihlášky studenta (F-9)", () => {
  const renderStudent = async (studentPractices) => {
    useUser.mockReturnValue({ user: studentUser() });
    useNabidkaAPI.mockReturnValue({
      getPracticeUserRelations: jest.fn().mockResolvedValue({
        employer_invitations: [],
        student_practices: studentPractices,
      }),
    });
    render(
      <MemoryRouter>
        <PraxePage />
      </MemoryRouter>,
    );
  };

  test("s student_practice_id naviguje na /karta-praxe/<id>", async () => {
    await renderStudent([
      { practice_id: 28, student_practice_id: 21, practice_title: "Moje prihlaska", application_date: "2026-01-01" },
    ]);

    fireEvent.click(await screen.findByText("Moje prihlaska"));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/karta-praxe/21"));
  });

  test("bez student_practice_id naviguje na detail nabídky", async () => {
    await renderStudent([{ practice_id: 28, practice_title: "Bez SP", application_date: "2026-01-02" }]);

    fireEvent.click(await screen.findByText("Bez SP"));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/nabidka/28"));
  });
});
