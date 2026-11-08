import React from "react";
import { render, screen } from "@testing-library/react";
import PraxeDepartmentEntity from "./PraxeDepartmentEntity";

jest.mock("@core/Container/ContainerForEntity", () => ({ children }) => <div>{children}</div>);
jest.mock("@core/Container/Container", () => ({ children }) => <div>{children}</div>);
jest.mock("@components/core/Text/Paragraph", () => ({ children }) => <p>{children}</p>);
jest.mock("@core/Button/Button", () => () => <button />);

test("preserves numeric zero workflow label instead of treating it as missing", () => {
  render(<PraxeDepartmentEntity type="approved" entity={{ practice_id: 1, workflow_status_label: 0 }} onClick={() => {}} onView={() => {}} />);
  expect(screen.getByText("0")).toBeInTheDocument();
});
