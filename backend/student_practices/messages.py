from django.utils.translation import gettext_lazy as _


class StudentPracticeMessages:
    # Errors
    NOT_FOUND = _("Přihláška na praxi nebyla nalezena.")
    UNAUTHORIZED = _("Nemáte oprávnění spravovat tuto přihlášku.")
    PRACTICE_NOT_FOUND = _("Praxe nenalezena.")
    INVITATION_NOT_FOUND = _("Pozvánka nebyla nalezena nebo k ní nemáte přístup.")
    INVITATION_PROCESSED = _("Pozvánka již byla zpracována.")
    INVALID_ACTION = _("Neplatná akce.")
    INVALID_APPROVAL_VALUE = _("Neplatná hodnota pro stav schválení.")
    INVALID_PROGRESS_VALUE = _("Neplatná hodnota pro stav průběhu.")
    CANNOT_REJECT = _("Nemáte oprávnění zamítnout tuto přihlášku.")
    PROGRESS_UPDATE_FORBIDDEN = _("Nelze měnit stav průběhu u neschválené praxe.")
    FILE_TOO_LARGE = _("Soubor je příliš velký. Maximální povolená velikost je {size} MB.")
    INVALID_EXTENSION = _("Jenom Word (.doc, .docx) dokumenty jsou povoleny.")
    INTERNAL_ERROR = _("Došlo k vnitřní chybě při schvalování.")

    # Success
    INVITATION_ACCEPTED = _("Pozvánka byla přijata a praxe byla zahájena.")
    INVITATION_REJECTED = _("Pozvánka byla zamítnuta.")
