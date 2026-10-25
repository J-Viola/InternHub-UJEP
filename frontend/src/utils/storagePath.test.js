import { storageUrlToApiPath } from "./storagePath";

describe("storageUrlToApiPath (A-24)", () => {
    test("převede absolutní i relativní storage URL na /files/", () => {
        expect(storageUrlToApiPath("http://localhost:8000/storage/storage/documents/cvs/a.pdf")).toBe("/files/storage/documents/cvs/a.pdf/");
        expect(storageUrlToApiPath("/storage/images/profiles/a.png")).toBe("/files/images/profiles/a.png/");
    });
    test("ostatní URL (data:, jiná cesta, prázdné) vrací null", () => {
        expect(storageUrlToApiPath("data:image/png;base64,AAA")).toBeNull();
        expect(storageUrlToApiPath("/jina/cesta.png")).toBeNull();
        expect(storageUrlToApiPath(null)).toBeNull();
    });
});
