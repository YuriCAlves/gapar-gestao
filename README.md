# GAPAR Gestão — Back-End (MVP)

> Plataforma de Controle de Abrigo e Saúde Animal — **ONG GAPAR**  
> Especificação: Padrão ISO/IEC/IEEE 29148:2018 (Versão 4.0 Consolidada)

---

## 📌 Visão Geral da Arquitetura Back-End

Este repositório contém o desenvolvimento exclusivo do **back-end** do sistema GAPAR Gestão, estruturado de forma modular com **Python 3.12**, **Flask (Blueprints)** e **SQLAlchemy**.

### 🧩 Estrutura de Blueprints

- `auth` (`/auth`): Autenticação Google OAuth 2.0 (RF01), validação de Whitelist (RF02) e controle de sessão.
- `core` (`/` e `/api/hoje`): Painel operacional diário 'Hoje' (RF23) com consolidação de medicações e vacinas do dia.
- `animals` (`/api/animais`): Cadastro e consulta de cães, máquina de status operacional, busca com filtros e upload de fotos com compressão (< 300 KB).
- `health` (`/api/saude`): Cartão de vacinação digital (RF13), prontuário médico (RF14), prescrições e baixa diária de doses (RF16).
- `adoptions` (`/api/adocoes`): Registro formal obrigatório de adoção (RF20) e congelamento histórico do cão (RF21).
- `admin` (`/api/admin`): Gestão de e-mails autorizados na Whitelist (RF04), Lista Sigilosa de Não Aptos (RF22) e Trilha Inviolável de Auditoria (RF24).

---

## 🛠️ Instalação e Execução Local

### 1. Pré-requisitos
- Python 3.12+
- Git

### 2. Configurar o Ambiente Virtual
```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Ativar ambiente virtual (Linux / macOS)
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

### 4. Executar a Aplicação
```bash
python run.py
```
A API estará disponível em: `http://127.0.0.1:5000`

---

## 🔒 Regras de Negócio Críticas (RN)
- **RN01:** Todo cão recém-cadastrado entra obrigatoriamente com o status `em acolhimento` e data do dia.
- **RN03:** É proibida a exclusão física de registros de animais, prontuários ou vacinas.
- **RN04:** Adoções exigem obrigatoriamente nome, telefone e data do adotante.
- **RN05:** Animais nos status `adotado` ou `óbito` têm seus prontuários e cadastros congelados para edições.
- **RN12/RN14:** Acesso fechado restrito a e-mails na Whitelist; desativação tem efeito imediato na próxima requisição.
- **RN15:** Lista de pessoas não aptas a adotar é sigilosa e restrita exclusivamente à Administradora.
