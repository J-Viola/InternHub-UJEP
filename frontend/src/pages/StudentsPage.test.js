import React from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import StudentPage from "./StudentsPage";
import { useUserAPI } from "@api/user/userAPI";
import { useUser } from "@hooks/UserProvider";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useMessage } from "@hooks/MessageContext";
import User from "@auth/UserObj";

jest.mock("@api/user/userAPI");
jest.mock("@hooks/UserProvider");
jest.mock("@api/department/departmentAPI");
jest.mock("@api/student_practice/student_practiceAPI");
jest.mock("@api/nabidka/nabidkaAPI");
jest.mock("@hooks/MessageContext");
jest.mock("@components/User/UserEntity", () => () => <div />);
jest.mock("@components/Filter/SearchBar", () => () => <div />);
jest.mock("@core/Button/BackButton", () => () => <button />);

test("organization paged students request does not repeat on rerender", async () => {
  const user = new User();
  user.setUser({ role: "OWNER", user_id: 1, username: "org", email: "org@test.cz" });
  const getAllStudents = jest.fn().mockResolvedValue({ results: [], count: 0 });
  useUser.mockReturnValue({ user });
  useUserAPI.mockReturnValue({ getAllStudents });
  useDepartmentAPI.mockReturnValue({ getDepartmentStudents: jest.fn() });
  useStudentPracticeAPI.mockReturnValue({ getStudentsByPracticeId: jest.fn(), createInvitation: jest.fn() });
  useNabidkaAPI.mockReturnValue({ getNabidkaById: jest.fn(), getOrganizationPractices: jest.fn() });
  useMessage.mockReturnValue({ addMessage: jest.fn() });
  const { rerender } = render(<MemoryRouter><StudentPage /></MemoryRouter>);
  await waitFor(() => expect(getAllStudents).toHaveBeenCalledTimes(1));
  rerender(<MemoryRouter><StudentPage /></MemoryRouter>);
  expect(getAllStudents).toHaveBeenCalledTimes(1);
});
