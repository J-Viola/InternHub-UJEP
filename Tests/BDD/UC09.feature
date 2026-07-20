# US-09 — Monitorování rizik — Dashboard
# Acceptance Criteria:
#   AC-01: Dashboard zobrazuje počty praxí v každém stavu životního cyklu.
#   AC-02: Zvýrazněny jsou praxe po termínu nebo bez nahraných dokumentů.
#   AC-03: Garant může z dashboardu přejít přímo na detail problematické praxe.
#   AC-04: Data jsou aktualizována v reálném čase (nebo s definovanou latencí).
Feature: Monitorovací dashboard garantu
  Jako garant předmětu
  Chci sledovat kritické stavy a prodlení na dashboardu
  Abych mohl proaktivně řešit rizika

  Background:
    Given jsem přihlášen jako garant

  # AC-01, AC-04 | UAT: TC-09-01
  Scenario: Zobrazení přehledu stavů praxí
    When otevřu dashboard
    Then vidím počty praxí v každém stavu životního cyklu
    And data jsou aktuální

  # AC-02 | UAT: TC-09-02
  Scenario: Zvýraznění praxí po termínu
    Given existuje praxe s chybějícím dokumentem po termínu odevzdání
    When otevřu dashboard
    Then tato praxe je vizuálně zvýrazněna jako riziková

  # AC-03 | UAT: TC-09-03
  Scenario: Přechod na detail problematické praxe
    When kliknu na rizikovou praxi v dashboardu
    Then přejdu přímo na detail dané praxe
