// Cadastro profissional por etapas (PR 2 do onboarding V0).
// Mesma ordem, mesmas mensagens e mesmas regras do Web: cada etapa é salva
// no servidor (PATCH), a etapa atual vem da API (journey.currentStep) e a
// publicação é explícita (F1). Áreas fixas (D-ONB-01), apresentação com
// 40+ caracteres (D-ONB-02), tema opcional com padrão Beleza (D-ONB-03).
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { useRouter } from "expo-router";

import { ApiError } from "@/api/client";
import {
  type MissingRequirement,
  type ProfessionalDraftPatch,
  type ProfessionalOnboardingProfile,
  getProfessionalOnboarding,
  patchProfessionalDraft,
  publishProfessionalProfile,
} from "@/api/onboarding";
import { Button } from "@/components/Button";
import { useOnboardingStyles } from "@/components/onboarding/onboardingStyles";
import { Icon } from "@/components/Icon";
import { store } from "@/store/local";
import { useTheme } from "@/theme";

type StepKey =
  | "identity"
  | "location"
  | "specialty"
  | "modality"
  | "presentation"
  | "personalize"
  | "review";

const STEPS: { key: StepKey; title: string; lead: string }[] = [
  {
    key: "identity",
    title: "Como as pessoas vão te chamar?",
    lead: "Use o nome que seus clientes já conhecem. Ele aparece no seu perfil público.",
  },
  {
    key: "location",
    title: "Onde você atende?",
    lead: "Cidade e UF ajudam clientes da sua região a encontrar você.",
  },
  {
    key: "specialty",
    title: "Qual é a sua especialidade?",
    lead: "Diga o que você faz de melhor e escolha as áreas em que atua.",
  },
  {
    key: "modality",
    title: "Como você atende?",
    lead: "Escolha uma ou mais formas. O endereço do cliente nunca aparece no seu perfil.",
  },
  {
    key: "presentation",
    title: "Conte quem você é.",
    lead: "Fale da sua técnica, da sua experiência e do resultado que gosta de entregar.",
  },
  {
    key: "personalize",
    title: "Deixe o perfil com a sua cara",
    lead: "Tudo nesta etapa é opcional. Dá para fazer agora ou depois, em Editar perfil.",
  },
  {
    key: "review",
    title: "Revise e publique seu perfil",
    lead: "Publicar coloca seu perfil no ar. Receber reservas depende de serviços e horários, que você cria depois.",
  },
];

// D-ONB-01: a mesma lista do Web e da API.
const AREAS: [string, string][] = [
  ["cabelo", "Cabelo"],
  ["unhas", "Unhas"],
  ["barbearia", "Barbearia"],
  ["estetica", "Estética"],
  ["maquiagem", "Maquiagem"],
  ["sobrancelhas", "Sobrancelhas"],
  ["tatuagem", "Tatuagem"],
  ["massagem", "Massagem"],
];

const MODALITIES: [string, string][] = [
  ["establishment", "Em estabelecimento"],
  ["own_space", "Em espaço próprio"],
  ["client_location", "No endereço do cliente"],
];

const THEMES: ["beauty" | "barber" | "tattoo", string][] = [
  ["beauty", "Beleza"],
  ["barber", "Barbearia"],
  ["tattoo", "Tatuagem"],
];

const BIO_MIN = 40;
const BIO_MAX = 2000;

type FieldErrors = Partial<Record<string, string>>;

function stepIndex(key: string | undefined) {
  const index = STEPS.findIndex((step) => step.key === key);
  return index === -1 ? 0 : index;
}

export default function ProOnboardingScreen() {
  const styles = useOnboardingStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [locked, setLocked] = useState(false);
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);
  const [profile, setProfile] = useState<ProfessionalOnboardingProfile | null>(null);
  const [index, setIndex] = useState(0);
  const [returnToReview, setReturnToReview] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [stepError, setStepError] = useState("");
  const [missing, setMissing] = useState<MissingRequirement[]>([]);

  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [uf, setUf] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [areas, setAreas] = useState<string[]>([]);
  const [modalities, setModalities] = useState<string[]>([]);
  const [bio, setBio] = useState("");
  const [headline, setHeadline] = useState("");
  const [phone, setPhone] = useState("");
  const [whatsapp, setWhatsapp] = useState(true);
  const [instagram, setInstagram] = useState("");
  const [theme, setTheme] = useState<"beauty" | "barber" | "tattoo">("beauty");

  const hydrate = useCallback((item: ProfessionalOnboardingProfile) => {
    setProfile(item);
    setName(item.displayName);
    setCity(item.city);
    setUf(item.state);
    setSpecialty(item.primarySpecialty ?? "");
    setAreas(item.categories);
    setModalities(item.attendanceModalities ?? []);
    setBio(item.bio);
    setHeadline(item.headline ?? "");
    setPhone(item.phone);
    setWhatsapp(item.whatsappEnabled ?? true);
    setInstagram(item.instagram ?? "");
    setTheme(item.visualTheme ?? "beauty");
    setMissing(item.journey?.missingRequirements ?? []);
  }, []);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const response = await getProfessionalOnboarding();
        if (!mounted) return;
        if (response.profile?.isActive) {
          // Perfil no ar não refaz o cadastro: segue para o perfil.
          router.replace("/professional-onboarding");
          return;
        }
        if (response.profile?.publishedAt) {
          setLocked(true);
          return;
        }
        if (response.profile) {
          hydrate(response.profile);
          setIndex(stepIndex(response.profile.journey?.currentStep));
        } else {
          setName(store.getUser()?.name ?? "");
        }
      } catch {
        if (mounted) {
          setStepError("Não foi possível carregar seu cadastro. Verifique a conexão e tente de novo.");
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void load();
    return () => {
      mounted = false;
    };
  }, [hydrate, router]);

  const step = STEPS[index];

  const goTo = (next: number, fromReview = false) => {
    setErrors({});
    setStepError("");
    setReturnToReview(fromReview);
    setIndex(next);
  };

  const goBack = () => {
    if (index === 0) {
      if (router.canGoBack()) router.back();
      else router.replace("/(tabs)/profile");
      return;
    }
    goTo(index - 1);
  };

  // Mesmas mensagens do formulário Web.
  const validate = (): { changes: ProfessionalDraftPatch; found: FieldErrors } => {
    const found: FieldErrors = {};
    const changes: ProfessionalDraftPatch = {};
    switch (step.key) {
      case "identity":
        if (name.trim().length < 2) found.name = "Informe seu nome profissional.";
        changes.displayName = name.trim();
        break;
      case "location":
        if (city.trim().length < 2) found.city = "Informe a cidade onde você atende.";
        if (!/^[A-Za-z]{2}$/.test(uf.trim())) found.uf = "Use as duas letras da UF.";
        changes.city = city.trim();
        changes.state = uf.trim().toUpperCase();
        break;
      case "specialty":
        if (specialty.trim().length < 2) found.specialty = "Informe sua especialidade principal.";
        if (areas.length === 0) found.areas = "Escolha pelo menos uma área de atuação.";
        changes.primarySpecialty = specialty.trim();
        changes.categories = areas;
        break;
      case "modality":
        if (modalities.length === 0) found.modalities = "Selecione pelo menos uma modalidade de atendimento.";
        changes.attendanceModalities = modalities;
        break;
      case "presentation": {
        const length = bio.trim().length;
        if (!length) found.bio = "Escreva sua apresentação.";
        else if (length < BIO_MIN || length > BIO_MAX) found.bio = `Use entre ${BIO_MIN} e ${BIO_MAX} caracteres.`;
        changes.bio = bio.trim();
        changes.headline = headline.trim() || null;
        break;
      }
      case "personalize":
        changes.phone = phone.trim() || null;
        changes.whatsappEnabled = Boolean(whatsapp && phone.trim());
        changes.instagram = instagram.trim() || null;
        changes.visualTheme = theme;
        break;
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
      const response = await patchProfessionalDraft(changes);
      if (response.profile) hydrate(response.profile);
      goTo(returnToReview ? STEPS.length - 1 : index + 1);
    } catch (error) {
      setStepError(error instanceof Error ? error.message : "Não foi possível salvar. Tente novamente.");
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    setStepError("");
    try {
      setSaving(true);
      const response = await publishProfessionalProfile();
      if (response.profile) setProfile(response.profile);
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

  const toggle = (list: string[], value: string, setter: (next: string[]) => void) => {
    setter(list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);
  };

  const renderChoices = (
    options: [string, string][],
    selected: string[],
    onToggle: (value: string) => void,
    label: string,
  ) => (
    <View style={styles.choices} accessibilityLabel={label}>
      {options.map(([value, text]) => {
        const checked = selected.includes(value);
        return (
          <Pressable
            key={value}
            accessibilityRole="checkbox"
            accessibilityState={{ checked }}
            accessibilityLabel={text}
            onPress={() => onToggle(value)}
            style={({ pressed }) => [styles.choice, checked && styles.choiceSelected, pressed && styles.pressed]}
          >
            <Text style={[styles.choiceText, checked && styles.choiceTextSelected]}>{text}</Text>
            <View style={[styles.check, checked && styles.checkSelected]}>
              {checked ? <Icon name="check" size={14} color={colors.onBrandPrimary} /> : null}
            </View>
          </Pressable>
        );
      })}
    </View>
  );

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

  if (loading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator color={colors.plum} />
      </View>
    );
  }

  if (locked) {
    // Desativado pela moderação (publishedAt sem isActive): mesma regra do
    // servidor, que recusa a publicação com publication_locked.
    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content}>
          <Text style={styles.kicker}>CADASTRO PROFISSIONAL</Text>
          <Text style={styles.title} accessibilityRole="header">Este perfil foi desativado.</Text>
          <Text style={styles.lead}>Não é possível publicar por aqui. Fale com o suporte do IDDUN.</Text>
          <View style={styles.actions}>
            <Button title="Voltar ao perfil" fullWidth onPress={() => router.replace("/(tabs)/profile")} />
          </View>
        </ScrollView>
      </View>
    );
  }

  if (done && profile) {
    return (
      <View style={styles.container}>
        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.doneMark}>
            <Icon name="check" size={24} color={colors.onBrandPrimary} />
          </View>
          <Text style={styles.kicker}>CADASTRO PROFISSIONAL</Text>
          <Text style={styles.title} accessibilityRole="header">Seu perfil está no ar.</Text>
          <Text style={styles.lead}>
            Clientes já podem encontrar {profile.displayName} no IDDUN. Reservas ainda não estão
            abertas: elas começam quando você tiver um serviço publicado com horários disponíveis.
          </Text>
          <Text style={styles.subtitle}>Próximos passos</Text>
          {[
            ["Criar um serviço", "Nome, duração e preço do que você oferece.", "/create-service"],
            ["Abrir horários", "Defina quando você atende para receber reservas.", "/weekly-schedule"],
            ["Mostrar seus trabalhos", "Fotos do portfólio ajudam clientes a escolher você.", "/professional-onboarding"],
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

  const journeySteps = profile?.journey?.steps ?? [];

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
          <Text style={styles.count}>Etapa {index + 1} de {STEPS.length}</Text>
          <Pressable
            accessibilityRole="link"
            onPress={() => router.replace("/(tabs)/profile")}
            style={styles.exit}
          >
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
            const complete = journeySteps.find((entry) => entry.key === item.key)?.complete;
            return (
              <View
                key={item.key}
                style={[
                  styles.segment,
                  complete && styles.segmentDone,
                  position === index && styles.segmentCurrent,
                ]}
              />
            );
          })}
        </View>

        <Text style={styles.kicker}>CADASTRO PROFISSIONAL</Text>
        <Text style={styles.title} accessibilityRole="header">{step.title}</Text>
        <Text style={styles.lead}>{step.lead}</Text>

        {stepError ? (
          <View style={styles.alert} accessibilityRole="alert" accessibilityLiveRegion="polite">
            <Icon name="alert-circle" size={18} color={colors.error} />
            <Text style={styles.alertText}>{stepError}</Text>
          </View>
        ) : null}

        <View style={styles.form}>
          {step.key === "identity"
            ? input("Nome profissional", name, setName, "name", { autoCapitalize: "words", autoComplete: "name" })
            : null}

          {step.key === "location" ? (
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
          ) : null}

          {step.key === "specialty" ? (
            <>
              {input("Especialidade principal", specialty, setSpecialty, "specialty", {
                placeholder: "Ex.: Nail designer, colorista, barbeiro",
              })}
              <View style={styles.field}>
                <Text style={styles.label}>Áreas de atuação</Text>
                <Text style={styles.hint}>Escolha uma ou mais.</Text>
                {renderChoices(AREAS, areas, (value) => toggle(areas, value, setAreas), "Áreas de atuação")}
                {fieldError("areas")}
              </View>
            </>
          ) : null}

          {step.key === "modality" ? (
            <View style={styles.field}>
              {renderChoices(
                MODALITIES,
                modalities,
                (value) => toggle(modalities, value, setModalities),
                "Como você atende?",
              )}
              {fieldError("modalities")}
            </View>
          ) : null}

          {step.key === "presentation" ? (
            <>
              <View style={styles.field}>
                <Text style={styles.label}>Apresentação</Text>
                <TextInput
                  value={bio}
                  onChangeText={setBio}
                  multiline
                  maxLength={BIO_MAX}
                  accessibilityLabel="Apresentação"
                  accessibilityHint={`Pelo menos ${BIO_MIN} caracteres.`}
                  placeholder="Ex.: Trabalho com unhas naturais e alongamento em gel há 6 anos. Cuido da saúde da unha e do acabamento."
                  placeholderTextColor={colors.muted}
                  style={[styles.input, styles.textArea, errors.bio && styles.inputError]}
                />
                <Text style={styles.hint}>
                  Pelo menos {BIO_MIN} caracteres. {bio.trim().length} de {BIO_MAX} caracteres.
                </Text>
                {fieldError("bio")}
              </View>
              {input("Chamada (opcional)", headline, setHeadline, "headline", {
                placeholder: "Ex.: Especialista em loiros e transformações",
              })}
            </>
          ) : null}

          {step.key === "personalize" ? (
            <>
              <Pressable
                accessibilityRole="button"
                onPress={() => router.push("/professional-onboarding")}
                style={({ pressed }) => [styles.nextItem, pressed && styles.pressed]}
              >
                <View style={styles.nextText}>
                  <Text style={styles.nextTitle}>Foto, capa e portfólio</Text>
                  <Text style={styles.nextBody}>Abrir o editor de fotos. Seu cadastro continua salvo.</Text>
                </View>
                <Icon name="chevron-right" size={18} color={colors.muted} />
              </Pressable>
              {input("WhatsApp / telefone", phone, setPhone, "phone", {
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
                <Text style={styles.choiceText}>Mostrar botão do WhatsApp no meu perfil</Text>
              </Pressable>
              {input("Instagram", instagram, setInstagram, "instagram", {
                autoCapitalize: "none",
                placeholder: "@seuperfil",
              })}
              <View style={styles.field}>
                <Text style={styles.label}>Universo visual</Text>
                <Text style={styles.hint}>Muda a atmosfera do seu perfil. Se não escolher, fica Beleza.</Text>
                {renderChoices(THEMES, [theme], (value) => setTheme(value as typeof theme), "Universo visual")}
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
                    <Text key={item.key} style={styles.pendingText}>• {item.message}</Text>
                  ))}
                </View>
              ) : (
                <Text style={styles.hint}>
                  Tudo pronto. Fotos, portfólio e contatos podem ser completados depois, em Editar perfil.
                </Text>
              )}
            </>
          ) : null}
        </View>

        <View style={styles.actions}>
          {step.key === "review" ? (
            <Button
              title="Publicar perfil"
              fullWidth
              loading={saving}
              disabled={!profile || missing.length > 0}
              onPress={() => void handlePublish()}
            />
          ) : (
            <Button
              title={step.key === "personalize" ? "Salvar e continuar" : "Continuar"}
              fullWidth
              loading={saving}
              onPress={() => void handleContinue()}
            />
          )}
          {returnToReview && step.key !== "review" ? (
            <Button title="Voltar para a revisão" variant="ghost" fullWidth onPress={() => goTo(STEPS.length - 1)} />
          ) : step.key === "personalize" ? (
            <Button title="Fazer depois" variant="ghost" fullWidth onPress={() => goTo(STEPS.length - 1)} />
          ) : null}
        </View>
      </ScrollView>
    </View>
  );
}
