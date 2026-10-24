import React from 'react';
import { render, screen } from '@testing-library/react';
import StateBadge, { getStateLabelKey, getStateVariant } from './StateBadge';

jest.mock('react-i18next', () => ({
    useTranslation: () => ({ t: (key) => key }),
}));

describe('StateBadge — mapování stavů (BL-04)', () => {
    test('DOCUMENTS_RESUBMITTED (13 i string) má vlastní label klíč', () => {
        expect(getStateLabelKey(13)).toBe('state_badge.DOCUMENTS_RESUBMITTED');
        expect(getStateLabelKey('DOCUMENTS_RESUBMITTED')).toBe('state_badge.DOCUMENTS_RESUBMITTED');
    });

    test('DOCUMENTS_RESUBMITTED se zobrazuje jako varování (review pending)', () => {
        expect(getStateVariant('DOCUMENTS_RESUBMITTED')).toBe('yellow');
        expect(getStateVariant(13)).toBe('yellow');
    });

    test('ostatní opravné stavy zůstávají beze změny', () => {
        expect(getStateLabelKey(9)).toBe('state_badge.DOCUMENTS_REJECTED');
        expect(getStateVariant(9)).toBe('red');
        expect(getStateLabelKey('DOCUMENTS_REJECTED')).toBe('state_badge.DOCUMENTS_REJECTED');
        expect(getStateLabelKey('AWAITING_CONTENT_APPROVAL')).toBe('state_badge.AWAITING_CONTENT_APPROVAL');
        expect(getStateLabelKey('CANCELLED')).toBe('state_badge.CANCELLED');
    });

    test('neznámý stav padá na UNKNOWN klíč', () => {
        expect(getStateLabelKey(undefined)).toBe('state_badge.UNKNOWN');
        expect(getStateLabelKey(null)).toBe('state_badge.UNKNOWN');
    });

    test('komponenta vyrenderuje label klíče nového stavu', () => {
        render(<StateBadge status="DOCUMENTS_RESUBMITTED" />);
        expect(screen.getByText('state_badge.DOCUMENTS_RESUBMITTED')).toBeInTheDocument();
    });
});
