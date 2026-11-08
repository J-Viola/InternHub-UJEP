import React from 'react';
import { render, screen } from '@testing-library/react';
import StateBadge, { getStateLabel, getStateVariant } from './StateBadge';


describe('StateBadge — mapování stavů (BL-04)', () => {
    test('DOCUMENTS_RESUBMITTED (13 i string) má vlastní label klíč', () => {
        expect(getStateLabel(13)).toBe("Opravené dokumenty čekají na kontrolu");
        expect(getStateLabel('DOCUMENTS_RESUBMITTED')).toBe("Opravené dokumenty čekají na kontrolu");
    });

    test('DOCUMENTS_RESUBMITTED se zobrazuje jako varování (review pending)', () => {
        expect(getStateVariant('DOCUMENTS_RESUBMITTED')).toBe('yellow');
        expect(getStateVariant(13)).toBe('yellow');
    });

    test('ostatní opravné stavy zůstávají beze změny', () => {
        expect(getStateLabel(9)).toBe("Dokumenty zamítnuty");
        expect(getStateVariant(9)).toBe('red');
        expect(getStateLabel('DOCUMENTS_REJECTED')).toBe("Dokumenty zamítnuty");
        expect(getStateLabel('AWAITING_CONTENT_APPROVAL')).toBe("Čeká na schválení obsahu");
        expect(getStateLabel('CANCELLED')).toBe("Stornováno");
    });

    test('neznámý stav padá na UNKNOWN klíč', () => {
        expect(getStateLabel(undefined)).toBe("Neznámý");
        expect(getStateLabel(null)).toBe("Neznámý");
    });

    test('komponenta vyrenderuje label klíče nového stavu', () => {
        render(<StateBadge status="DOCUMENTS_RESUBMITTED" />);
        expect(screen.getByText("Opravené dokumenty čekají na kontrolu")).toBeInTheDocument();
    });
});

describe("practiceStateName (F-1)", () => {
  const { practiceStateName } = require("./StateBadge");
  test("číselné stavy nabídky se překládají na názvy", () => {
    expect(practiceStateName(0)).toBe("PENDING_CONTENT_APPROVAL");
    expect(practiceStateName(3)).toBe("OPEN_FOR_APPLICATIONS");
    expect(practiceStateName(4)).toBe("CLOSED_FOR_APPLICATIONS");
  });
  test("řetězce a neznámé hodnoty projdou beze změny", () => {
    expect(practiceStateName("CONTENT_REJECTED")).toBe("CONTENT_REJECTED");
    expect(practiceStateName(undefined)).toBeUndefined();
  });
});
