# MASA in JavaScript / TypeScript — Language-Specific Guide

## Project Layout (Node.js / TypeScript)

```
src/
├── domain_models/
│   ├── order.ts              # Order interface / class
│   ├── ids.ts                # OrderId, CustomerId branded types
│   └── exceptions.ts         # OrderNotFoundError, StorageUnavailableError, …
├── engines/
│   └── order-calculator.ts   # calculateTotal(), applyDiscount()
├── services/
│   └── order.service.ts      # OrderService — orchestration
├── integrations/
│   ├── database/
│   │   ├── models/
│   │   │   └── order.model.ts         # TypeORM Entity / Prisma model
│   │   └── repos/
│   │       └── order.repo.ts          # OrderRepository implementation
│   └── external_apis/
│       └── email.client.ts            # EmailClient (wraps nodemailer / SendGrid SDK)
└── delivery/
    ├── http/
    │   └── order.handler.ts           # Express / Fastify route handler
    └── schemas/
        ├── create-order.request.ts    # Zod schema + toDomain()
        └── create-order.response.ts  # Response DTO + fromDomain()
```

---

## Domain Models

Use `interface` for pure data shapes (preferred for cognizability). Use `class` only
when factory methods or validation on construction is required. Avoid TypeORM `@Entity`
decorators in domain models entirely.

```typescript
// domain_models/ids.ts
declare const __brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [__brand]: B };

export type OrderId   = Brand<string, 'OrderId'>;   // UUID string
export type CustomerId = Brand<string, 'CustomerId'>;

export const OrderId = {
  new: (): OrderId => crypto.randomUUID() as OrderId,
  from: (raw: string): OrderId => raw as OrderId,
};
export const CustomerId = {
  from: (raw: string): CustomerId => raw as CustomerId,
};


// domain_models/order.ts
import type { OrderId, CustomerId } from './ids';

export interface Order {
  readonly id: OrderId;
  readonly customerId: CustomerId;
  readonly itemsTotal: number;
  readonly shippingCost: number;
  readonly status: OrderStatus;
}

export type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'cancelled';


// domain_models/exceptions.ts
export class OrderNotFoundError extends Error {
  constructor(id: string) {
    super(`Order ${id} not found`);
    this.name = 'OrderNotFoundError';
  }
}

export class StorageUnavailableError extends Error {
  constructor(msg?: string) {
    super(msg ?? 'Storage unavailable');
    this.name = 'StorageUnavailableError';
  }
}

export class DuplicateOrderError extends Error {
  constructor(id: string) {
    super(`Order ${id} already exists`);
    this.name = 'DuplicateOrderError';
  }
}
```

---

## Engines (Pure Functions)

Pure functions only. No classes, no `this`, no `async` unless strictly required by a
pure transformation. Use TypeScript's `readonly` to enforce immutability.

```typescript
// engines/order-calculator.ts
import type { Order } from '../domain_models/order';

export function calculateTotal(order: Order): number {
  return order.itemsTotal + order.shippingCost;
}

export function applyDiscount(order: Order, discountPct: number): Order {
  return {
    ...order,
    itemsTotal: parseFloat((order.itemsTotal * (1 - discountPct / 100)).toFixed(2)),
  };
}
```

---

## Services

Declare repository/client interfaces in `services/` using TypeScript `interface`.
Implement them in `integrations/`. This keeps services testable without DB.

```typescript
// services/order.service.ts
import type { Order } from '../domain_models/order';
import type { OrderId } from '../domain_models/ids';
import { calculateTotal } from '../engines/order-calculator';

// Interface — implemented by integrations/database/repos/order.repo.ts
export interface OrderRepository {
  save(order: Order): Promise<Order>;
  findById(id: OrderId): Promise<Order>;
}

export interface EmailClient {
  sendConfirmation(order: Order): Promise<void>;
}

export class OrderService {
  constructor(
    private readonly repo: OrderRepository,
    private readonly emailClient: EmailClient,
  ) {}

  async create(order: Order): Promise<Order> {
    const saved = await this.repo.save(order);
    await this.emailClient.sendConfirmation(saved);
    return saved;
  }

  async get(orderId: OrderId): Promise<Order> {
    return this.repo.findById(orderId);
  }
}
```

---

## Integrations — Repository Pattern

```typescript
// integrations/database/models/order.model.ts  (TypeORM example)
import { Entity, PrimaryGeneratedColumn, Column } from 'typeorm';

@Entity('orders')
export class OrderModel {
  @PrimaryGeneratedColumn()         // internal — never exposed upward
  pk!: number;

  @Column({ type: 'uuid', unique: true })
  id!: string;                      // domain UUID

  @Column({ name: 'customer_id', type: 'uuid' })
  customerId!: string;

  @Column({ name: 'items_total', type: 'decimal' })
  itemsTotal!: number;

  @Column({ name: 'shipping_cost', type: 'decimal' })
  shippingCost!: number;

  @Column({ length: 50 })
  status!: string;
}


// integrations/database/repos/order.repo.ts
import { Repository, DataSource } from 'typeorm';
import { OrderModel } from '../models/order.model';
import type { Order } from '../../../domain_models/order';
import type { OrderId } from '../../../domain_models/ids';
import { OrderNotFoundError, StorageUnavailableError } from '../../../domain_models/exceptions';
import type { OrderRepository } from '../../../services/order.service';

function toOrder(m: OrderModel): Order {
  return {
    id: m.id as Order['id'],
    customerId: m.customerId as Order['customerId'],
    itemsTotal: Number(m.itemsTotal),
    shippingCost: Number(m.shippingCost),
    status: m.status as Order['status'],
  };
}

export class OrderRepositoryImpl implements OrderRepository {
  private readonly repo: Repository<OrderModel>;

  constructor(dataSource: DataSource) {
    this.repo = dataSource.getRepository(OrderModel);
  }

  async save(order: Order): Promise<Order> {
    try {
      await this.repo.save({ ...order });
      return order;
    } catch (e) {
      throw new StorageUnavailableError((e as Error).message);
    }
  }

  async findById(id: OrderId): Promise<Order> {
    try {
      const model = await this.repo.findOne({ where: { id } });
      if (!model) throw new OrderNotFoundError(id);
      return toOrder(model);
    } catch (e) {
      if (e instanceof OrderNotFoundError) throw e;
      throw new StorageUnavailableError((e as Error).message);
    }
  }
}
```

---

## Delivery — Express / Fastify

```typescript
// delivery/schemas/create-order.request.ts
import { z } from 'zod';
import { Order } from '../../domain_models/order';
import { OrderId, CustomerId } from '../../domain_models/ids';

export const CreateOrderSchema = z.object({
  customerId: z.string().uuid(),
  itemsTotal: z.number().positive(),
  shippingCost: z.number().nonnegative(),
});

export type CreateOrderRequest = z.infer<typeof CreateOrderSchema>;

export function toDomain(req: CreateOrderRequest): Order {
  return {
    id: OrderId.new(),
    customerId: CustomerId.from(req.customerId),
    itemsTotal: req.itemsTotal,
    shippingCost: req.shippingCost,
    status: 'pending',
  };
}


// delivery/schemas/create-order.response.ts
import type { Order } from '../../domain_models/order';

export interface CreateOrderResponse {
  id: string;
  status: string;
}

export function fromDomain(order: Order): CreateOrderResponse {
  return { id: order.id, status: order.status };
}


// delivery/http/order.handler.ts  (Express)
import { Router, Request, Response } from 'express';
import { CreateOrderSchema, toDomain } from '../schemas/create-order.request';
import { fromDomain } from '../schemas/create-order.response';
import type { OrderService } from '../../services/order.service';

export function orderRouter(service: OrderService): Router {
  const router = Router();

  router.post('/', async (req: Request, res: Response) => {
    const parsed = CreateOrderSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ errors: parsed.error.flatten() });
      return;
    }
    const order = await service.create(toDomain(parsed.data));
    res.status(201).json(fromDomain(order));
  });

  return router;
}
```

---

## Tooling

### ESLint — enforce layer boundaries

```js
// .eslintrc.js — no-restricted-imports rules
module.exports = {
  rules: {
    'no-restricted-imports': ['error', {
      patterns: [
        // engines must not import from integrations or delivery
        { group: ['*/engines/*'], importNames: [], message: 'engines cannot import from infra layers' },
        // delivery must not import from engines directly
        {
          group: ['*/engines/*'],
          // apply only when in delivery/ — use eslint-plugin-import layers for full support
          message: 'delivery must import through services, not engines directly',
        },
      ],
    }],
  },
};
```

For full layer enforcement use **eslint-plugin-boundaries**:

```json
// .eslintrc.json
{
  "plugins": ["boundaries"],
  "settings": {
    "boundaries/elements": [
      { "type": "domain",       "pattern": "src/domain_models/*" },
      { "type": "engine",       "pattern": "src/engines/*" },
      { "type": "service",      "pattern": "src/services/*" },
      { "type": "integration",  "pattern": "src/integrations/*" },
      { "type": "delivery",     "pattern": "src/delivery/*" }
    ]
  },
  "rules": {
    "boundaries/element-types": ["error", {
      "default": "disallow",
      "rules": [
        { "from": "engine",      "allow": ["domain"] },
        { "from": "service",     "allow": ["domain", "engine", "integration"] },
        { "from": "integration", "allow": ["domain"] },
        { "from": "delivery",    "allow": ["domain", "service"] }
      ]
    }]
  }
}
```

### TypeScript path aliases (tsconfig.json)

```json
{
  "compilerOptions": {
    "baseUrl": "src",
    "paths": {
      "@domain/*":       ["domain_models/*"],
      "@engines/*":      ["engines/*"],
      "@services/*":     ["services/*"],
      "@integrations/*": ["integrations/*"],
      "@delivery/*":     ["delivery/*"]
    },
    "strict": true
  }
}
```

### Jest layout

```
tests/
├── unit/
│   ├── engines/        # pure functions — no mocks
│   └── domain_models/  # value objects, exceptions
└── integration/
    ├── repos/          # real DB or jest-testcontainers
    └── services/       # jest.mock() for repos
```
