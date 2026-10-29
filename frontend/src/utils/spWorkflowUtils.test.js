import {
    isCancellationPending,
    canRequestCancellation,
    canResolveCancellation,
    canReviewResubmittedDocuments,
    canTerminalReject,
} from './spWorkflowUtils';

const makeUser = (roles) => ({
    isStudent: () => roles.includes('ST'),
    isDepartmentUser: () => roles.includes('VY') || roles.includes('VK'),
    isAdmin: () => roles.includes('admin'),
});

describe('spWorkflowUtils — A-12 storno studentem', () => {
    const cancelled = { is_cancelled: true, cancellation_requested_at: '2026-10-10T10:00:00Z', cancellation_resolved_at: null };

    test('storno studentem bez vzetí na vědomí je pending', () => {
        expect(isCancellationPending(cancelled)).toBe(true);
    });

    test('vzaté na vědomí, nestornované i storno bez žádosti (kaskáda) není pending', () => {
        expect(isCancellationPending({ ...cancelled, cancellation_resolved_at: '2026-10-11T10:00:00Z' })).toBe(false);
        expect(isCancellationPending({ is_cancelled: false, cancellation_requested_at: '2026-10-10T10:00:00Z' })).toBe(false);
        expect(isCancellationPending({ is_cancelled: true, cancellation_reason: 'x' })).toBe(false);
        expect(isCancellationPending(null)).toBe(false);
    });

    test('storno: jen student-vlastník ve stavu CONTRACTED a ne už stornované', () => {
        const student = makeUser(['ST']);
        const contracted = {
            student_practice_status: { workflow_status: 'CONTRACTED' },
        };
        expect(canRequestCancellation(contracted, student)).toBe(true);
        expect(
            canRequestCancellation(
                { ...contracted, is_cancelled: true },
                student
            )
        ).toBe(false);
        expect(
            canRequestCancellation({ student_practice_status: { workflow_status: 'APPLIED' } }, student)
        ).toBe(false);
        expect(canRequestCancellation(contracted, makeUser(['VY']))).toBe(false);
        expect(canRequestCancellation({}, student)).toBe(false);
    });

    test('storno bere na vědomí jen garant (VY/VK) nebo admin', () => {
        expect(canResolveCancellation(makeUser(['VY']))).toBe(true);
        expect(canResolveCancellation(makeUser(['VK']))).toBe(true);
        expect(canResolveCancellation(makeUser(['admin']))).toBe(true);
        expect(canResolveCancellation(makeUser(['ST']))).toBe(false);
        expect(canResolveCancellation(makeUser(['OWNER']))).toBe(false);
        expect(canResolveCancellation(null)).toBe(false);
    });
});

describe('spWorkflowUtils — C19-B/T2c repair loop role visibility', () => {
    test('review opravných dokumentů: VY/VK/admin', () => {
        expect(canReviewResubmittedDocuments(makeUser(['VY']))).toBe(true);
        expect(canReviewResubmittedDocuments(makeUser(['VK']))).toBe(true);
        expect(canReviewResubmittedDocuments(makeUser(['admin']))).toBe(true);
        expect(canReviewResubmittedDocuments(makeUser(['ST']))).toBe(false);
        expect(canReviewResubmittedDocuments(makeUser(['OWNER']))).toBe(false);
    });

    test('terminální REJECTED: pouze admin', () => {
        expect(canTerminalReject(makeUser(['admin']))).toBe(true);
        expect(canTerminalReject(makeUser(['VY']))).toBe(false);
        expect(canTerminalReject(makeUser(['VK']))).toBe(false);
        expect(canTerminalReject(makeUser(['ST']))).toBe(false);
    });
});
