import React from "react";
import { act, render, screen } from "@testing-library/react";
import Timeline from "./Timeline";
import { useApi } from "@hooks/useApi";

jest.mock("@hooks/useApi", () => ({ useApi: jest.fn() }));
jest.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

describe("Timeline refresh behavior", () => {
  test("keeps loaded history visible while refreshing the same practice", async () => {
    let resolveRefresh;
    const get = jest.fn()
      .mockResolvedValueOnce({ data: [{ action_description: "Původní událost", action_date: "2026-01-01", user_name: "Student" }] })
      .mockImplementationOnce(() => new Promise((resolve) => { resolveRefresh = resolve; }));
    useApi.mockReturnValue({ get });
    const { rerender } = render(<Timeline studentPracticeId="5" currentStatus="APPLIED" refreshKey={0} />);
    expect(await screen.findByText("Původní událost")).toBeInTheDocument();

    rerender(<Timeline studentPracticeId="5" currentStatus="APPLIED" refreshKey={1} />);
    expect(screen.getByText("Původní událost")).toBeInTheDocument();
    expect(screen.queryByText("practice_detail.timeline_loading")).not.toBeInTheDocument();
    await act(async () => {
      resolveRefresh({ data: [{ action_description: "Aktualizovaná událost", action_date: "2026-01-02", user_name: "Student" }] });
    });
    expect(screen.getByText("Aktualizovaná událost")).toBeInTheDocument();
    expect(screen.queryByText("Původní událost")).not.toBeInTheDocument();
  });
});
