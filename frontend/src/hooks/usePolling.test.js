import { act, renderHook } from "@testing-library/react";
import usePolling from "./usePolling";

describe("usePolling", () => {
  let visibilityState;

  beforeEach(() => {
    jest.useFakeTimers();
    visibilityState = "visible";
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => visibilityState,
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test("spouští callback v nastaveném intervalu a při unmountu interval uklidí", () => {
    const callback = jest.fn();
    const { unmount } = renderHook(() => usePolling(callback, 1_000));

    act(() => jest.advanceTimersByTime(999));
    expect(callback).not.toHaveBeenCalled();
    act(() => jest.advanceTimersByTime(1));
    expect(callback).toHaveBeenCalledTimes(1);

    unmount();
    act(() => jest.advanceTimersByTime(2_000));
    expect(callback).toHaveBeenCalledTimes(1);
  });

  test("pozastaví polling při hidden a pokračuje po návratu viditelnosti", () => {
    const callback = jest.fn();
    renderHook(() => usePolling(callback, 1_000));

    visibilityState = "hidden";
    act(() => jest.advanceTimersByTime(1_000));
    expect(callback).not.toHaveBeenCalled();

    visibilityState = "visible";
    act(() => jest.advanceTimersByTime(1_000));
    expect(callback).toHaveBeenCalledTimes(1);
  });

  test("nepřekrývá požadavky při pomalé odpovědi", async () => {
    let finishRequest;
    const callback = jest.fn(() => new Promise((resolve) => { finishRequest = resolve; }));
    renderHook(() => usePolling(callback, 1_000));

    act(() => jest.advanceTimersByTime(1_000));
    expect(callback).toHaveBeenCalledTimes(1);
    act(() => jest.advanceTimersByTime(3_000));
    expect(callback).toHaveBeenCalledTimes(1);

    await act(async () => finishRequest());
    act(() => jest.advanceTimersByTime(1_000));
    expect(callback).toHaveBeenCalledTimes(2);
  });
});
