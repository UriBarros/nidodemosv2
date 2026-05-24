# Acesso à API iFood — homologação e produção

## Estado atual (2026-05-23)

✅ Conta no portal `developer.ifood.com.br` criada (perfil **Profissional**)
✅ App Centralizado **Teste (C)** criado — categoria TEST
✅ Credenciais `client_id` + `client_secret` disponíveis na aba "Credenciais"
✅ 1 merchant fictício pré-vinculado (`CNPJ 99.999.999/9999-99`)
✅ Todos os módulos liberados pra teste

⏳ App de **produção** — ainda não criado

## Limitações do app de teste

Conforme o iFood na aba "Detalhes":

> "Aplicativo exclusivo para testes com permissão na sua loja de teste. **Não é possível alterar módulos nem solicitar acesso a outros merchants.**"

Significa:
- Funciona **apenas** com o merchant fictício
- Não dá pra conectar lojas reais
- Serve pra desenvolver e validar a integração

## Como ir para produção (quando o MVP estiver pronto)

1. **Cadastrar novo app de produção** no portal
   - Menu → "Meus aplicativos" → "Cadastrar aplicativo"
   - Categoria: **PRODUCTION** (ou similar — não TEST)
   - Tipo: **Centralizado**
   - Selecionar módulos necessários (Order, Events, Merchant, Financial, Review)

2. **Solicitar homologação**
   - O iFood vai pedir documentação técnica:
     - Descrição da integração
     - Fluxo de uso
     - Tratamento de eventos
     - Política de privacidade do app
   - Possíveis testes técnicos guiados pelo time iFood

3. **Configurar URL pública de webhook** (opcional mas recomendado em prod)
   - Reduz latência vs polling
   - URL precisa ser HTTPS válida com domínio do app
   - Configurar na aba "Webhook" do app

4. **Onboarding de merchants reais**
   - Modelo Centralizada: cada lojista autoriza o app via fluxo de "userCode"
   - Lojista vai na conta dele do iFood Gestor → autoriza nosso app
   - Após autorização, o merchant aparece na aba "Permissões" do app

## Fluxo userCode (autorização por merchant em produção)

Em produção, pra cada lojista que vai usar o sistema:

```
1. App chama POST /authentication/v1.0/oauth/userCode
   → recebe { userCode, verificationUrlComplete }
2. App mostra para o lojista: "Acesse <verificationUrlComplete> e cole o código: <userCode>"
3. Lojista autoriza no portal iFood
4. App faz polling em POST /authentication/v1.0/oauth/token
   com grant_type=authorization_code + authorizationCode (do userCode)
5. Recebe accessToken + refreshToken específicos do merchant
6. Salva tokens + merchantId associado ao tenant interno
```

Este fluxo **não se aplica ao app de teste atual** — lá o merchant fictício já está vinculado.

## Checklist para sair de teste → produção

- [ ] MVP funcional rodando com app de teste
- [ ] Documentação técnica da integração escrita
- [ ] Domínio HTTPS + URL de webhook configurada
- [ ] Política de privacidade publicada
- [ ] Termos de uso publicados
- [ ] Cadastrar app de produção no portal
- [ ] Solicitar homologação
- [ ] Aguardar aprovação iFood
- [ ] Implementar fluxo userCode na UI
- [ ] Onboarding do primeiro cliente real

## Contato com suporte iFood

- Portal → "Suporte" (canto superior direito)
- Email aberto via portal vincula automaticamente seu app/conta
