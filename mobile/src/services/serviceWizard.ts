/*
 * P-002 · Wizard A no app. Regras puras (sem React) do cadastro de
 * serviço em cinco etapas, as mesmas da Web:
 * Básico; Preço e duração; Local e disponibilidade; Imagem; Revisão.
 * Os limites espelham o servidor (ProfessionalServiceDraftForm e
 * /api/v1/onboarding/professional/services); o servidor continua sendo a
 * autoridade e qualquer erro dele volta para a etapa certa.
 */

export const SERVICE_STEPS = [
  { key: "basico", label: "Básico" },
  { key: "preco", label: "Preço e duração" },
  { key: "local", label: "Local e disponibilidade" },
  { key: "imagem", label: "Imagem" },
  { key: "revisao", label: "Revisão" },
] as const;

export type ServiceStepKey = (typeof SERVICE_STEPS)[number]["key"];

export const SERVICE_CATEGORIES = [
  ["cabelo", "Cabelo"],
  ["unhas", "Unhas"],
  ["barbearia", "Barbearia"],
  ["estetica", "Estética"],
  ["tatuagem", "Tatuagem"],
  ["sobrancelhas", "Sobrancelhas"],
] as const;

export const SERVICE_STATUS_LABELS: Record<string, string> = {
  draft: "Rascunho",
  published: "Publicado",
  paused: "Pausado",
  archived: "Arquivado",
};

export const SLOT_STATUS_LABELS: Record<string, string> = {
  available: "Disponível",
  held: "Em reserva",
  booked: "Reservado",
  blocked_external: "Bloqueado pela agenda",
  blocked_manual: "Bloqueado manualmente",
  expired: "Expirado",
};

export const LIMITS = {
  title: 160,
  shortDescription: 220,
  description: 4000,
  durationMin: 10,
  durationMax: 720,
  priceMax: 99999999.99,
} as const;

export const EMPTY = "Ainda não informado";

export type ServiceWizardValues = {
  name: string;
  category: string;
  shortDescription: string;
  description: string;
  regularPrice: string;
  price: string;
  duration: string;
  establishmentId: number | null;
};

export type StepErrors = Partial<Record<keyof ServiceWizardValues, string>>;

export function categoryLabel(key: string): string {
  const found = SERVICE_CATEGORIES.find(([value]) => value === key);
  return found ? found[1] : key;
}

/** "120", "120,5", "1.200,50" ou "120.50" → número; vazio → null; inválido → NaN. */
export function parseMoney(text: string): number | null {
  const raw = text.trim().replace(/\s/g, "").replace(/^R\$/i, "");
  if (!raw) return null;
  const normalized = raw.includes(",") ? raw.replace(/\./g, "").replace(",", ".") : raw;
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return Number.NaN;
  return Number(normalized);
}

export function formatMoney(value: number): string {
  return `R$ ${value.toFixed(2).replace(".", ",")}`;
}

export function stepErrors(step: number, values: ServiceWizardValues): StepErrors {
  const errors: StepErrors = {};
  if (step === 0) {
    const name = values.name.trim();
    if (!name) errors.name = "Informe o nome do serviço.";
    else if (name.length > LIMITS.title) errors.name = `Use até ${LIMITS.title} caracteres.`;
    if (!SERVICE_CATEGORIES.some(([key]) => key === values.category)) errors.category = "Selecione uma categoria.";
    const short = values.shortDescription.trim();
    if (!short) errors.shortDescription = "Informe a descrição resumida.";
    else if (short.length > LIMITS.shortDescription) errors.shortDescription = `Use até ${LIMITS.shortDescription} caracteres.`;
    if (values.description.length > LIMITS.description) errors.description = `Use até ${LIMITS.description} caracteres.`;
  }
  if (step === 1) {
    const regular = parseMoney(values.regularPrice);
    const price = parseMoney(values.price);
    if (regular === null) errors.regularPrice = "Informe o preço regular.";
    else if (Number.isNaN(regular) || regular > LIMITS.priceMax) errors.regularPrice = "Informe um valor válido, como 120,00.";
    if (price === null) errors.price = "Informe o preço IDDUN.";
    else if (Number.isNaN(price) || price > LIMITS.priceMax) errors.price = "Informe um valor válido, como 100,00.";
    else if (regular !== null && !Number.isNaN(regular) && price > regular) {
      errors.price = "O preço IDDUN não pode ser maior que o preço regular.";
    }
    const minutes = Number(values.duration);
    if (!/^\d+$/.test(values.duration.trim()) || minutes < LIMITS.durationMin || minutes > LIMITS.durationMax) {
      errors.duration = `A duração deve estar entre ${LIMITS.durationMin} e ${LIMITS.durationMax} minutos.`;
    }
  }
  return errors;
}

/** Primeira etapa com problema antes de `target`; senão o próprio `target`. */
export function firstReachableStep(target: number, values: ServiceWizardValues): number {
  for (let step = 0; step < target; step += 1) {
    if (Object.keys(stepErrors(step, values)).length > 0) return step;
  }
  return target;
}

/** Erro do servidor → etapa onde a pessoa corrige. */
export function stepForServerError(code: string | undefined): number | null {
  switch (code) {
    case "invalid_title":
    case "invalid_category":
    case "invalid_description":
      return 0;
    case "invalid_price":
    case "invalid_duration":
      return 1;
    case "invalid_establishment":
    case "establishment_not_allowed":
    case "service_has_slots":
      return 2;
    default:
      return null;
  }
}

export type ServiceDraftPayload = {
  name: string;
  category: string;
  shortDescription: string;
  description: string;
  regularPrice: number;
  price: number;
  durationMinutes: number;
  establishmentId: number | null;
};

/** Só monta o envio com as etapas válidas; nunca inventa preço regular. */
export function buildPayload(values: ServiceWizardValues): ServiceDraftPayload | null {
  if (firstReachableStep(SERVICE_STEPS.length - 1, values) !== SERVICE_STEPS.length - 1) return null;
  return {
    name: values.name.trim(),
    category: values.category,
    shortDescription: values.shortDescription.trim(),
    description: values.description.trim(),
    regularPrice: parseMoney(values.regularPrice) as number,
    price: parseMoney(values.price) as number,
    durationMinutes: Number(values.duration),
    establishmentId: values.establishmentId,
  };
}
