import { renderHook } from "@testing-library/react";
import { useStudentPracticeAPI } from "./student_practiceAPI";

const mockApi = { get: jest.fn(), post: jest.fn() };
jest.mock("@hooks/useApi", () => ({ useApi: () => mockApi }));

describe("useStudentPracticeAPI workflow fail-closed", () => {
    beforeEach(() => jest.clearAllMocks());

    test.each(["UNRECOGNIZED", undefined])("normalizes unknown/missing detail state (%s)", async (status) => {
        mockApi.get.mockResolvedValue({ data: { student_practice_status: status === undefined ? {} : { workflow_status: status } } });
        const { result } = renderHook(() => useStudentPracticeAPI());
        const card = await result.current.getStudentPracticeCard(1);
        expect(card.student_practice_status.workflow_status).toBe("UNKNOWN");
    });

    test.each([undefined, "UNRECOGNIZED"])("does not mutate without known status (%s)", async (workflowStatus) => {
        const { result } = renderHook(() => useStudentPracticeAPI());
        await expect(result.current.updateStudentPracticeStatus(1, "approve", { workflowStatus })).rejects.toThrow(/Unknown or missing/);
        expect(mockApi.post).not.toHaveBeenCalled();
    });

    test("resubmit only from CONTENT_REJECTED targets AWAITING_CONTENT_APPROVAL", async () => {
        mockApi.post.mockResolvedValue({ data: { ok: true } });
        const { result } = renderHook(() => useStudentPracticeAPI());
        await result.current.updateStudentPracticeStatus(9, "resubmit", { workflowStatus: "CONTENT_REJECTED" });
        expect(mockApi.post).toHaveBeenCalledWith("/student-practices/9/transition/", { target_state: 10, reason: "" });
        mockApi.post.mockClear();
        await expect(result.current.updateStudentPracticeStatus(9, "resubmit", { workflowStatus: "APPLIED" })).rejects.toThrow(/only allowed from CONTENT_REJECTED/);
        expect(mockApi.post).not.toHaveBeenCalled();
    });

    test.each(["APPLIED", "PRELIMINARY_APPROVED"])("rejects %s to REJECTED", async (workflowStatus) => {
        mockApi.post.mockResolvedValue({ data: { ok: true } });
        const { result } = renderHook(() => useStudentPracticeAPI());
        await result.current.updateStudentPracticeStatus(4, "reject", { workflowStatus });
        expect(mockApi.post).toHaveBeenCalledWith("/student-practices/4/transition/", { target_state: 2, reason: "" });
    });

    test.each(["STARTED", "AWAITING_DOCUMENTS"])("does not reject from disallowed matrix state %s", async (workflowStatus) => {
        const { result } = renderHook(() => useStudentPracticeAPI());
        await expect(result.current.updateStudentPracticeStatus(4, "reject", { workflowStatus })).rejects.toThrow(/Rejection is not allowed/);
        expect(mockApi.post).not.toHaveBeenCalled();
    });

    test.each(["STARTED", "AWAITING_DOCUMENTS"])("recognizes backend workflow state %s", async (workflowStatus) => {
        mockApi.get.mockResolvedValue({ data: { student_practice_status: { workflow_status: workflowStatus } } });
        const { result } = renderHook(() => useStudentPracticeAPI());
        const card = await result.current.getStudentPracticeCard(1);
        expect(card.student_practice_status.workflow_status).toBe(workflowStatus);
    });
});
