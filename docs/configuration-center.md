# Configuration Center

## Visao do modulo

O `configuration_center` centraliza configuracoes transversais do ecossistema SMART360. O modulo oferece `system settings`, `feature flags`, `runtime toggles`, perfis modulares, overrides por empresa e trilha basica de auditoria para reduzir hardcodes espalhados pelos bounded contexts.

## Entidades

- `SystemSetting`: configuracoes centrais tipadas por modulo e grupo.
- `FeatureFlag`: flags globais ou modulares, com rollout e configuracao extra.
- `FeatureFlagScope`: escopo de ativacao por usuario, empresa, modulo ou chave.
- `ConfigurationAuditLog`: historico basico de alteracoes.
- `ModuleConfigurationProfile`: presets operacionais por modulo.
- `CompanyConfigurationOverride`: override de configuracao por empresa.
- `RuntimeToggle`: toggle operacional rapido para incidentes e manutencoes.

## System Settings

`SystemSetting` suporta `string`, `number`, `boolean` e `json`. O endpoint de estado efetivo consolida settings ativos e aplica overrides por empresa quando existirem.

## Feature Flags

`FeatureFlag` foi modelada para suportar:

- ativacao global simples
- rollout percentual futuro
- configuracao adicional via JSON
- escopo por usuario, empresa e modulo

O endpoint de estado efetivo retorna flags ativas e toggles operacionais relevantes para o contexto consultado.

## Scopes e Runtime Toggles

`FeatureFlagScope` permite liberar ou bloquear uma flag para recortes operacionais especificos. `RuntimeToggle` atende cenarios como:

- pausar novas entradas
- desabilitar notificacoes externas
- ativar modo de manutencao
- desligar partes do sistema em incidente

## Auditoria

Alteracoes relevantes em settings, flags, profiles, overrides e toggles geram `ConfigurationAuditLog`. Isso fornece rastreabilidade para operacao, seguranca e analytics futuros.

## Integracao com o ecossistema

O modulo foi preparado para atender `core_platform`, `smart_site_factory`, `growth_engine`, `market_core`, `caneca_de_garagem`, `smart_system`, `trust_and_safety`, `marketplace_technicians`, `marketplace_analytical`, `knowledge_engine`, `analytics_platform`, `integration_bus`, `billing`, `notification_center`, `backoffice` e `reporting_center`.

## Endpoints criados

- `GET|POST /api/v1/configuration/system-settings/`
- `GET|POST /api/v1/configuration/feature-flags/`
- `GET|POST /api/v1/configuration/feature-flag-scopes/`
- `GET /api/v1/configuration/audit-logs/`
- `GET|POST /api/v1/configuration/module-profiles/`
- `GET|POST /api/v1/configuration/company-overrides/`
- `GET|POST /api/v1/configuration/runtime-toggles/`
- `GET /api/v1/configuration/effective-settings/`
- `GET /api/v1/configuration/effective-flags/`

## Proximos passos

- adicionar cache de configuracoes efetivas
- integrar atualizacoes com `integration_bus`
- acoplar rollout gradual real por usuario e cohort
- adicionar API de leitura rapida para uso interno dos apps
