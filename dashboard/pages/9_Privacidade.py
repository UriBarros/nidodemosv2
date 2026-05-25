"""Política de Privacidade — pública, sem auth."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from dashboard.theme import apply_theme  # noqa: E402

st.set_page_config(page_title="Privacidade | gtrifood", page_icon="🔒", layout="centered")
apply_theme()

st.title("Política de Privacidade")
st.caption("Última atualização: 24 de maio de 2026")

st.markdown(
    """
Esta Política de Privacidade descreve como a **ACELERADORA GTR PARA RESTAURANTES
GESTAO E CONSULTORIA DE DELIVERY LTDA** (CNPJ a confirmar), operadora da plataforma
**gtrifood** (`gtrifood.aceleradoragtr.cloud`), coleta, usa e protege dados pessoais
em conformidade com a **Lei Geral de Proteção de Dados (LGPD — Lei 13.709/2018)**.

## 1. Controlador dos Dados

- **Razão social:** ACELERADORA GTR PARA RESTAURANTES GESTAO E CONSULTORIA DE
  DELIVERY LTDA
- **Encarregado (DPO):** Robson Queiroz Rabelo
- **Contato:** privacidade@aceleradoragtr.com.br

## 2. Quais dados coletamos

### 2.1. Do usuário do gtrifood (operador da loja)
- Nome completo e e-mail (cadastro)
- Senha criptografada (Supabase Auth)
- Endereço IP e dados de navegação (logs do servidor)
- Histórico de uso da plataforma

### 2.2. Da loja iFood vinculada
- Identificadores do estabelecimento (UUID, nome, CNPJ, endereço)
- Pedidos: número, status, valor, itens, forma de pagamento
- Dados financeiros: vendas, antecipações, ocorrências
- Avaliações de clientes finais (reviews)

### 2.3. De clientes finais dos pedidos (titulares indiretos)
Quando uma loja cliente nossa recebe um pedido, recebemos via API iFood:
- Nome do cliente final
- Telefone (geralmente número intermediado pelo iFood)
- Endereço de entrega
- Histórico do pedido

Esses dados pertencem ao **cliente final do iFood** — nós os processamos como
**operador** em nome da loja (controladora).

## 3. Finalidade

- Permitir que lojas clientes visualizem e analisem dados de operação iFood
- Gerar relatórios e dashboards
- Notificar eventos de pedido (recebido, despachado, concluído, cancelado)
- Cumprir obrigações legais e regulatórias

## 4. Base legal

- **Execução de contrato** (Art. 7º, V LGPD) — pra prestar o serviço contratado
- **Legítimo interesse** (Art. 7º, IX) — pra logs de segurança e auditoria
- **Consentimento** (Art. 7º, I) — quando cabível (ex: comunicações de marketing)

## 5. Compartilhamento

Compartilhamos dados estritamente com:

- **iFood** (`developer.ifood.com.br`) — origem dos dados de pedido/financeiro/reviews
- **Supabase Inc.** (USA / sa-east-1) — hospedagem do banco de dados (Postgres) e
  autenticação
- **Hostinger** (provedor de VPS) — hospedagem da aplicação
- **GitHub Inc.** (USA) — registro de código e imagens Docker

Não vendemos dados a terceiros. Não compartilhamos com fins de marketing.

## 6. Transferência internacional

Os dados podem ser armazenados em servidores fora do Brasil (Supabase, GitHub).
Adotamos provedores com cláusulas contratuais padrão e certificações de segurança
(SOC 2, ISO 27001 quando aplicável).

## 7. Retenção

- **Dados de operação (pedidos, financeiro, reviews):** mantidos enquanto o
  cliente usar a plataforma + 5 anos após cancelamento, pra fins fiscais e legais
- **Logs de acesso:** 6 meses
- **Backups:** rotacionados em 30 dias

## 8. Direitos do titular

Você pode exercer a qualquer momento, gratuitamente, via e-mail
`privacidade@aceleradoragtr.com.br`:

- Confirmação da existência de tratamento
- Acesso aos dados
- Correção de dados incompletos/desatualizados
- Anonimização, bloqueio ou eliminação
- Portabilidade
- Revogação de consentimento
- Informação sobre compartilhamento

Respondemos em até 15 dias.

## 9. Segurança

- Criptografia em trânsito (HTTPS/TLS 1.2+)
- Senhas armazenadas com hash (bcrypt via Supabase Auth)
- Tokens iFood encriptados em repouso (Fernet AES-128)
- Isolamento multi-tenant via Row-Level Security (Postgres)
- Acesso ao banco restrito por VPC e service_role rotacionável

## 10. Cookies

Usamos cookies estritamente necessários para sessão (autenticação Supabase).
Não usamos cookies de marketing ou análise de terceiros.

## 11. Alterações

Esta política pode ser atualizada. Mudanças relevantes serão notificadas por
e-mail e exibidas em destaque na próxima entrada na plataforma.

## 12. Contato

Dúvidas, solicitações ou reclamações:
**privacidade@aceleradoragtr.com.br**

Em caso de não solução, você pode reclamar à **Autoridade Nacional de Proteção
de Dados (ANPD)**: https://www.gov.br/anpd
    """
)
