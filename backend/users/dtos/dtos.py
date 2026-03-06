from datetime import date

from pydantic import BaseModel, Field


class Adresa(BaseModel):
    """Adresa - obecný předek"""

    kodStatu: str | None = Field(None, description="Kód státu (ciselnikKod: Stat)")
    nazevStatu: str | None = Field(None, description="Název státu")
    kodKraje: int | None = Field(None, description="Kód kraje")
    nazevKraje: str | None = Field(None, description="Název kraje")
    kodOkresu: int | None = Field(None, description="Kód okresu")
    nazevOkresu: str | None = Field(None, description="Název okresu")
    kodObce: int | None = Field(None, description="Kód obce")
    nazevObce: str | None = Field(None, description="Název obce")
    kodCastiObce: int | None = Field(None, description="Kód části obce")
    nazevCastiObce: str | None = Field(None, description="Název části obce")
    kodMestskeCastiObvodu: int | None = Field(None, description="Kód městské části/obvodu")
    nazevMestskeCastiObvodu: str | None = Field(None, description="Název městské části/obvodu")
    kodUlice: int | None = Field(None, description="Kód ulice")
    nazevUlice: str | None = Field(None, description="Název ulice")
    cisloDomovni: int | None = Field(None, description="Číslo domovní")
    cisloOrientacni: int | None = Field(None, description="Číslo orientační")
    cisloOrientacniPismeno: str | None = Field(None, description="Písmeno čísla orientačního")
    kodAdresnihoMista: int | None = Field(None, description="Kód adresního místa")
    psc: int | None = Field(None, description="PSČ")
    textovaAdresa: str | None = Field(None, description="Textová podoba adresy")


class AdresaDorucovaci(BaseModel):
    """Adresa doručovací dle vyhlášky 359/2011 sb."""

    radekAdresy1: str | None = Field(None, description="řádek doručovací adresy")
    radekAdresy2: str | None = Field(None, description="řádek doručovací adresy")
    radekAdresy3: str | None = Field(None, description="řádek doručovací adresy")


class EkonomickySubjektDTO(BaseModel):
    description: str | None = None
    ico: int | None = None
    obchodniJmeno: str | None = None
    sidlo: Adresa | None = None
    pravniForma: str | None = None
    financniUrad: str | None = None
    datumVzniku: date | None = None
    datumZaniku: date | None = None
    datumAktualizace: date | None = None
    dic: str | None = None
    icoId: str | None = None
    adresaDorucovaci: AdresaDorucovaci | None = None
    seznamRegistraci: dict | None = None
    primarniZdroj: str | None = None
    dalsiUdaje: list[dict] | None = None
    subRegistrSzr: str | None = None
    dicSkDph: str | None = None

    class Config:
        # Allow extra attributes from the API response
        extra = "allow"
