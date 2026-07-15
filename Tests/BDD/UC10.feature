# US-10 — Hromadný export dat
# Acceptance Criteria:
#   AC-01: Export lze filtrovat podle akademického roku, stavu praxe a oboru.
#   AC-02: Systém generuje soubory ve formátech .xlsx a .csv.
#   AC-03: Export obsahuje všechna klíčová pole (student, organizace, termín, stav, garant).
#   AC-04: Velké exporty jsou zpracovány asynchronně a uživatel je notifikován po dokončení.
Feature: Hromadný export historických dat o praxích
  Jako garant předmětu
  Chci exportovat filtrovaná data do XLSX a CSV
  Abych je mohl použít pro reporty a archivaci

  Background:
    Given jsem přihlášen jako garant
    And v systému existují záznamy o praxích

  # AC-01, AC-02, AC-03 | UAT: TC-10-01
  Scenario: Export dat do formátu XLSX
    When nastavím filtr "akademický rok" na "2025/2026"
    And vyberu sloupce: student, organizace, termín, stav, garant
    And vyberu formát "XLSX"
    And kliknu na "Exportovat"
    Then systém vygeneruje soubor ve formátu .xlsx
    And soubor obsahuje vybrané sloupce: student, organizace, termín, stav, garant

  # AC-02 | UAT: TC-10-02
  Scenario: Export dat do formátu CSV
    When nastavím filtr "akademický rok" na "2025/2026"
    And vyberu sloupce: student, organizace, termín, stav, garant
    And vyberu formát "CSV"
    And kliknu na "Exportovat"
    Then systém vygeneruje soubor ve formátu .csv
    And soubor obsahuje vybrané sloupce: student, organizace, termín, stav, garant

  # AC-04 | UAT: TC-10-03
  Scenario: Asynchronní zpracování velkého exportu
    Given existuje více než 500 záznamů k exportu
    When zahájím export
    Then systém spustí zpracování na pozadí
    And zobrazí zprávu "Export se zpracovává. Budete notifikováni po dokončení."
    And po dokončení obdržím notifikaci s odkazem ke stažení
