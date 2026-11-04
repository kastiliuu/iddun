import React, { useState } from "react";
import {
  Linking,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import type {
  ProfileCertification,
  ProfileExperience,
  ProfilePlace,
  ProfileReview,
} from "@/api/professionals";
import type { EstablishmentAbout } from "@/api/establishments";
import { API_URL } from "@/api/client";
import { Avatar } from "@/components/Avatar";
import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  typography,
  useTheme,
} from "@/theme";

/**
 * Seções dos perfis públicos no app (PR 4a; D-SOC-12): mesma ordem, mesmos
 * rótulos e mesmos dados do Web. Sem dado, um aviso honesto — nada
 * inventado (avaliação só de atendimento concluído).
 */

const READ_MORE_LIMIT = 280;

export type SectionEdit = {
  /** Texto visível; padrão "Editar". */
  label?: string;
  onPress: () => void;
};

/**
 * Editor da Web na seção certa (PR 4b; D-SOC-15). Usado quando o app ainda
 * não tem editor para aquela parte do perfil.
 */
export function openWebEditor(path: string) {
  void Linking.openURL(`${API_URL}${path}`);
}

export function ProfileSection({
  kicker,
  title,
  children,
  action,
  edit,
}: {
  kicker: string;
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  /** Modo dono: atalho para editar esta seção (só para quem é dono). */
  edit?: SectionEdit | SectionEdit[];
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  const edits = edit ? (Array.isArray(edit) ? edit : [edit]) : [];

  return (
    <View style={styles.section}>
      {edits.length > 0 ? (
        <View style={styles.editRow}>
          {edits.map((item) => {
            const label = item.label ?? "Editar";
            return (
              <Pressable
                key={label}
                accessibilityRole="button"
                accessibilityLabel={`${label}: ${title}`}
                onPress={item.onPress}
                style={({ pressed }) => [styles.editLink, pressed && styles.pressed]}
              >
                <Icon name="edit-2" size={14} color={colors.onSurfaceSecondary} />
                <Text style={styles.editLinkText}>{label}</Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}
      <View style={styles.sectionHead}>
        <View style={styles.sectionTitles}>
          <Text style={styles.kicker}>{kicker}</Text>
          <Text style={styles.title} accessibilityRole="header">
            {title}
          </Text>
        </View>
        {action}
      </View>
      {children}
    </View>
  );
}

/** Aviso do modo dono, com o atalho principal de edição. */
export function OwnerBanner({
  message,
  actionLabel,
  onPress,
}: {
  message: string;
  actionLabel: string;
  onPress: () => void;
}) {
  const styles = useStyles();
  const { colors } = useTheme();

  return (
    <View style={styles.ownerBanner} accessibilityRole="summary">
      <View style={styles.inlineRow}>
        <Icon name="user" size={14} color={colors.onSurfaceSecondary} />
        <Text style={styles.ownerText}>{message}</Text>
      </View>
      <Pressable
        accessibilityRole="button"
        onPress={onPress}
        style={({ pressed }) => [styles.outlineButton, pressed && styles.pressed]}
      >
        <Icon name="edit-2" size={16} color={colors.onSurface} />
        <Text style={styles.outlineButtonText}>{actionLabel}</Text>
      </Pressable>
    </View>
  );
}

export function Placeholder({ children }: { children: string }) {
  const styles = useStyles();
  return <Text style={styles.placeholder}>{children}</Text>;
}

/** "Sobre" curto, com Ler mais acima de 280 caracteres. */
export function ReadMoreText({ text }: { text: string }) {
  const styles = useStyles();
  const [open, setOpen] = useState(false);
  const long = text.length > READ_MORE_LIMIT;
  const shown = long && !open ? `${text.slice(0, READ_MORE_LIMIT).trim()}…` : text;

  return (
    <View>
      <Text style={styles.body}>{shown}</Text>
      {long ? (
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ expanded: open }}
          onPress={() => setOpen((value) => !value)}
          style={styles.inlineButton}
        >
          <Text style={styles.inlineButtonText}>{open ? "Ler menos" : "Ler mais"}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export function SectionLink({
  label,
  onPress,
  accessibilityLabel,
}: {
  label: string;
  onPress: () => void;
  accessibilityLabel?: string;
}) {
  const styles = useStyles();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      onPress={onPress}
      style={styles.inlineButton}
    >
      <Text style={styles.inlineButtonText}>{label}</Text>
    </Pressable>
  );
}

export function PortfolioStrip({
  items,
  ownerName,
}: {
  items: { url: string | null; caption: string | null }[];
  ownerName: string;
}) {
  const styles = useStyles();
  const visible = items.filter((item) => item.url);

  if (visible.length === 0) {
    return <Placeholder>O portfólio deste perfil será publicado em breve.</Placeholder>;
  }

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.portfolio}
      accessibilityLabel={`Galeria de trabalhos de ${ownerName}`}
    >
      {visible.map((item, index) => (
        <View key={`${item.url}-${index}`} style={styles.portfolioItem}>
          <Image
            source={{ uri: item.url as string }}
            style={styles.portfolioImage}
            contentFit="cover"
            accessibilityLabel={`Trabalho ${index + 1} de ${ownerName}`}
          />
          {item.caption ? (
            <Text style={styles.caption} numberOfLines={2}>
              {item.caption}
            </Text>
          ) : null}
        </View>
      ))}
    </ScrollView>
  );
}

function Badge({ verified, label }: { verified?: boolean; label: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={[styles.badge, verified && styles.badgeVerified]}>
      {verified ? <Icon name="shield" size={12} color={colors.onBrandTertiary} /> : null}
      <Text style={[styles.badgeText, verified && styles.badgeTextVerified]}>{label}</Text>
    </View>
  );
}

function Entry({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: "briefcase" | "award";
  title: string;
  subtitle?: string | null;
  children?: React.ReactNode;
}) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <View style={styles.entry}>
      <View style={styles.entryIcon}>
        <Icon name={icon} size={16} color={colors.onSurface} />
      </View>
      <View style={styles.entryBody}>
        <Text style={styles.entryTitle}>{title}</Text>
        {subtitle ? <Text style={styles.meta}>{subtitle}</Text> : null}
        {children}
      </View>
    </View>
  );
}

export function ExperienceAndTraining({
  experiences,
  certifications,
}: {
  experiences: ProfileExperience[];
  certifications: ProfileCertification[];
}) {
  const styles = useStyles();

  return (
    <View style={styles.stack}>
      {experiences.length > 0 ? (
        <>
          <Text style={styles.subhead}>Experiência profissional</Text>
          {experiences.map((item) => {
            const end = item.current ? "atual" : item.endYear ? String(item.endYear) : "";
            const period = item.startYear ? ` · ${item.startYear} — ${end}` : "";
            return (
              <Entry key={item.id} icon="briefcase" title={item.role} subtitle={`${item.company}${period}`}>
                {item.description ? <Text style={styles.body}>{item.description}</Text> : null}
                {/* D-SOC-12: declarado ≠ verificado. */}
                <Badge
                  verified={item.verified}
                  label={item.verified ? "Vínculo verificado no IDDUN" : "Declarado pelo profissional"}
                />
              </Entry>
            );
          })}
        </>
      ) : null}

      <Text style={styles.subhead}>Formação e certificações</Text>
      {certifications.length > 0 ? (
        certifications.map((item) => (
          <Entry
            key={item.id}
            icon="award"
            title={item.title}
            subtitle={[item.issuer, item.year].filter(Boolean).join(" · ") || null}
          >
            {item.credentialId ? <Text style={styles.meta}>{`Credencial ${item.credentialId}`}</Text> : null}
            <Badge label="Declarado pelo profissional" />
            {item.verificationUrl ? (
              <SectionLink
                label="Verificar"
                accessibilityLabel={`Verificar certificado ${item.title}`}
                onPress={() => void Linking.openURL(item.verificationUrl as string)}
              />
            ) : null}
          </Entry>
        ))
      ) : (
        <Placeholder>Este profissional ainda não publicou certificações.</Placeholder>
      )}
    </View>
  );
}

export function ReviewSummary({
  rating,
  count,
  label,
}: {
  rating: number;
  count: number;
  label?: string | null;
}) {
  const styles = useStyles();
  if (!count) {
    return null;
  }
  return (
    <View style={styles.score} accessible accessibilityLabel={`Nota ${rating.toFixed(1)}, ${label ?? ""}`}>
      <Text style={styles.scoreValue}>{`${rating.toFixed(1)} ★`}</Text>
      {label ? <Text style={styles.meta}>{label}</Text> : null}
    </View>
  );
}

export function ReviewList({
  reviews,
  subject,
  emptyText,
}: {
  reviews: ProfileReview[];
  subject: "profissional" | "estabelecimento";
  emptyText: string;
}) {
  const styles = useStyles();
  const { colors } = useTheme();

  if (reviews.length === 0) {
    return <Placeholder>{emptyText}</Placeholder>;
  }

  return (
    <View style={styles.stack}>
      {reviews.map((review) => (
        <View key={review.id} style={styles.review}>
          <View style={styles.reviewHead}>
            <Text style={styles.entryTitle}>{review.author}</Text>
            <Text style={styles.stars} accessibilityLabel={`${review.rating} de 5 estrelas`}>
              {"★".repeat(review.rating)}
            </Text>
          </View>
          <View style={styles.inlineRow}>
            <Icon name="shield" size={12} color={colors.muted} />
            <Text style={styles.meta}>Atendimento verificado</Text>
          </View>
          {review.comment ? <Text style={styles.body}>{`“${review.comment}”`}</Text> : null}
          <Text style={styles.meta}>
            {review.recommended ? `✓ Recomenda este ${subject}` : "Avaliação sem recomendação"}
          </Text>
        </View>
      ))}
    </View>
  );
}

export function PlaceList({ places }: { places: ProfilePlace[] }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  if (places.length === 0) {
    return <Placeholder>Atendimento independente ou local ainda não informado.</Placeholder>;
  }

  return (
    <View style={styles.stack}>
      {places.map((place) => (
        <Pressable
          key={place.id}
          accessibilityRole="link"
          accessibilityLabel={`Abrir ${place.name}`}
          onPress={() => router.push(`/establishment/${place.routeId}`)}
          style={({ pressed }) => [styles.place, pressed && styles.pressed]}
        >
          <Avatar name={place.name} uri={place.logo} size={40} />
          <View style={styles.entryBody}>
            <Text style={styles.entryTitle}>{place.name}</Text>
            {place.subtitle ? <Text style={styles.meta}>{place.subtitle}</Text> : null}
          </View>
          <Icon name="chevron-right" size={18} color={colors.muted} />
        </Pressable>
      ))}
    </View>
  );
}

export function WhatsAppButton({ url, label = "WhatsApp" }: { url: string; label?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={label}
      onPress={() => void Linking.openURL(url)}
      style={({ pressed }) => [styles.outlineButton, pressed && styles.pressed]}
    >
      <Icon name="message-circle" size={16} color={colors.onSurface} />
      <Text style={styles.outlineButtonText}>{label}</Text>
    </Pressable>
  );
}

/** Aba Sobre da empresa: funcionamento, contatos e localização. */
export function BusinessAbout({
  about,
  editSlug,
}: {
  about?: EstablishmentAbout;
  /** Modo dono (D-SOC-15/16): slug para abrir o editor da Web na seção. */
  editSlug?: string | null;
}) {
  const web = (anchor: string, label?: string) =>
    editSlug
      ? { label, onPress: () => openWebEditor(`/business/${editSlug}/editar#${anchor}`) }
      : undefined;
  const styles = useStyles();

  const hasOperation = Boolean(about?.operationLabel || about?.hours);
  const hasContacts = Boolean(about?.whatsappUrl || about?.instagram);

  return (
    <View style={styles.stack}>
      <ProfileSection
        kicker="FUNCIONAMENTO"
        title="Como atende"
        edit={
          editSlug
            ? [web("atendimento", "Editar modalidade")!, web("funcionamento", "Editar horários")!]
            : undefined
        }
      >
        {hasOperation ? (
          <View style={styles.stack}>
            {about?.operationLabel ? (
              <View>
                <Text style={styles.meta}>Modalidade</Text>
                <Text style={styles.body}>{about.operationLabel}</Text>
              </View>
            ) : null}
            {about?.hours ? (
              <View>
                <Text style={styles.meta}>Funcionamento</Text>
                <Text style={styles.body}>{about.hours.label}</Text>
              </View>
            ) : null}
            {about?.hours?.days.length ? (
              <View accessibilityLabel="Horários de funcionamento">
                {about.hours.days.map((day) => (
                  <View key={day.label} style={styles.hoursRow}>
                    <Text style={styles.entryTitle}>{day.label}</Text>
                    <Text style={styles.body}>{day.ranges.length ? day.ranges.join(", ") : "Fechado"}</Text>
                  </View>
                ))}
              </View>
            ) : null}
          </View>
        ) : (
          <Placeholder>A empresa ainda não informou como atende.</Placeholder>
        )}
      </ProfileSection>

      <ProfileSection kicker="CONTATOS" title="Fale com a empresa" edit={web("contatos")}>
        {hasContacts ? (
          <View style={styles.stack}>
            {about?.whatsappUrl ? <WhatsAppButton url={about.whatsappUrl} /> : null}
            {about?.instagram ? <Text style={styles.body}>{`Instagram · ${about.instagram}`}</Text> : null}
          </View>
        ) : (
          <Placeholder>A empresa ainda não informou contatos públicos.</Placeholder>
        )}
      </ProfileSection>

      <ProfileSection kicker="LOCALIZAÇÃO" title={about?.city ?? "Localização"} edit={web("localizacao")}>
        {about?.address || about?.city ? (
          <Text style={styles.body}>{[about?.address, about?.city].filter(Boolean).join("\n")}</Text>
        ) : (
          <Placeholder>Endereço ainda não informado.</Placeholder>
        )}
      </ProfileSection>
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  section: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
    gap: spacing.md,
  },
  editRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: spacing.md,
  },
  editLink: {
    minHeight: touch.minimum,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  editLinkText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
    textDecorationLine: "underline",
  },
  ownerBanner: {
    marginHorizontal: spacing.lg,
    marginTop: spacing.lg,
    padding: spacing.md,
    gap: spacing.md,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surfaceSecondary,
  },
  ownerText: {
    flex: 1,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: typography.bodySmall,
  },
  sectionHead: {
    flexDirection: "row",
    alignItems: "flex-end",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  sectionTitles: {
    flex: 1,
    gap: spacing.xs,
  },
  kicker: {
    color: colors.muted,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.caption,
    letterSpacing: 1.2,
  },
  title: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: typography.titleSmall,
  },
  subhead: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.body,
  },
  body: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.body,
    lineHeight: 21,
  },
  meta: {
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: typography.small,
  },
  placeholder: {
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: typography.bodySmall,
    padding: spacing.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  inlineButton: {
    alignSelf: "flex-start",
    minHeight: touch.minimum,
    justifyContent: "center",
  },
  inlineButtonText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
    textDecorationLine: "underline",
  },
  portfolio: {
    gap: spacing.md,
  },
  portfolioItem: {
    width: 220,
    gap: spacing.xs,
  },
  portfolioImage: {
    width: 220,
    height: 280,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
  },
  caption: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: typography.small,
  },
  stack: {
    gap: spacing.md,
  },
  entry: {
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
  },
  entryIcon: {
    width: 32,
    height: 32,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surfaceTertiary,
  },
  entryBody: {
    flex: 1,
    gap: spacing.xs,
  },
  entryTitle: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.body,
  },
  badge: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
  },
  badgeVerified: {
    borderColor: colors.brandTertiary,
    backgroundColor: colors.brandTertiary,
  },
  badgeText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: typography.caption,
  },
  badgeTextVerified: {
    color: colors.onBrandTertiary,
  },
  score: {
    alignItems: "flex-end",
  },
  scoreValue: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: typography.titleSmall,
  },
  review: {
    gap: spacing.xs,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
  },
  reviewHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  stars: {
    color: colors.warning,
    fontSize: typography.bodySmall,
  },
  inlineRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  place: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    minHeight: touch.minimum,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
  },
  pressed: {
    opacity: 0.8,
  },
  outlineButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    minHeight: touch.minimum,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
  },
  outlineButtonText: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: typography.bodySmall,
  },
  hoursRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.divider,
  },
}));
