# CANECA DE GARAGEM

## Visao do modulo

O Caneca de Garagem foi estruturado como marketplace-first para produtos personalizados, sublimação, camisetas, canecas e artesanato, com produção própria integrada.

## Entidades

- `MarketplaceVendor`, `MarketplaceProduct`, `MarketplaceOrder`, `MarketplaceOrderItem` via `market_core`
- `CreativeStoreProfile`
- `CustomizationTemplate`
- `CustomizationRequest`
- `ArtworkAsset`
- `ProductionJob`
- `ProductionStep`
- `ShipmentPreparation`

## Fluxo do pedido personalizado

1. Vendedor cadastra produto no `market_core`.
2. Loja criativa define template de personalização.
3. Cliente gera pedido e item de pedido.
4. Item recebe `CustomizationRequest` com textos, imagens e observações.
5. Assets entram na trilha de arte e revisão.

## Fluxo de producao

1. `ProductionJob` entra na fila.
2. O sistema cria etapas padrão de produção.
3. Equipe acompanha andamento e conclusão.
4. Ao concluir, item vai para pronto para envio.
5. `ShipmentPreparation` registra postagem e entrega.

## Endpoints

- `GET|POST /api/v1/caneca-de-garagem/vendors/`
- `GET|POST /api/v1/caneca-de-garagem/products/`
- `GET|POST /api/v1/caneca-de-garagem/orders/`
- `GET|POST /api/v1/caneca-de-garagem/order-items/`
- `GET|POST /api/v1/caneca-de-garagem/store-profiles/`
- `GET|POST /api/v1/caneca-de-garagem/customization-templates/`
- `GET|POST /api/v1/caneca-de-garagem/customization-requests/`
- `GET|POST /api/v1/caneca-de-garagem/artwork-assets/`
- `GET|POST /api/v1/caneca-de-garagem/production-jobs/`
- `POST /api/v1/caneca-de-garagem/production-jobs/{id}/start/`
- `POST /api/v1/caneca-de-garagem/production-jobs/{id}/complete/`
- `GET|POST /api/v1/caneca-de-garagem/production-steps/`
- `GET|POST /api/v1/caneca-de-garagem/shipment-preparations/`
- `POST /api/v1/caneca-de-garagem/shipment-preparations/{id}/mark_posted/`
