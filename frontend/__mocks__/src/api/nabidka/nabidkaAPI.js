const useNabidkaAPI = () => ({
  calculateEndDate: jest.fn(() => Promise.resolve('31.12.2025')),
});

export { useNabidkaAPI };
