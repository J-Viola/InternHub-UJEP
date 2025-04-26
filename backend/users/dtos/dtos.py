from datetime import date
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, constr


class Adresa(BaseModel):
    """Adresa - obecný předek"""

    kodStatu: Optional[str] = Field(
        None, description="Kód státu (ciselnikKod: Stat)"
    )
    nazevStatu: Optional[str] = Field(
        None, description="Název státu"
    )
    kodKraje: Optional[int] = Field(
        None, description="Kód kraje"
    )
    nazevKraje: Optional[str] = Field(
        None, description="Název kraje"
    )
    kodOkresu: Optional[int] = Field(
        None, description="Kód okresu"
    )
    nazevOkresu: Optional[str] = Field(
        None, description="Název okresu"
    )
    kodObce: Optional[int] = Field(
        None, description="Kód obce"
    )
    nazevObce: Optional[str] = Field(
        None, description="Název obce"
    )
    kodCastiObce: Optional[int] = Field(
        None, description="Kód části obce"
    )
    nazevCastiObce: Optional[str] = Field(
        None, description="Název části obce"
    )
    kodMestskeCastiObvodu: Optional[int] = Field(
        None, description="Kód městské části/obvodu"
    )
    nazevMestskeCastiObvodu: Optional[str] = Field(
        None, description="Název městské části/obvodu"
    )
    kodUlice: Optional[int] = Field(
        None, description="Kód ulice"
    )
    nazevUlice: Optional[str] = Field(
        None, description="Název ulice"
    )
    cisloDomovni: Optional[int] = Field(
        None, description="Číslo domovní"
    )
    cisloOrientacni: Optional[int] = Field(
        None, description="Číslo orientační"
    )
    cisloOrientacniPismeno: Optional[str] = Field(
        None, description="Písmeno čísla orientačního"
    )
    kodAdresnihoMista: Optional[int] = Field(
        None, description="Kód adresního místa"
    )
    psc: Optional[str] = Field(
        None, description="PSČ"
    )
    textAdresy: Optional[str] = Field(
        None, description="Textová podoba adresy"
    )

class AdresaDorucovaci(BaseModel):
    """Adresa doručovací dle vyhlášky 359/2011 sb."""

    radekAdresy1: Optional[str] = Field(
        None, description="řádek doručovací adresy"
    )
    radekAdresy2: Optional[str] = Field(
        None, description="řádek doručovací adresy"
    )
    radekAdresy3: Optional[str] = Field(
        None, description="řádek doručovací adresy"
    )

class EkonomickySubjektDTO(BaseModel):
    description: Optional[str] = None
    ico: Optional[str] = None
    obchodniJmeno: Optional[str] = None
    sidlo: Optional[Adresa] = None
    pravniForma: Optional[str] = None
    financniUrad: Optional[str] = None
    datumVzniku: Optional[date] = None
    datumZaniku: Optional[date] = None
    datumAktualizace: Optional[date] = None
    dic: Optional[str] = None
    icoId: Optional[str] = None
    adresaDorucovaci: Optional[AdresaDorucovaci] = None
    seznamRegistraci: Optional[Dict] = None
    primarniZdroj: Optional[str] = None
    dalsiUdaje: Optional[List[Dict]] = None
    czNace: Optional[List[Dict]] = None
    subRegistrSzr: Optional[str] = None
    dicSkDph: Optional[str] = None

    class Config:
        # Allow extra attributes from the API response
        extra = "allow"