import SearchBar from "@components/Filter/SearchBar";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";

export default function FilterNabidka({ searchValue, onSearchChange, onSearchClear, onSearchSubmit }) {
    return (
        <Container property="w-full flex items-center inline-block justify-center mb-8">
            <SearchBar 
                value={searchValue}
                onChange={onSearchChange}
                onClear={onSearchClear}
            />
            <Button 
                onClick={onSearchSubmit} 
                noVariant={true} 
                property={"ml-2 bg-facultyColLight px-4 py-1 border border-black rounded-lg transition-colors duration-200 hover:bg-facultyCol"}
            >
                Hledat
            </Button>
        </Container>
    )
}
