export type User = { id: string; username: string; role: string };

export type MenuItem = {
  id: string;
  name: string;
  sku: string | null;
  price_cents: number;
  stock: number;
  kitchenSection: string | null;
};

/** @deprecated use MenuItem */
export type Product = MenuItem;

export type OrderLine = {
  lineId: string;
  menuItemId: string;
  nameSnapshot: string;
  qty: number;
  unitPriceCents: number;
  kotStatus: string;
};

export type RestaurantOrder = {
  id: string;
  orderType: string;
  tableId: string | null;
  status: string;
  lines: OrderLine[];
  subtotalCents: number;
  totalCents: number;
  createdAt?: Date;
  updatedAt?: Date;
};

export type FloorArea = {
  id: string;
  name: string;
  tables: {
    id: string;
    name: string;
    capacity: number;
    status: string;
    currentOrderId: string | null;
  }[];
};

export type CartLine = {
  menuItemId: string;
  name: string;
  unitPriceCents: number;
  qty: number;
};

export type LoginResult =
  | { ok: true; user: User }
  | { ok: false; error: string };

export type HealthResult =
  | { ok: true; connected: true }
  | { ok: false; connected: false; error?: string };

export type PosApi = {
  health: () => Promise<HealthResult>;
  getConfig: () => Promise<{ mongoUri: string }>;
  setMongoUri: (mongoUri: string) => Promise<{ ok: true } | { ok: false; error: string }>;

  login: (username: string, password: string) => Promise<LoginResult>;
  session: () => Promise<User | null>;
  logout: () => Promise<{ ok: true }>;

  listMenu: () => Promise<MenuItem[]>;
  listFloor: () => Promise<FloorArea[]>;

  startOrOpenForTable: (
    tableId: string,
  ) => Promise<{ ok: true; order: RestaurantOrder } | { ok: false; error: string }>;
  getOrder: (orderId: string) => Promise<RestaurantOrder | null>;
  addOrderLines: (
    orderId: string,
    items: { menuItemId: string; qty: number }[],
  ) => Promise<{ ok: true; order: RestaurantOrder } | { ok: false; error: string }>;
  sendKot: (
    orderId: string,
  ) => Promise<{ ok: true; order: RestaurantOrder } | { ok: false; error: string }>;
  completeOrder: (
    orderId: string,
  ) => Promise<{ ok: true; orderId: string; totalCents: number } | { ok: false; error: string }>;
  createWalkIn: (
    items: { menuItemId: string; qty: number }[],
  ) => Promise<{ ok: true; orderId: string; totalCents: number } | { ok: false; error: string }>;

  kitchenQueue: () => Promise<RestaurantOrder[]>;
  kitchenUpdateLine: (
    orderId: string,
    lineId: string,
    status: 'preparing' | 'ready' | 'served',
  ) => Promise<{ ok: true; order: RestaurantOrder } | { ok: false; error: string }>;
};

declare global {
  interface Window {
    posApi?: PosApi;
  }
}

export function getPosApi(): PosApi | null {
  return window.posApi ?? null;
}

export function formatMoney(cents: number): string {
  return (cents / 100).toLocaleString('en-PK', {
    style: 'currency',
    currency: 'PKR',
    minimumFractionDigits: 2,
  });
}
