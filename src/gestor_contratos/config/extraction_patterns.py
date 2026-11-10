"""Configurable labels and regular expressions for SIGA documents."""

ORDER_DATE = (
    r"(?im)^\s*1\.\s*FECHA\s+DE\s+LA\s+ORDEN\s*:?[ \t]*"
    r"(?P<value>\d{1,2}[\s\-/]+\d{1,2}[\s\-/]+\d{4}|"
    r"\d{1,2}\s*\n\s*\d{1,2}\s*\n\s*\d{4})"
)

ORDER_NUMBER = (
    r"(?im)^\s*2\.\s*CONSECUTIVO\s+DE\s+LA\s+ORDEN\s*"
    r"(?:\n\s*)?Orden\s+de\s+Trabajo\s*\n\s*(?P<value>\d+)"
)

ORDER_TYPE = r"(?im)^\s*(?P<value>Orden\s+de\s+Trabajo|Petici[oó]n\s+de\s+Servicio)\s*$"
OBJECT = r"(?im)^\s*3\.1\.\s*Objeto\s+del\s+trabajo/servicio\s*:\s*(?P<value>.+)$"
LOCATION = r"(?im)^\s*3\.2\.\s*Edificio\s*[–-]\s*Sede[ \t]*:[ \t]*(?P<value>.+)$"
START_DATE = r"(?im)^\s*3\.3\.\s*Fecha\s+de\s+Inicio\s*:\s*(?P<value>.+)$"
END_DATE = (
    r"(?im)^\s*3\.4\.\s*Fecha\s+de\s+Entrega\s*/?\s*"
    r"Fecha\s+de\s+Vencimiento\s*:\s*(?P<value>.+)$"
)

PROVIDER_NAME = (
    r"(?im)^\s*(?:4\.1\.\s*Nombre|2\.1\.\s*Nombre\s+o\s+raz[oó]n\s+social)"
    r"\s*:\s*(?P<value>.+)$"
)
PROVIDER_NIT = r"(?im)^\s*(?:4\.2\.|2\.2\.)\s*N[ií]t\s*:\s*(?P<value>[\d.\- ]+)"
PROVIDER_ADDRESS = (
    r"(?ims)^\s*4\.3\.\s*Direcci[oó]n[ \t]*:[ \t]*(?P<value>.+?)"
    r"(?=\n\s*4\.4\.)"
)
CONTACT = r"(?im)^\s*4\.4\.\s*Persona\s+contacto\s*:\s*(?P<value>.+)$"
CITY = r"(?im)^\s*4\.5\.\s*Ciudad\s*:\s*(?P<value>.+)$"
PHONE = (
    r"(?im)^[ \t]*4\.6\.\s*Tel[eé]fono[ \t]*:[ \t]*"
    r"(?P<value>[^\r\n]+)[ \t]*$"
)
MOBILE = r"(?im)^\s*4\.7\.\s*Celular[ \t]*:[ \t]*(?P<value>.*)$"
EMAIL = r"(?im)^\s*4\.8\.\s*Correo\s+electr[oó]nico\s*:\s*(?P<value>.+)$"

ACTA_ORDER_NUMBER = (
    r"(?im)^\s*2\.5\.\s*Orden\s+de\s+Trabajo\s*N[°º]?\s*:\s*"
    r"(?P<value>\d+)"
)
ACTA_ORDER_DATE = (
    r"(?im)^\s*2\.6\.\s*Fecha\s+de\s+la\s+Orden\s+de\s+Trabajo\s*:?[ \t]*"
    r"(?P<value>\d{1,2}[\-/]\d{1,2}[\-/]\d{4})"
)
ACTA_DELIVERY_DATE = (
    r"(?im)^\s*2\.7\.\s*Fecha\s+de\s+entrega\s+de\s+la\s+obra\s+"
    r"seg[uú]n\s+Orden\s+de\s+Trabajo\s*:\s*(?P<value>\d{1,2}[\-/]\d{1,2}[\-/]\d{4})"
)

TOTAL_LETTERS = (
    r"(?is)Valor\s+Total\s+en\s+Letras\s*:\s*(?P<value>.+?)"
    r"(?=TOTAL\s+\d|\*Los\s+precios)"
)
TOTAL = r"(?im)^\s*TOTAL\s+(?P<value>[\d.,]+)\s*$"
