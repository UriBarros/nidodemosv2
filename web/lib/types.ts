// Tipos espelhando os schemas Pydantic da API FastAPI.
// Em sync com src/gtrifood/api/schemas.py.

export type Merchant = {
  id: string;
  ifood_merchant_id: string;
  name: string;
  corporate_name: string | null;
  cnpj: string | null;
  status: string;
  created_at: string;
};

export type Order = {
  id: string;
  merchant_id: string;
  ifood_order_id: string;
  display_id: string | null;
  status: OrderStatus;
  order_type: string | null;
  created_at_ifood: string | null;
  total_amount: string | null; // Decimal vem como string
  customer_name: string | null;
  synced_at: string;
  updated_at: string;
};

export type OrderEvent = {
  id: string;
  ifood_event_id: string;
  ifood_order_id: string | null;
  code: string;
  full_code: string | null;
  acknowledged_at: string | null;
  received_at: string;
};

export type FinancialEvent = {
  id: string;
  merchant_id: string;
  event_type: "SALE" | "ANTICIPATION" | "OCCURRENCE" | "ADJUSTMENT";
  competence_date: string | null;
  amount: string;
  description: string | null;
  synced_at: string;
};

export type Review = {
  id: string;
  merchant_id: string;
  ifood_review_id: string;
  ifood_order_id: string | null;
  score: number | null;
  comment: string | null;
  customer_name: string | null;
  answered: boolean;
  answer_text: string | null;
  created_at_ifood: string | null;
};

export type OrderStatus =
  | "PLACED"
  | "CONFIRMED"
  | "READY_FOR_PICKUP"
  | "DISPATCHED"
  | "ARRIVED"
  | "CONCLUDED"
  | "CANCELLATION_REQUESTED"
  | "CANCELLATION_REQUEST_ACCEPTED"
  | "CANCELLATION_REQUEST_DENIED"
  | "CANCELLED"
  | string; // permite valores inesperados

export type Count = { count: number };
export type ActionResult = { message: string };

// =============================================================================
// Modelo agência: clients + userCode flow
// =============================================================================
export type ClientStatus = "pending" | "connected" | "disconnected" | "error";

export type Client = {
  id: string;
  name: string;
  ifood_merchant_id: string | null;
  legal_name: string | null;
  cnpj: string | null;
  phone: string | null;
  email: string | null;
  notes: string | null;
  status: ClientStatus;
  connected_at: string | null;
  disconnected_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type ClientIn = {
  name: string;
  ifood_merchant_id?: string;
  legal_name?: string;
  cnpj?: string;
  phone?: string;
  email?: string;
  notes?: string;
};

export type UserCodeSession = {
  id: string;
  client_id: string | null;
  user_code: string;
  verification_url: string;
  verification_url_complete: string | null;
  expires_at: string;
  status: "pending" | "authorized" | "expired" | "error";
  poll_count: number;
};

export type UserCodePoll = {
  session_id: string;
  status: "pending" | "authorized" | "expired" | "error";
  message: string | null;
  client_status: ClientStatus | null;
};

// =============================================================================
// Catalog
// =============================================================================
export type CatalogCategory = {
  id: string;
  merchant_id: string;
  ifood_category_id: string;
  name: string;
  external_code: string | null;
  status: string;
  sequence: number;
  synced_at: string;
};

export type CatalogItem = {
  id: string;
  merchant_id: string;
  category_id: string | null;
  ifood_item_id: string;
  name: string;
  description: string | null;
  external_code: string | null;
  price: string | null; // Decimal vem como string
  original_price: string | null;
  status: "AVAILABLE" | "UNAVAILABLE";
  image_path: string | null;
  synced_at: string;
};

export type CatalogSyncResult = {
  merchant_id: string;
  categories: number;
  items: number;
};

export type CategoryCreateIn = {
  merchant_id: string;
  name: string;
  external_code?: string;
};

export type ItemCreateIn = {
  merchant_id: string;
  category_id: string;
  name: string;
  description?: string;
  price: number;
  status?: "AVAILABLE" | "UNAVAILABLE";
  external_code?: string;
  image_path?: string;
};

export type ItemUpdateIn = {
  name?: string;
  description?: string;
  image_path?: string;
  external_code?: string;
};

export type UploadImageOut = {
  path?: string;
  [key: string]: any;
};

export type OptionGroup = {
  id?: string;
  name?: string;
  min?: number;
  max?: number;
  status?: string;
  options?: any[];
  [key: string]: any;
};

export type OptionGroupCreateIn = {
  merchant_id: string;
  name: string;
  min_choices?: number;
  max_choices?: number;
  external_code?: string;
};

export type OptionCreateIn = {
  merchant_id: string;
  option_group_id: string;
  name: string;
  price: number;
  status?: "AVAILABLE" | "UNAVAILABLE";
  image_path?: string;
  external_code?: string;
};

// =============================================================================
// Merchant — interrupções + horários
// =============================================================================
export type Interruption = {
  id?: string;
  description?: string;
  start?: string;
  end?: string;
  [key: string]: any; // iFood payload completo
};

export type InterruptionIn = {
  description: string;
  start: string; // ISO datetime
  end: string;
};

export type DayOfWeek =
  | "MONDAY"
  | "TUESDAY"
  | "WEDNESDAY"
  | "THURSDAY"
  | "FRIDAY"
  | "SATURDAY"
  | "SUNDAY";

export type Shift = {
  dayOfWeek: DayOfWeek;
  start: string; // HH:MM:SS
  duration: number; // minutos
};

export type OpeningHours = {
  shifts?: Shift[];
  [key: string]: any;
};
