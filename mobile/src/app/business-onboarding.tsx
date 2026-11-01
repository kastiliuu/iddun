// Cadastro de Estabelecimento por etapas (PR 3 do onboarding V0).
// Mesma ordem, mensagens e regras do Web: o rascunho nasce na etapa 1
// (nome, tipo, cidade e UF), cada etapa seguinte é salva pelo id estável
// (PATCH) e a publicação é explícita (F1). Endereço só para físico ou
// híbrido (F2), apresentação 40+ (D-ONB-04), e-mail da conta só como
// sugestão (D-ONB-05) e os 7 tipos do Web (D-ONB-06).
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useLocalSearchParams, useRouter } from "expo-router";

import { ApiError } from "@/api/client";
import {
  type BusinessHours,
  type EstablishmentDraft,
  type EstablishmentDraftPatch,
  type MissingRequirement,
  getEstablishmentDraft,
  patchEstablishmentDraft,
  publishEstablishment,
  saveEstablishmentDraft,
} from "@/api/onboarding";
import {
  type EstablishmentMedia,
  deleteEstablishmentGalleryItem,
  getEstablishmentMedia,
  uploadEstablishmentGalleryItem,
  uploadEstablishmentImage,
} from "@/api/media";
import { Button } from "@/components/Button";
import { useOnboardingStyles } from "@/components/onboarding/onboardingStyles";
import { Icon } from "@/components/Icon";
import { MediaPermissionError, pickAndPrepareImage } from "@/media/imagePipeline";
import { store } from "@/store/local";
import { useTheme } from "@/theme";

type StepKey = "basics" | "operation" | "address" | "hours" | "contact" | "personalize" | "review";

const STEPS: { key: StepKey; title: string; lead: string }[] = [
  {
    key: "basics",
    title: "Qual é o seu espaço e onde ele fica?",
    lead: "Nome, tipo e cidade criam o rascunho da sua página. Nada fica público até você publicar.",
  },
  {
    key: "operation",
    title: "Como seu negócio atende?",
    lead: "Se você atende só no endereço do cliente, nenhum endereço aparece na sua página.",
  },
  {
    key: "address",
    title: "Qual é o endereço comercial?",
    lead: "Use o endereço do espaço onde os clientes são atendidos. Nunca um endereço residencial.",
  },
  {
    key: "hours",
    title: "Quando você atende?",
    lead: "Funcionamento do espaço. Os horários de cada profissional são definidos depois, na agenda.",
  },
  {
    key: "contact",
    title: "Como os clientes falam com você?",
    lead: "Uma apresentação curta e pelo menos um contato: telefone ou e-mail comercial.",
  },
  {
    key: "personalize",
    title: "Mostre seu espaço",
    lead: "Logo, capa e fotos são opcionais. Dá para fazer agora ou depois, em Editar empresa.",
  },
  {
    key: "review",
    title: "Revise e publique sua página",
    lead: "Publicar coloca a página no ar. Reservas dependem de serviços, profissionais e horários, que você organiza depois.",
  },
];

// D-ONB-06: os mesmos 7 tipos do Web e da API.
const TYPES: [string, string][] = [
  ["salao", "Salão de beleza"],
  ["barbearia", "Barbearia"],
  ["tatuagem", "Estúdio de tatuagem"],
  ["unhas", "Studio de unhas"],
  ["estetica", "Estética"],
  ["bem-estar", "Bem-estar / Spa"],
  ["multisservicos", "Multi-serviços"],
];

const MODES: [string, string][] = [
  ["physical", "No estabelecimento"],
  ["mobile", "No endereço do cliente"],
  ["hybrid", "Nos dois (híbrido)"],
];

const HOURS_MODES: [string, string][] = [
  ["scheduled", "Sob agendamento"],
  ["fixed_hours", "Horários fixos"],
];

const DAYS: [keyof BusinessHours, string][] = [
  ["monday", "Segunda"],
  ["tuesday", "Terça"],
  ["wednesday", "Quarta"],
  ["thursday", "Quinta"],
  ["friday", "Sexta"],
  ["saturday", "Sábado"],
  ["sunday", "Domingo"],
];

const HOUR_PATTERN = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
const DESCRIPTION_MIN = 40;
const DESCRIPTION_MAX = 2000;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type FieldErrors = Partial<Record<string, string>>;
type DayRange = { start: string; end: string };

function stepIndex(key: string | undefined) {
  const index = STEPS.findIndex((step) => step.key === key);
  return index === -1 ? 0 : index;
}

export default function BusinessOnboardingScreen() {
  const styles = useOnboardingStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ id?: string }>();

  const [loading, setLoading] = useState(Boolean(params.id));
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [draft, setDraft] = useState<EstablishmentDraft | null>(null);
  const [index, setIndex] = useState(0);
  const [returnToReview, setReturnToReview] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [stepError, setStepError] = useState("");
  const [missing, setMissing] = useState<MissingRequirement[]>([]);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [city, setCity] = useState("");
  const [uf, setUf] = useState("");
  const [mode, setMode] = useState("");
  const [address, setAddress] = useState("");
  const [complement, setComplement] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [hoursMode, setHoursMode] = useState("");
  const [hours, setHours] = useState<Record<string, DayRange>>({});
  const [description, setDescription] = useState("");
  const [phone, setPhone] = useState("");
  const [whatsapp, setWhatsapp] = useState(true);
  const [email, setEmail] = useState("");
  const [media, setMedia] = useState<EstablishmentMedia | null>(null);
  const [mediaBusy, setMediaBusy] = useState<"logo" | "cover" | "gallery" | null>(null);

  const hydrate = useCallback((item: EstablishmentDraft) => {
    setDraft(item);
    setName(item.name);
    setCategory(item.category ?? "");
    setCity(item.city);
    setUf(item.state);
    setMode(item.operationMode ?? "");
    setAddress(item.addressLine1 ?? "");
    setComplement(item.addressLine2 ?? "");
    setNeighborhood(item.neighborhood);
    setPostalCode(item.postalCode ?? "");
    setHoursMode(item.businessHoursMode ?? "");
    setHours(
      Object.fromEntries(
        Object.entries(item.businessHours ?? {}).map(([day, periods]) => [
          day,
          { start: periods?.[0]?.start ?? "", end: periods?.[0]?.end ?? "" },
        ]),
      ),
    );
    setDescription(item.description);
    setPhone(item.phone);
    setWhatsapp(item.whatsappEnabled ?? true);
    // D-ONB-05: sugestão visível; só vale ao salvar a etapa de contato.
    setEmail(item.commercialEmail || store.getUser()?.email || "");
    setMissing(item.journey?.missingRequirements ?? []);
  }, []);

  useEffect(() => {
    if (!params.id) return;
    let mounted = true;
    const load = async () => {
      try {
        const response = await getEstablishmentDraft(params.id as string);
        if (!mounted) return;
        if (response.establishment.isActive) {
          router.replace("/(tabs)/profile");
          return;
        }
        hydrate(response.establishment);
        setIndex(stepIndex(response.establishment.journey?.currentStep));
      } catch {
        if (mounted) setStepError("Não foi possível carregar o rascunho. Verifique a conexão e tente de novo.");
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void load();
    return () => {
      mounted = false;
    };
  }, [hydrate, params.id, router]);

  const needsAddress = mode === "physical" || mode === "hybrid";
  const step = STEPS[index];

  const goTo = (next: number, fromReview = false) => {
    setErrors({});
    setStepError("");
    setReturnToReview(fromReview);
    setIndex(next);
  };

  const neighbour = (direction: 1 | -1, modeValue = mode) => {
    let position = index + direction;
    while (position >= 0 && position < STEPS.length) {
      const key = STEPS[position].key;
      if (key !== "address" || modeValue === "physical" || modeValue === "hybrid") return position;
      position += direction;
    }
    return null;
  };

  const goBack = () => {
    const previous = neighbour(-1);
    if (previous === null) {
      if (router.canGoBack()) router.back();
      else router.replace("/(tabs)/profile");
      return;
    }
    goTo(previous);
  };

  // Mesmas mensagens do Web.
  const validate = (): { changes: EstablishmentDraftPatch; found: FieldErrors } => {
    const found: FieldErrors = {};
    const changes: EstablishmentDraftPatch = {};
    switch (step.key) {
      case "basics":
        if (name.trim().length < 2) found.name = "Informe o nome do estabelecimento.";
        if (!category) found.category = "Escolha o tipo de estabelecimento.";
        if (city.trim().length < 2) found.city = "Informe cidade e UF.";
        if (!/^[A-Za-z]{2}$/.test(uf.trim())) found.uf = "Use as duas letras da UF.";
        Object.assign(changes, {
          name: name.trim(),
          category,
          city: city.trim(),
          state: uf.trim().toUpperCase(),
        });
        break;
      case "operation":
        if (!mode) found.mode = "Diga como o estabelecimento atende.";
        changes.operationMode = mode as EstablishmentDraftPatch["operationMode"];
        break;
      case "address":
        if (!address.trim()) found.address = "Informe o endereço comercial.";
        Object.assign(changes, {
          addressLine1: address.trim(),
          addressLine2: complement.trim() || null,
          neighborhood: neighborhood.trim() || null,
          postalCode: postalCode.trim() || null,
        });
        break;
      case "hours": {
        if (!hoursMode) {
          found.hoursMode = "Defina o funcionamento: sob agendamento ou horários fixos.";
          break;
        }
        if (hoursMode === "scheduled") {
          Object.assign(changes, { businessHoursMode: "scheduled", businessHours: null });
          break;
        }
        const filled = Object.entries(hours).filter(([, range]) => range.start.trim() || range.end.trim());
        const invalid =
          filled.length === 0 ||
          filled.some(
            ([, range]) =>
              !HOUR_PATTERN.test(range.start) || !HOUR_PATTERN.test(range.end) || range.start >= range.end,
          );
        if (invalid) found.hoursMode = "Informe abertura e fechamento válidos (HH:MM) em pelo menos um dia.";
        Object.assign(changes, {
          businessHoursMode: "fixed_hours",
          businessHours: Object.fromEntries(
            filled.map(([day, range]) => [day, [{ start: range.start, end: range.end }]]),
          ),
        });
        break;
      }
      case "contact": {
        const length = description.trim().length;
        if (!length) found.description = "Escreva a apresentação do estabelecimento.";
        else if (length < DESCRIPTION_MIN || length > DESCRIPTION_MAX) {
          found.description = `Use entre ${DESCRIPTION_MIN} e ${DESCRIPTION_MAX} caracteres.`;
        }
        if (email.trim() && !EMAIL_PATTERN.test(email.trim())) found.email = "Informe um e-mail válido.";
        if (!phone.trim() && !email.trim()) found.phone = "Informe telefone ou e-mail comercial.";
        Object.assign(changes, {
          description: description.trim(),
          phone: phone.trim() || null,
          commercialEmail: email.trim().toLowerCase() || null,
        });
        changes.whatsappEnabled = Boolean(whatsapp && phone.trim());
        break;
      }
      default:
        break;
    }
    return { changes, found };
  };

  const handleContinue = async () => {
    const { changes, found } = validate();
    setErrors(found);
    setStepError("");
    if (Object.keys(found).length > 0) return;
    try {
      setSaving(true);
      let response;
      if (!draft) {
        // Etapa 1 cria o rascunho; as próximas usam o id estável.
        response = await saveEstablishmentDraft({
          name: changes.name ?? "",
          category: changes.category ?? "",
          city: changes.city ?? "",
          state: changes.state ?? "",
        });
      } else {
        response = await patchEstablishmentDraft(draft.id, changes);
      }
      hydrate(response.establishment);
      const nextMode = changes.operationMode ?? mode;
      const next = returnToReview ? STEPS.length - 1 : neighbour(1, nextMode ?? "");
      goTo(next ?? STEPS.length - 1);
    } catch (error) {
      setStepError(error instanceof Error ? error.message : "Não foi possível salvar. Tente novamente.");
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (step.key !== "personalize" || !draft) return;
    let mounted = true;
    getEstablishmentMedia(draft.id)
      .then((response) => {
        if (mounted) setMedia(response.media);
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, [step.key, draft]);

  // D-ONB-07: logo, capa e galeria pelo app (opcionais).
  const handleMedia = async (kind: "logo" | "cover" | "gallery") => {
    if (!draft || mediaBusy) return;
    setStepError("");
    try {
      const image = await pickAndPrepareImage(
        "library",
        kind === "logo" ? "avatar" : kind === "cover" ? "cover" : "portfolio",
      );
      if (!image) return;
      setMediaBusy(kind);
      const response =
        kind === "gallery"
          ? await uploadEstablishmentGalleryItem(draft.id, image)
          : await uploadEstablishmentImage(draft.id, kind, image);
      setMedia(response.media);
    } catch (error) {
      setStepError(
        error instanceof MediaPermissionError || error instanceof Error
          ? error.message
          : "Não foi possível salvar a imagem. Tente novamente.",
      );
    } finally {
      setMediaBusy(null);
    }
  };

  const handleRemoveGallery = async (itemId: number) => {
    if (!draft) return;
    try {
      const response = await deleteEstablishmentGalleryItem(draft.id, itemId);
      setMedia(response.media);
    } catch (error) {
      setStepError(error instanceof Error ? error.message : "Não foi possível remover a foto.");
    }
  };

  const handlePublish = async () => {
    if (!draft) return;
    setStepError("");
    try {
      setSaving(true);
      const response = await publishEstablishment(draft.id);
      setDraft(response.establishment);
      setDone(true);
    } catch (error) {
      if (error instanceof ApiError) {
        const details = error.details as { missingRequirements?: MissingRequirement[] } | undefined;
        if (details?.missingRequirements?.length) setMissing(details.missingRequirements);
      }
      setStepError(error instanceof Error ? error.message : "Não foi possível publicar. Tente novamente.");
    } finally {
      setSaving(false);
    }
  };

  const fieldError = (key: string) =>
    errors[key] ? (
      <Text style={styles.fieldError} accessibilityLiveRegion="polite">
        {errors[key]}
      </Text>
    ) : null;

  const input = (
    label: string,
    value: string,
    onChange: (text: string) => void,
    key: string,
    extra: Partial<React.ComponentProps<typeof TextInput>> = {},
  ) => (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChange}
        accessibilityLabel={label}
        placeholderTextColor={colors.muted}
        style={[styles.input, errors[key] && styles.inputError]}
        {...extra}
      />
      {fieldError(key)}
    </View>
  );

  const radios = (options: [string, string][], selected: string, onSelect: (value: string) => void, label: string) => (
    <View style={styles.choices} accessibilityRole="radiogroup" accessibilityLabel={label}>
      {options.map(([value, text]) => {
        const checked = selected === value;
        return (
          <Pressable
            key={value}
            accessibilityRole="radio"
            accessibilityState={{ checked }}
            accessibilityLabel={text}
            onPress={() => onSelect(value)}
            style={({ pressed }) => [styles.choice, checked && styles.choiceSelected, pressed && styles.pressed]}
          >
            <Text style={styles.choiceText}>{text}</Text>
            <View style={[styles.radio, checked && styles.checkSelected]}>
              {checked ? <Icon name="check" size={14} color={colors.onBrandPrimary} /> : null}
            </View>
          </Pressable>
        );
      })}
    </View>
  );

  if (loading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator color={colors.plum} />
      </View>
    );
  }

  if (done && draft) {
    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.doneMark}>
            <Icon name="check" size={24} color={colors.onBrandPrimary} />
          </View>
          <Text style={styles.kicker}>CADASTRO DO ESTABELECIMENTO</Text>
          <Text style={styles.title} accessibilityRole="header">A página de {draft.name} está no ar.</Text>
          <Text style={styles.lead}>
            Clientes já podem encontrar o seu espaço no IDDUN. Reservas ainda não estão abertas: elas
            começam quando houver serviços com profissionais e horários disponíveis.
          </Text>
          <Text style={styles.subtitle}>Próximos passos</Text>
          {[
            ["Convidar a equipe", "Profissionais que atendem no espaço, com o aceite deles.", `/establishment-team/${draft.id}`],
            ["Ver a página", "Como clientes veem o seu espaço.", `/establishment/${draft.id}`],
          ].map(([title, body, href]) => (
            <Pressable
              key={href}
              accessibilityRole="button"
              onPress={() => router.push(href as never)}
              style={({ pressed }) => [styles.nextItem, pressed && styles.pressed]}
            >
              <View style={styles.nextText}>
                <Text style={styles.nextTitle}>{title}</Text>
                <Text style={styles.nextBody}>{body}</Text>
              </View>
              <Icon name="chevron-right" size={18} color={colors.muted} />
            </Pressable>
          ))}
          <View style={styles.actions}>
            <Button title="Explorar o IDDUN" fullWidth onPress={() => router.replace("/(tabs)")} />
          </View>
        </ScrollView>
      </View>
    );
  }

  const journeySteps = draft?.journey?.steps ?? [];

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.top}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={goBack}
            style={({ pressed }) => [styles.iconButton, pressed && styles.pressed]}
          >
            <Icon name="arrow-left" size={20} color={colors.onSurface} />
          </Pressable>
          <Text style={styles.count}>
            Etapa {index + 1} de {STEPS.length}
          </Text>
          <Pressable accessibilityRole="link" onPress={() => router.replace("/(tabs)/profile")} style={styles.exit}>
            <Text style={styles.exitText}>Sair e continuar depois</Text>
          </Pressable>
        </View>

        <View
          style={styles.progress}
          accessible
          accessibilityRole="progressbar"
          accessibilityLabel={`Etapa ${index + 1} de ${STEPS.length}`}
        >
          {STEPS.map((item, position) => {
            const entry = journeySteps.find((candidate) => candidate.key === item.key);
            return (
              <View
                key={item.key}
                style={[
                  styles.segment,
                  (entry?.complete || (item.key === "address" && !needsAddress && position < index)) &&
                    styles.segmentDone,
                  position === index && styles.segmentCurrent,
                ]}
              />
            );
          })}
        </View>

        <Text style={styles.kicker}>CADASTRO DO ESTABELECIMENTO</Text>
        <Text style={styles.title} accessibilityRole="header">{step.title}</Text>
        <Text style={styles.lead}>{step.lead}</Text>

        {stepError ? (
          <View style={styles.alert} accessibilityRole="alert" accessibilityLiveRegion="polite">
            <Icon name="alert-circle" size={18} color={colors.error} />
            <Text style={styles.alertText}>{stepError}</Text>
          </View>
        ) : null}

        <View style={styles.form}>
          {step.key === "basics" ? (
            <>
              {input("Nome do estabelecimento", name, setName, "name", {
                autoCapitalize: "words",
                placeholder: "Ex.: Atelier Lumi",
              })}
              <View style={styles.field}>
                <Text style={styles.label}>Tipo de estabelecimento</Text>
                {radios(TYPES, category, setCategory, "Tipo de estabelecimento")}
                {fieldError("category")}
              </View>
              <View style={styles.row}>
                <View style={styles.rowWide}>
                  {input("Cidade", city, setCity, "city", { autoCapitalize: "words", placeholder: "Ex.: Curitiba" })}
                </View>
                <View style={styles.rowShort}>
                  {input("UF", uf, (text) => setUf(text.toUpperCase()), "uf", {
                    autoCapitalize: "characters",
                    maxLength: 2,
                    placeholder: "PR",
                  })}
                </View>
              </View>
            </>
          ) : null}

          {step.key === "operation" ? (
            <View style={styles.field}>
              {radios(MODES, mode, setMode, "Como o estabelecimento atende?")}
              {fieldError("mode")}
              <Text style={styles.hint}>
                O endereço comercial só é pedido para quem recebe clientes no próprio espaço.
              </Text>
            </View>
          ) : null}

          {step.key === "address" ? (
            <>
              {input("Endereço comercial", address, setAddress, "address", { placeholder: "Rua, número" })}
              {input("Complemento (opcional)", complement, setComplement, "complement", { placeholder: "Sala, andar" })}
              {input("Bairro (opcional)", neighborhood, setNeighborhood, "neighborhood")}
              {input("CEP (opcional)", postalCode, setPostalCode, "postalCode", {
                keyboardType: "number-pad",
                maxLength: 16,
                placeholder: "80000-000",
              })}
              <Text style={styles.hint}>
                Cidade e UF: {city}/{uf}. Para mudar, volte à primeira etapa.
              </Text>
            </>
          ) : null}

          {step.key === "hours" ? (
            <View style={styles.field}>
              {radios(HOURS_MODES, hoursMode, setHoursMode, "Funcionamento")}
              {fieldError("hoursMode")}
              {hoursMode === "fixed_hours" ? (
                <View style={styles.hours}>
                  <Text style={styles.hint}>
                    Preencha abertura e fechamento (HH:MM) dos dias em que atende. Deixe em branco os dias fechados.
                  </Text>
                  {DAYS.map(([day, label]) => (
                    <View key={day} style={styles.hourRow}>
                      <Text style={styles.dayLabel}>{label}</Text>
                      <TextInput
                        value={hours[day]?.start ?? ""}
                        onChangeText={(value) =>
                          setHours((previous) => ({ ...previous, [day]: { start: value, end: previous[day]?.end ?? "" } }))
                        }
                        placeholder="09:00"
                        placeholderTextColor={colors.muted}
                        accessibilityLabel={`Abertura na ${label.toLowerCase()}`}
                        keyboardType="numbers-and-punctuation"
                        maxLength={5}
                        style={[styles.input, styles.hourInput]}
                      />
                      <TextInput
                        value={hours[day]?.end ?? ""}
                        onChangeText={(value) =>
                          setHours((previous) => ({ ...previous, [day]: { start: previous[day]?.start ?? "", end: value } }))
                        }
                        placeholder="18:00"
                        placeholderTextColor={colors.muted}
                        accessibilityLabel={`Fechamento na ${label.toLowerCase()}`}
                        keyboardType="numbers-and-punctuation"
                        maxLength={5}
                        style={[styles.input, styles.hourInput]}
                      />
                    </View>
                  ))}
                </View>
              ) : null}
            </View>
          ) : null}

          {step.key === "contact" ? (
            <>
              <View style={styles.field}>
                <Text style={styles.label}>Apresentação</Text>
                <TextInput
                  value={description}
                  onChangeText={setDescription}
                  multiline
                  maxLength={DESCRIPTION_MAX}
                  accessibilityLabel="Apresentação"
                  accessibilityHint={`Pelo menos ${DESCRIPTION_MIN} caracteres.`}
                  placeholder="Ex.: Studio de unhas no Batel com atendimento com hora marcada, foco em saúde da unha e acabamento."
                  placeholderTextColor={colors.muted}
                  style={[styles.input, styles.textArea, errors.description && styles.inputError]}
                />
                <Text style={styles.hint}>
                  Pelo menos {DESCRIPTION_MIN} caracteres. {description.trim().length} de {DESCRIPTION_MAX} caracteres.
                </Text>
                {fieldError("description")}
              </View>
              {input("Telefone / WhatsApp", phone, setPhone, "phone", {
                keyboardType: "phone-pad",
                autoComplete: "tel",
                placeholder: "(41) 99999-9999",
              })}
              <Pressable
                accessibilityRole="checkbox"
                accessibilityState={{ checked: whatsapp }}
                onPress={() => setWhatsapp((value) => !value)}
                style={styles.toggleRow}
              >
                <View style={[styles.check, whatsapp && styles.checkSelected]}>
                  {whatsapp ? <Icon name="check" size={14} color={colors.onBrandPrimary} /> : null}
                </View>
                <Text style={styles.choiceText}>Mostrar botão do WhatsApp na página</Text>
              </Pressable>
              {input("E-mail comercial", email, setEmail, "email", {
                keyboardType: "email-address",
                autoCapitalize: "none",
                autoComplete: "email",
              })}
              <Text style={styles.hint}>
                Aparece na sua página. Sugerimos o e-mail da sua conta; troque se preferir.
              </Text>
            </>
          ) : null}

          {step.key === "personalize" ? (
            <>
              {(
                [
                  ["logo", "Logo", "Quadrada, até 5 MB", media?.logo?.url],
                  ["cover", "Foto de capa", "Fachada ou ambiente, até 5 MB", media?.cover?.url],
                ] as const
              ).map(([kind, label, help, url]) => (
                <Pressable
                  key={kind}
                  accessibilityRole="button"
                  accessibilityLabel={`${url ? "Trocar" : "Escolher"} ${label.toLowerCase()}`}
                  disabled={mediaBusy !== null}
                  onPress={() => void handleMedia(kind)}
                  style={({ pressed }) => [styles.nextItem, pressed && styles.pressed]}
                >
                  {url ? (
                    <Image source={{ uri: url }} style={kind === "logo" ? styles.thumbSquare : styles.thumbWide} />
                  ) : (
                    <Icon name="image" size={20} color={colors.muted} />
                  )}
                  <View style={styles.nextText}>
                    <Text style={styles.nextTitle}>{label}</Text>
                    <Text style={styles.nextBody}>{mediaBusy === kind ? "Enviando…" : help}</Text>
                  </View>
                  <Text style={styles.linkText}>{url ? "Trocar" : "Escolher"}</Text>
                </Pressable>
              ))}
              <View style={styles.field}>
                <Text style={styles.label}>Fotos do espaço</Text>
                <View style={styles.gallery}>
                  {(media?.gallery ?? []).map((item) => (
                    <View key={item.id} style={styles.galleryItem}>
                      <Image source={{ uri: item.imageUrl }} style={styles.galleryImage} />
                      <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Remover foto"
                        onPress={() => void handleRemoveGallery(item.id)}
                        style={styles.galleryRemove}
                      >
                        <Icon name="x" size={16} color={colors.onSurface} />
                      </Pressable>
                    </View>
                  ))}
                </View>
                <Button
                  title={mediaBusy === "gallery" ? "Enviando…" : "Adicionar foto"}
                  variant="outline"
                  disabled={mediaBusy !== null || (media?.gallery.length ?? 0) >= 10}
                  onPress={() => void handleMedia("gallery")}
                />
                <Text style={styles.hint}>Até 10 fotos. Tudo opcional: dá para publicar sem fotos.</Text>
              </View>
            </>
          ) : null}

          {step.key === "review" ? (
            <>
              {journeySteps
                .filter((item) => item.key !== "personalize" && item.key !== "review" && item.applicable)
                .map((item) => (
                  <View key={item.key} style={styles.reviewItem}>
                    <Icon
                      name={item.complete ? "check-circle" : "alert-circle"}
                      size={20}
                      color={item.complete ? colors.plum : colors.error}
                    />
                    <View style={styles.nextText}>
                      <Text style={styles.nextTitle}>{item.label}</Text>
                      <Text style={styles.nextBody}>{item.complete ? "Pronto" : "Falta preencher"}</Text>
                    </View>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`${item.complete ? "Editar" : "Completar"} ${item.label}`}
                      onPress={() => goTo(stepIndex(item.key), true)}
                      style={styles.reviewLink}
                    >
                      <Text style={styles.linkText}>{item.complete ? "Editar" : "Completar"}</Text>
                    </Pressable>
                  </View>
                ))}
              {missing.length > 0 ? (
                <View style={styles.pending}>
                  <Text style={styles.pendingTitle}>Para publicar, falta:</Text>
                  {missing.map((item) => (
                    <Text key={item.key} style={styles.pendingText}>
                      • {item.message}
                    </Text>
                  ))}
                </View>
              ) : (
                <Text style={styles.hint}>
                  Tudo pronto. Logo, capa, fotos, equipe e serviços podem ser organizados depois.
                </Text>
              )}
            </>
          ) : null}
        </View>

        <View style={styles.actions}>
          {step.key === "review" ? (
            <Button
              title="Publicar página"
              fullWidth
              loading={saving}
              disabled={!draft || missing.length > 0}
              onPress={() => void handlePublish()}
            />
          ) : step.key === "personalize" ? (
            <Button title="Continuar" fullWidth onPress={() => goTo(STEPS.length - 1)} />
          ) : (
            <Button title="Continuar" fullWidth loading={saving} onPress={() => void handleContinue()} />
          )}
          {returnToReview && step.key !== "review" ? (
            <Button title="Voltar para a revisão" variant="ghost" fullWidth onPress={() => goTo(STEPS.length - 1)} />
          ) : null}
        </View>
      </ScrollView>
    </View>
  );
}
