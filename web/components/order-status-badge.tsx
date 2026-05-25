import { Badge } from "@/components/ui/badge";
import type { OrderStatus } from "@/lib/types";

const LABEL: Record<string, string> = {
  PLACED: "Recebido",
  CONFIRMED: "Confirmado",
  READY_FOR_PICKUP: "Pronto",
  DISPATCHED: "A caminho",
  ARRIVED: "Entregue",
  CONCLUDED: "Concluído",
  CANCELLATION_REQUESTED: "Cancel. solicitado",
  CANCELLATION_REQUEST_ACCEPTED: "Cancel. aceito",
  CANCELLATION_REQUEST_DENIED: "Cancel. negado",
  CANCELLED: "Cancelado",
};

const VARIANT: Record<string, "default" | "success" | "warning" | "destructive" | "info" | "secondary"> = {
  PLACED: "info",
  CONFIRMED: "info",
  READY_FOR_PICKUP: "warning",
  DISPATCHED: "warning",
  ARRIVED: "success",
  CONCLUDED: "success",
  CANCELLATION_REQUESTED: "warning",
  CANCELLATION_REQUEST_ACCEPTED: "destructive",
  CANCELLATION_REQUEST_DENIED: "secondary",
  CANCELLED: "destructive",
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return (
    <Badge variant={VARIANT[status] ?? "secondary"} className="font-medium">
      {LABEL[status] ?? status}
    </Badge>
  );
}
