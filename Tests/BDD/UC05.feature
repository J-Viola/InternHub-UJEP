# US-05 — Krizové ukončení praxe
# Acceptance Criteria:
#   AC-01: Formulář vyžaduje zadání důvodu ukončení.
#   AC-02: Po odeslání žádosti je praxe přepnuta do stavu Stornováno.
#   AC-03: Garant je okamžitě notifikován o podané žádosti.
#   AC-04: Student nemůže podat novou žádost o praxi, dokud není stornování vyřešeno.
#   AC-05: Systém zaznamenává datum a důvod ukončení do auditního logu.
Feature: Předčasné ukončení praxe
  Jako student
  Chci podat žádost o předčasné ukončení praxe
  Abych formálně zahájil proces stornování

  Background:
    Given jsem přihlášen jako student
    And mám aktivní praxi ve stavu "Zasmluvněno"

  # AC-02, AC-03, AC-05 | UAT: TC-05-01
  Scenario: Úspěšné podání žádosti o ukončení
    When otevřu detail praxe
    And kliknu na "Stornovat praxi"
    And vyplním pole "Důvod ukončení" hodnotou "Zdravotní důvody"
    And potvrdím odeslání
    Then praxe se přepne do stavu "Stornováno"
    And garant obdrží notifikaci
    And systém zaznamená datum a důvod do auditního logu

  # AC-01 | UAT: TC-05-02
  Scenario: Pokus odeslat žádost bez uvedení důvodu
    When kliknu na "Stornovat praxi"
    And nechám pole "Důvod ukončení" prázdné
    And kliknu na "Odeslat"
    Then systém zobrazí chybu "Důvod storno je povinný"

  # AC-04 | UAT: TC-05-03
  Scenario: Blokace nové žádosti během nevyřešeného stornování
    Given mám praxi ve stavu "Stornováno"
    When se pokusím podat novou žádost o praxi
    Then systém zobrazí chybu "Nelze podat novou žádost, dokud není storno vyřešeno"
