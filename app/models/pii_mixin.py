"""Campo pessoal cifrado com leitura transparente (CP-01).

`campo_pii(...)` cria a propriedade pública (ex.: `cpf`) sobre três colunas:
- `<legado>`: coluna antiga em claro. Só é LIDA (registros anteriores ao backfill); toda gravação
  nova a deixa `NULL`. Some na migração `0003b`;
- `<cifrado>`: valor cifrado com MultiFernet (PII_FERNET_KEYS);
- `<bidx>` (opcional): índice cego HMAC para busca exata.

Gravar o valor normaliza (ex.: CPF só com dígitos), cifra, calcula o índice e limpa o legado.
"""
from app.utils.crypto import cifrar_pii, decifrar_pii, indice_cego


def campo_pii(legado: str, cifrado: str, bidx: str | None = None, dominio: str | None = None,
              normalizar=None):
    normalizar = normalizar or (lambda v: str(v).strip() if v else "")

    def ler(self):
        cifra = getattr(self, cifrado)
        if cifra:
            return decifrar_pii(cifra)
        return getattr(self, legado)

    def gravar(self, valor):
        normalizado = normalizar(valor) if valor else ""
        setattr(self, cifrado, cifrar_pii(normalizado) if normalizado else None)
        if bidx:
            setattr(self, bidx, indice_cego(dominio, normalizado) if normalizado else None)
        setattr(self, legado, None)

    return property(ler, gravar)


def preencher_pii_de_legado(obj, legado: str, cifrado: str, bidx: str | None = None,
                            dominio: str | None = None, normalizar=None) -> bool:
    """Backfill: cifra o valor legado SEM apagá-lo. Devolve True se algo mudou."""
    valor = getattr(obj, legado)
    if not valor or getattr(obj, cifrado):
        return False
    normalizado = normalizar(valor) if normalizar else str(valor).strip()
    if not normalizado:
        return False
    setattr(obj, cifrado, cifrar_pii(normalizado))
    if bidx:
        setattr(obj, bidx, indice_cego(dominio, normalizado))
    return True
