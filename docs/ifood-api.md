# iFood Developer API — Referência interna

App usado: **Centralizado de TESTE** (categoria TEST, 1 merchant fictício).

## Autenticação

Modelo **client_credentials** (Centralizada).

```http
POST https://merchant-api.ifood.com.br/authentication/v1.0/oauth/token
Content-Type: application/x-www-form-urlencoded

grantType=client_credentials&clientId=...&clientSecret=...
```

Resposta:
```json
{
  "accessToken": "eyJ...",
  "type": "bearer",
  "expiresIn": 10800
}
```

- `expiresIn` em segundos (~3h)
- Reusar token até expirar; renovar com margem de 5min
- Header em todas as chamadas: `Authorization: Bearer <accessToken>`

## Módulos liberados no app de teste

Todos abaixo estão liberados — não precisa solicitar.

| Módulo | Endpoint base | Uso no projeto |
|---|---|---|
| **Merchant** | `/merchant/v1.0/merchants` | Listar lojas, status |
| **Order** | `/order/v1.0/orders/{id}` | Detalhes do pedido |
| **Events** | `/events/v1.0/events:polling` | Polling de eventos novos |
| **Catalog** | `/catalog/v2.0/...` | Catálogo de produtos |
| **Financial** | `/financial-v3.0/...` | Faturas, repasses, vendas |
| **Review** | `/review/v1.0/merchants/{id}/reviews` | Avaliações |
| Logistics, Shipping, Item, Picking | — | Não usados no MVP |
| Groceries, Promotion (legado) | — | Ignorar |

## Fluxo de Eventos (polling)

Padrão recomendado pelo iFood pra app de teste (sem URL pública pra webhook):

```
loop a cada 30s:
  1. GET /events/v1.0/events:polling
     → retorna array de eventos novos
  2. processa cada evento (ex: novo pedido, mudança de status)
  3. POST /events/v1.0/events/acknowledgment
     body: [{ id: <eventId> }, ...]
     → sem ack, iFood reenvia o mesmo evento na próxima chamada
```

**Importante:** o `acknowledgment` é obrigatório. Sem ele, eventos se repetem indefinidamente.

Tipos de evento comuns:
- `PLC` — Pedido criado (Placed)
- `CFM` — Confirmado
- `DSP` — Despachado (Dispatched)
- `CON` — Concluído (Concluded)
- `CAN` — Cancelado

## Endpoints principais que vamos usar

### Merchant
- `GET /merchant/v1.0/merchants` — lista todos os merchants do app
- `GET /merchant/v1.0/merchants/{id}` — detalhes
- `GET /merchant/v1.0/merchants/{id}/status` — status operacional

### Order
- `GET /order/v1.0/orders/{orderId}` — detalhes completos do pedido
- `POST /order/v1.0/orders/{orderId}/confirm` — confirmar pedido
- `POST /order/v1.0/orders/{orderId}/dispatch` — despachar
- `POST /order/v1.0/orders/{orderId}/cancellation` — cancelar

### Events
- `GET /events/v1.0/events:polling`
- `POST /events/v1.0/events/acknowledgment`

### Financial
- `GET /financial-v3.0/merchants/{id}/sales` — vendas
- `GET /financial-v3.0/merchants/{id}/anticipations` — antecipações
- `GET /financial-v3.0/merchants/{id}/occurrences` — ocorrências (ajustes/débitos)

### Review
- `GET /review/v1.0/merchants/{merchantId}/reviews` — avaliações
- `POST /review/v1.0/merchants/{merchantId}/reviews/{reviewId}/answers` — responder

## Rate limits

iFood não publica limites exatos. Recomendações:
- Polling de eventos: **mínimo 30s entre chamadas** (recomendado pelo iFood)
- Backoff exponencial em 429/503
- Não usar threads — sempre async sequencial por merchant

## Referências oficiais

- Portal: https://developer.ifood.com.br
- Docs: https://developer.ifood.com.br/pt-BR/docs/references
- Suporte: via portal → "Suporte"
