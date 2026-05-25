"""Termos de Uso — pública, sem auth."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from dashboard.theme import apply_theme  # noqa: E402

st.set_page_config(page_title="Termos de Uso | gtrifood", page_icon="📜", layout="centered")
apply_theme()

st.title("Termos de Uso")
st.caption("Última atualização: 24 de maio de 2026")

st.markdown(
    """
Estes Termos regulam o uso da plataforma **gtrifood** operada pela
**ACELERADORA GTR PARA RESTAURANTES GESTAO E CONSULTORIA DE DELIVERY LTDA**
("nós", "plataforma", "gtrifood").

Ao criar conta ou acessar a plataforma, você concorda integralmente com estes
Termos e com a [Política de Privacidade](./Privacidade).

## 1. Descrição do serviço

O gtrifood é um software de **agregação e visualização de dados** da API
iFood Developer. Permite que lojistas autorizados consultem:
- Pedidos sincronizados em tempo real
- Indicadores financeiros (vendas, antecipações, ocorrências)
- Avaliações de clientes (reviews)

**Não somos** o iFood. Não processamos pagamentos. Não somos responsáveis pela
operação logística do delivery.

## 2. Cadastro

- Para usar a plataforma, você precisa criar conta com e-mail válido e senha
- Você é responsável por manter suas credenciais em sigilo
- Cada conta corresponde a um **tenant** isolado (multi-loja se aplicável)
- Proibimos contas falsas, automação não autorizada, e uso para fins ilícitos

## 3. Vínculo com iFood

Para sincronizar dados de uma loja, você deve:
- Possuir conta de lojista ativa no iFood
- Autorizar nosso app iFood via fluxo oficial (userCode ou similar)
- Ter os módulos contratados ativos no portal iFood Developer

A autorização pode ser revogada a qualquer momento pelo portal do iFood.

## 4. Obrigações do usuário

- Usar a plataforma apenas para fins lícitos
- Não tentar acessar dados de outros tenants
- Não fazer engenharia reversa, descompilar, ou explorar vulnerabilidades
- Reportar bugs ou vulnerabilidades a `seguranca@aceleradoragtr.com.br`
- Manter dados de contato atualizados

## 5. Nossas obrigações

- Manter a plataforma disponível com **best effort** (sem SLA contratual no
  plano gratuito/MVP)
- Aplicar correções de segurança em tempo razoável
- Tratar dados conforme [Política de Privacidade](./Privacidade)
- Notificar incidentes de segurança quando aplicável

## 6. Disponibilidade

A plataforma é oferecida **"como está"**. Não garantimos:
- Disponibilidade 100% (manutenção e falhas externas — iFood, Supabase — afetam o
  serviço)
- Ausência de bugs
- Adequação a fins específicos não declarados

## 7. Limitação de responsabilidade

Na máxima extensão permitida por lei, **não nos responsabilizamos** por:
- Lucros cessantes ou danos indiretos
- Perda de dados por falha de provedores externos (iFood, Supabase, Hostinger)
- Decisões de negócio tomadas com base nos relatórios da plataforma
- Mau uso pela conta do usuário

Em qualquer caso, nossa responsabilidade total fica limitada ao valor pago pelo
usuário nos últimos 12 meses (zero, no plano gratuito).

## 8. Propriedade intelectual

- Código-fonte do gtrifood pertence à ACELERADORA GTR
- Marcas iFood, Streamlit, Supabase pertencem aos respectivos titulares
- Dados sincronizados via iFood pertencem ao **lojista titular**, processados
  por nós como **operador**

## 9. Cancelamento e exclusão de conta

Você pode cancelar a qualquer momento via:
- E-mail pra `suporte@aceleradoragtr.com.br`
- (Futuramente) botão "Excluir conta" no painel

Dados são removidos conforme retenção descrita na Política de Privacidade.

## 10. Alterações destes Termos

Podemos atualizar estes Termos. Mudanças significativas serão comunicadas por
e-mail com 15 dias de antecedência. Uso continuado após a vigência implica
aceite.

## 11. Lei aplicável e foro

Estes Termos regem-se pelas leis brasileiras. Foro: comarca do município sede
da ACELERADORA GTR (a confirmar — atualizar no próximo release).

## 12. Contato

- **Suporte:** suporte@aceleradoragtr.com.br
- **Privacidade:** privacidade@aceleradoragtr.com.br
- **Segurança:** seguranca@aceleradoragtr.com.br
    """
)
