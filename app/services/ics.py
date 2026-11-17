"""Geração de arquivos iCalendar (.ics) conforme a RFC 5545 (RF18, RN11).

Cuida do que os aplicativos de calendário exigem para aceitar o arquivo: quebras de linha CRLF,
linhas de no máximo 75 octetos, escape de vírgula/ponto e vírgula/barra/quebra de linha nos
textos, DTSTAMP e UID em todo evento e DTEND exclusivo nos eventos de dia inteiro.

Os horários são gravados como hora local "flutuante" (sem fuso): 08:00 aparece como 08:00 no
calendário de quem importa, que é o esperado para quem está no abrigo.
"""
from datetime import date, datetime, timedelta, timezone

PRODID = "-//GAPAR Gestao//Saude Animal//PT-BR"
UID_DOMAIN = "gapargestao.ong"


def escape_text(valor) -> str:
    """Escapa um valor do tipo TEXT (RFC 5545, seção 3.3.11)."""
    texto = "" if valor is None else str(valor)
    texto = texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return texto.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


def fold_line(linha: str) -> str:
    """Quebra a linha em trechos de até 75 octetos sem partir um caractere UTF-8 ao meio."""
    dados = linha.encode("utf-8")
    if len(dados) <= 75:
        return linha
    partes = []
    limite = 75
    while dados:
        corte = min(limite, len(dados))
        while corte < len(dados) and (dados[corte] & 0xC0) == 0x80:
            corte -= 1
        partes.append(dados[:corte].decode("utf-8"))
        dados = dados[corte:]
        limite = 74  # as linhas de continuação começam com um espaço
    return "\r\n ".join(partes)


def _alarm(descricao, trigger):
    return ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{escape_text(descricao)}", f"TRIGGER:{trigger}", "END:VALARM"]


def all_day_event(uid, resumo, descricao, dia: date, alarme="-PT15H"):
    """Evento de dia inteiro. O DTEND de dia inteiro é exclusivo, por isso é o dia seguinte.

    O alarme padrão dispara 15 horas antes da meia-noite, isto é, às 9h da véspera.
    """
    linhas = [
        "BEGIN:VEVENT",
        f"UID:{uid}@{UID_DOMAIN}",
        f"SUMMARY:{escape_text(resumo)}",
        f"DESCRIPTION:{escape_text(descricao)}",
        f"DTSTART;VALUE=DATE:{dia.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(dia + timedelta(days=1)).strftime('%Y%m%d')}",
        "TRANSP:TRANSPARENT",
    ]
    if alarme:
        linhas += _alarm(resumo, alarme)
    return linhas + ["END:VEVENT"]


def daily_event(uid, resumo, descricao, primeiro_dia: date, horario: str, dias: int, alarme="PT0M"):
    """Evento com hora marcada que se repete todo dia, `dias` vezes a partir de `primeiro_dia`."""
    hora, minuto = (int(parte) for parte in horario.split(":"))
    inicio = datetime(primeiro_dia.year, primeiro_dia.month, primeiro_dia.day, hora, minuto)
    linhas = [
        "BEGIN:VEVENT",
        f"UID:{uid}@{UID_DOMAIN}",
        f"SUMMARY:{escape_text(resumo)}",
        f"DESCRIPTION:{escape_text(descricao)}",
        f"DTSTART:{inicio.strftime('%Y%m%dT%H%M%S')}",
        "DURATION:PT15M",
    ]
    if dias > 1:
        linhas.append(f"RRULE:FREQ=DAILY;COUNT={dias}")
    if alarme:
        linhas += _alarm(resumo, alarme)
    return linhas + ["END:VEVENT"]


def build_calendar(nome, eventos, gerado_em: datetime | None = None) -> str:
    """Monta o arquivo completo. `eventos` é uma lista de listas de linhas (de `*_event`)."""
    carimbo = (gerado_em or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(nome)}",
    ]
    for evento in eventos:
        # DTSTAMP é obrigatório em todo VEVENT e vem logo depois do UID
        linhas += evento[:2] + [f"DTSTAMP:{carimbo}"] + evento[2:]
    linhas.append("END:VCALENDAR")
    return "\r\n".join(fold_line(linha) for linha in linhas) + "\r\n"
