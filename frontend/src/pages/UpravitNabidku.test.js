import React from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import UpravitNabidku from "./UpravitNabidku";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useCodeListAPI } from "src/api/code_list/code_listAPI";
import { useUserAPI } from "src/api/user/userAPI";
import { useUser } from "@hooks/UserProvider";
import { useMessage } from "@hooks/MessageContext";
import User from "@auth/UserObj";

jest.mock("src/api/nabidka/nabidkaAPI");
jest.mock("src/api/code_list/code_listAPI");
jest.mock("src/api/user/userAPI");
jest.mock("@hooks/UserProvider");
jest.mock("@hooks/MessageContext");
jest.mock("@core/Button/BackButton", () => () => <button />);
jest.mock("@components/Forms/NabidkaForm", () => () => <div data-testid="nabidka-form" />);

test("editace načítá nabídku přes employer endpoint, ne přes katalogový (F-8)", async () => {
  const getEmployerNabidkaById = jest.fn().mockResolvedValue({
    practice_id: 28,
    title: "Nabidka",
    subject: { subject_id: 4 },
    contact_user: 26,
  });
  const getNabidkaById = jest.fn();

  useNabidkaAPI.mockReturnValue({ getEmployerNabidkaById, getNabidkaById, updateNabidka: jest.fn(), calculateEndDate: jest.fn() });
  useCodeListAPI.mockReturnValue({ getUniqueSubjects: jest.fn().mockResolvedValue([]) });
  useUserAPI.mockReturnValue({ getOrganizationUsers: jest.fn().mockResolvedValue([]) });
  const user = new User();
  user.setUser({ role: "OWNER", user_id: 26, username: "org", email: "org@test.cz" });
  useUser.mockReturnValue({ user });
  useMessage.mockReturnValue({ addMessage: jest.fn() });

  render(
    <MemoryRouter initialEntries={["/upravit-nabidku/28"]}>
      <Routes>
        <Route path="/upravit-nabidku/:id" element={<UpravitNabidku />} />
      </Routes>
    </MemoryRouter>,
  );

  await waitFor(() => expect(getEmployerNabidkaById).toHaveBeenCalledWith("28"));
  expect(getNabidkaById).not.toHaveBeenCalled();
});
