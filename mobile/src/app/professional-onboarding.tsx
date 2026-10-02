import React, {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  useRouter,
} from "expo-router";

import {
  ApiError,
} from "@/api/client";

import {
  addProfessionalExperience,
  getProfessionalOnboarding,
  ProfessionalOnboardingProfile,
  publishProfessionalProfile,
  removeProfessionalExperience,
} from "@/api/onboarding";

import {
  Button,
} from "@/components/Button";

import {
  Icon,
} from "@/components/Icon";

import {
  useToast,
} from "@/components/Toast";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";


export default function ProfessionalOnboardingScreen() {
  const styles =
    useStyles();

  const { colors } =
    useTheme();

  const router =
    useRouter();

  const toast =
    useToast();

  const [
    profile,
    setProfile,
  ] =
    useState<ProfessionalOnboardingProfile | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  const [
    savingExperience,
    setSavingExperience,
  ] =
    useState(false);

  const [
    publishing,
    setPublishing,
  ] =
    useState(false);

  const [
    companyName,
    setCompanyName,
  ] =
    useState("");

  const [
    roleTitle,
    setRoleTitle,
  ] =
    useState("");

  const [
    description,
    setDescription,
  ] =
    useState("");

  const [
    startedAt,
    setStartedAt,
  ] =
    useState("");

  const [
    endedAt,
    setEndedAt,
  ] =
    useState("");

  const [
    isCurrent,
    setIsCurrent,
  ] =
    useState(false);

  const load =
    useCallback(
      async () => {
        try {
          setLoading(true);

          const response =
            await getProfessionalOnboarding();

          setProfile(
            response.profile,
          );
        } catch (error) {
          toast.show({
            title:
              "Não foi possível carregar",
            body:
              error instanceof Error
                ? error.message
                : "Tente novamente.",
            icon:
              "alert-circle",
          });
        } finally {
          setLoading(false);
        }
      },
      [toast],
    );

  useEffect(
    () => {
      void load();
    },
    [load],
  );

  const handleAddExperience =
    async () => {
      if (
        !companyName.trim() ||
        !roleTitle.trim() ||
        !startedAt.trim()
      ) {
        toast.show({
          title:
            "Complete a experiência",
          body:
            "Informe empresa, função e data de início.",
          icon:
            "alert-circle",
        });
        return;
      }

      try {
        setSavingExperience(
          true,
        );

        await addProfessionalExperience({
          companyName:
            companyName.trim(),
          roleTitle:
            roleTitle.trim(),
          description:
            description.trim(),
          startedAt:
            startedAt.trim(),
          endedAt:
            isCurrent
              ? null
              : endedAt.trim() ||
                null,
          isCurrent,
        });

        setCompanyName("");
        setRoleTitle("");
        setDescription("");
        setStartedAt("");
        setEndedAt("");
        setIsCurrent(false);

        await load();

        toast.show({
          title:
            "Experiência adicionada",
          body:
            "Seu histórico profissional ficou mais completo.",
          icon:
            "check",
        });
      } catch (error) {
        toast.show({
          title:
            "Não foi possível salvar",
          body:
            error instanceof Error
              ? error.message
              : "Confira os dados e tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setSavingExperience(
          false,
        );
      }
    };

  const handleRemoveExperience =
    async (
      experienceId: number,
    ) => {
      try {
        await removeProfessionalExperience(
          experienceId,
        );
        await load();

        toast.show({
          title:
            "Experiência removida",
          icon:
            "check",
        });
      } catch (error) {
        toast.show({
          title:
            "Não foi possível remover",
          body:
            error instanceof Error
              ? error.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      }
    };

  const handlePublish =
    async () => {
      try {
        setPublishing(true);

        const response =
          await publishProfessionalProfile();

        setProfile(
          response.profile,
        );

        toast.show({
          title:
            "Perfil publicado",
          body:
            "Seu perfil profissional agora pode aparecer publicamente no IDDUN.",
          icon:
            "check",
        });

        router.replace(
          "/(tabs)/profile",
        );
      } catch (error) {
        let body =
          error instanceof Error
            ? error.message
            : "Complete os itens pendentes.";

        if (
          error instanceof ApiError &&
          error.code ===
            "profile_incomplete"
        ) {
          body =
            "Seu rascunho está salvo. Complete os itens pendentes antes de publicar.";
        }

        toast.show({
          title:
            "Perfil ainda incompleto",
          body,
          icon:
            "alert-circle",
        });
      } finally {
        setPublishing(false);
      }
    };

  if (loading) {
    return (
      <View
        style={
          styles.center
        }
        accessibilityRole="progressbar"
        accessibilityLabel="Carregando perfil profissional"
      >
        <ActivityIndicator
          color={colors.plum}
        />
      </View>
    );
  }

  if (!profile) {
    return (
      <View
        style={
          styles.center
        }
      >
        <Text
          style={
            styles.emptyTitle
          }
        >
          Seu perfil profissional ainda não foi criado.
        </Text>

        <Button
          title="Começar agora"
          onPress={() =>
            router.replace(
              "/signup-pro",
            )
          }
        />
      </View>
    );
  }

  return (
    <View
      style={
        styles.container
      }
    >
      <ScrollView
        contentContainerStyle={
          styles.content
        }
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={
          false
        }
      >
        <View
          style={
            styles.header
          }
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            onPress={() => {
              if (
                router.canGoBack()
              ) {
                router.back();
              } else {
                router.replace(
                  "/(tabs)/profile",
                );
              }
            }}
            style={
              styles.headerButton
            }
          >
            <Icon
              name="arrow-left"
              size={20}
              color={
                colors.onSurface
              }
            />
          </Pressable>

          <Text
            style={
              styles.headerTitle
            }
          >
            Perfil profissional
          </Text>

          <View
            style={
              styles.headerPlaceholder
            }
          />
        </View>

        <View
          style={
            styles.hero
          }
        >
          <Text
            style={
              styles.eyebrow
            }
          >
            SUA PRESENÇA NO IDDUN
          </Text>

          <Text
            style={
              styles.title
            }
          >
            {profile.displayName}
          </Text>

          <Text
            style={
              styles.subtitle
            }
          >
            {profile.primarySpecialty}
            {profile.city
              ? ` · ${profile.city}/${profile.state}`
              : ""}
          </Text>
        </View>

        <View
          style={
            styles.completionCard
          }
        >
          <View
            style={
              styles.completionHeader
            }
          >
            <View
              style={
                styles.completionCopy
              }
            >
              <Text
                style={
                  styles.sectionEyebrow
                }
              >
                PROFILE COMPLETION
              </Text>

              <Text
                style={
                  styles.sectionTitle
                }
              >
                Seu perfil está {profile.completion.percentage}% completo.
              </Text>
            </View>

            <Text
              style={
                styles.percentage
              }
            >
              {profile.completion.percentage}%
            </Text>
          </View>

          <View
            style={
              styles.progressTrack
            }
          >
            <View
              style={[
                styles.progressValue,
                {
                  width:
                    `${profile.completion.percentage}%`,
                },
              ]}
            />
          </View>

          <View
            style={
              styles.steps
            }
          >
            {profile.completion.steps.map(
              (step) => (
                <View
                  key={
                    step.key
                  }
                  style={
                    styles.step
                  }
                >
                  <Icon
                    name={
                      step.complete
                        ? "check-circle"
                        : "circle"
                    }
                    size={17}
                    color={
                      step.complete
                        ? colors.plum
                        : colors.muted
                    }
                  />

                  <Text
                    style={[
                      styles.stepText,
                      step.complete &&
                        styles.stepTextDone,
                    ]}
                  >
                    {step.label}
                  </Text>
                </View>
              ),
            )}
          </View>

          {profile.completion.recommendedActions.length >
          0 ? (
            <View
              style={
                styles.recommended
              }
            >
              <Text
                style={
                  styles.fieldHint
                }
              >
                Também fortalece sua presença:
              </Text>

              {profile.completion.recommendedActions.map(
                (item) => (
                  <Text
                    key={
                      item.key
                    }
                    style={
                      styles.recommendedText
                    }
                  >
                    ✦ {item.label}
                  </Text>
                ),
              )}
            </View>
          ) : null}

          <Button
            title="Editar dados básicos"
            variant="secondary"
            fullWidth
            onPress={() =>
              router.push(
                "/signup-pro",
              )
            }
          />
        </View>

        <View
          style={
            styles.section
          }
        >
          <Text
            style={
              styles.sectionEyebrow
            }
          >
            EXPERIÊNCIA PROFISSIONAL
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            Mostre onde sua história foi construída.
          </Text>

          <Text
            style={
              styles.sectionDescription
            }
          >
            Experiências externas ficam sem selo. Vínculos confirmados com estabelecimentos IDDUN poderão aparecer como verificados.
          </Text>

          {profile.experiences.map(
            (experience) => (
              <View
                key={
                  experience.id
                }
                style={
                  styles.experienceCard
                }
              >
                <View
                  style={
                    styles.experienceTop
                  }
                >
                  <View
                    style={
                      styles.experienceCopy
                    }
                  >
                    <Text
                      style={
                        styles.experienceRole
                      }
                    >
                      {experience.roleTitle}
                    </Text>

                    <Text
                      style={
                        styles.experienceCompany
                      }
                    >
                      {experience.companyName}
                    </Text>
                  </View>

                  {experience.verified ? (
                    <View
                      style={
                        styles.verifiedBadge
                      }
                    >
                      <Icon
                        name="check"
                        size={12}
                        color={
                          colors.onBrandPrimary
                        }
                      />
                      <Text
                        style={
                          styles.verifiedText
                        }
                      >
                        Verificado
                      </Text>
                    </View>
                  ) : null}
                </View>

                <Text
                  style={
                    styles.experiencePeriod
                  }
                >
                  {experience.startedAt}
                  {" — "}
                  {experience.isCurrent
                    ? "Atual"
                    : experience.endedAt ||
                      "Sem data final"}
                </Text>

                {experience.description ? (
                  <Text
                    style={
                      styles.experienceDescription
                    }
                  >
                    {experience.description}
                  </Text>
                ) : null}

                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={
                    `Remover experiência em ${experience.companyName}`
                  }
                  onPress={() =>
                    void handleRemoveExperience(
                      experience.id,
                    )
                  }
                >
                  <Text
                    style={
                      styles.removeText
                    }
                  >
                    Remover
                  </Text>
                </Pressable>
              </View>
            ),
          )}

          <View
            style={
              styles.formCard
            }
          >
            <Text
              style={
                styles.formTitle
              }
            >
              Adicionar experiência
            </Text>

            <TextInput
              value={
                companyName
              }
              onChangeText={
                setCompanyName
              }
              placeholder="Empresa ou studio"
              placeholderTextColor={
                colors.muted
              }
              style={
                styles.input
              }
            />

            <TextInput
              value={
                roleTitle
              }
              onChangeText={
                setRoleTitle
              }
              placeholder="Função, ex.: Nail Designer"
              placeholderTextColor={
                colors.muted
              }
              style={
                styles.input
              }
            />

            <TextInput
              value={
                startedAt
              }
              onChangeText={
                setStartedAt
              }
              placeholder="Início: AAAA-MM-DD"
              placeholderTextColor={
                colors.muted
              }
              autoCapitalize="none"
              style={
                styles.input
              }
            />

            {!isCurrent ? (
              <TextInput
                value={
                  endedAt
                }
                onChangeText={
                  setEndedAt
                }
                placeholder="Fim: AAAA-MM-DD"
                placeholderTextColor={
                  colors.muted
                }
                autoCapitalize="none"
                style={
                  styles.input
                }
              />
            ) : null}

            <View
              style={
                styles.switchRow
              }
            >
              <View
                style={
                  styles.switchCopy
                }
              >
                <Text
                  style={
                    styles.switchTitle
                  }
                >
                  Trabalho aqui atualmente
                </Text>

                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  A data final ficará aberta.
                </Text>
              </View>

              <Switch
                value={
                  isCurrent
                }
                onValueChange={
                  setIsCurrent
                }
                trackColor={{
                  false:
                    colors.graphite,
                  true:
                    colors.plum,
                }}
              />
            </View>

            <TextInput
              value={
                description
              }
              onChangeText={
                setDescription
              }
              placeholder="Conte brevemente o que você fazia"
              placeholderTextColor={
                colors.muted
              }
              multiline
              textAlignVertical="top"
              style={[
                styles.input,
                styles.textArea,
              ]}
            />

            <Button
              title="Adicionar experiência"
              variant="secondary"
              fullWidth
              loading={
                savingExperience
              }
              onPress={() =>
                void handleAddExperience()
              }
            />
          </View>
        </View>

        <View
          style={
            styles.publishCard
          }
        >
          <Text
            style={
              styles.sectionEyebrow
            }
          >
            PUBLICAÇÃO
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            {profile.completion.readyToPublish
              ? "Tudo pronto para entrar no ar."
              : "Seu rascunho está seguro."}
          </Text>

          <Text
            style={
              styles.sectionDescription
            }
          >
            {profile.completion.readyToPublish
              ? "Revise a prévia e publique quando estiver confortável."
              : "Foto e portfólio serão concluídos no fluxo de mídia. Você pode sair agora e continuar depois sem perder seus dados."}
          </Text>

          <Button
            title={
              profile.isActive
                ? "Perfil já publicado"
                : "Publicar perfil"
            }
            fullWidth
            disabled={
              profile.isActive ||
              !profile.completion
                .readyToPublish
            }
            loading={
              publishing
            }
            onPress={() =>
              void handlePublish()
            }
          />
        </View>
      </ScrollView>
    </View>
  );
}


const useStyles =
  makeStyles(
    (colors) => ({
      container: {
        flex: 1,
        backgroundColor:
          colors.surface,
      },

      content: {
        paddingHorizontal:
          spacing.lg,
        paddingBottom: 72,
        gap: spacing.xl,
      },

      center: {
        flex: 1,
        padding: spacing.xl,
        alignItems: "center",
        justifyContent:
          "center",
        gap: spacing.lg,
        backgroundColor:
          colors.surface,
      },

      emptyTitle: {
        fontFamily:
          fonts.display,
        fontSize: 24,
        lineHeight: 30,
        textAlign: "center",
        color:
          colors.onSurface,
      },

      header: {
        minHeight: 64,
        flexDirection: "row",
        alignItems: "center",
        justifyContent:
          "space-between",
      },

      headerButton: {
        width: 44,
        height: 44,
        alignItems: "center",
        justifyContent:
          "center",
      },

      headerPlaceholder: {
        width: 44,
        height: 44,
      },

      headerTitle: {
        fontFamily:
          fonts.sans,
        fontSize: 15,
        fontWeight: "700",
        color:
          colors.onSurface,
      },

      hero: {
        gap: spacing.sm,
      },

      eyebrow: {
        fontFamily:
          fonts.sans,
        fontSize: 11,
        letterSpacing: 1.5,
        color:
          colors.plum,
        fontWeight: "700",
      },

      title: {
        fontFamily:
          fonts.display,
        fontSize: 34,
        lineHeight: 39,
        color:
          colors.onSurface,
      },

      subtitle: {
        fontFamily:
          fonts.sans,
        fontSize: 15,
        color:
          colors.muted,
      },

      completionCard: {
        padding:
          spacing.lg,
        borderRadius:
          radius.xl,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.border,
        gap: spacing.lg,
      },

      completionHeader: {
        flexDirection: "row",
        alignItems:
          "flex-start",
        gap: spacing.md,
      },

      completionCopy: {
        flex: 1,
        gap: spacing.xs,
      },

      percentage: {
        fontFamily:
          fonts.display,
        fontSize: 30,
        color:
          colors.plum,
      },

      progressTrack: {
        height: 6,
        borderRadius:
          radius.pill,
        overflow: "hidden",
        backgroundColor:
          colors.graphite,
      },

      progressValue: {
        height: "100%",
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.plum,
      },

      steps: {
        gap: spacing.sm,
      },

      step: {
        flexDirection: "row",
        alignItems: "center",
        gap: spacing.sm,
      },

      stepText: {
        flex: 1,
        fontFamily:
          fonts.sans,
        fontSize: 14,
        color:
          colors.onSurface,
      },

      stepTextDone: {
        color:
          colors.muted,
      },

      recommended: {
        gap: spacing.xs,
      },

      recommendedText: {
        fontFamily:
          fonts.sans,
        fontSize: 13,
        color:
          colors.onSurface,
      },

      section: {
        gap: spacing.md,
      },

      sectionEyebrow: {
        fontFamily:
          fonts.sans,
        fontSize: 10,
        letterSpacing: 1.35,
        fontWeight: "700",
        color:
          colors.plum,
      },

      sectionTitle: {
        fontFamily:
          fonts.display,
        fontSize: 24,
        lineHeight: 30,
        color:
          colors.onSurface,
      },

      sectionDescription: {
        fontFamily:
          fonts.sans,
        fontSize: 14,
        lineHeight: 21,
        color:
          colors.muted,
      },

      experienceCard: {
        padding:
          spacing.lg,
        borderRadius:
          radius.lg,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.border,
        gap: spacing.sm,
      },

      experienceTop: {
        flexDirection: "row",
        alignItems:
          "flex-start",
        gap: spacing.sm,
      },

      experienceCopy: {
        flex: 1,
      },

      experienceRole: {
        fontFamily:
          fonts.sans,
        fontSize: 15,
        fontWeight: "700",
        color:
          colors.onSurface,
      },

      experienceCompany: {
        marginTop: 2,
        fontFamily:
          fonts.sans,
        fontSize: 14,
        color:
          colors.muted,
      },

      verifiedBadge: {
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
        paddingHorizontal:
          spacing.sm,
        paddingVertical: 5,
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.plum,
      },

      verifiedText: {
        fontFamily:
          fonts.sans,
        fontSize: 10,
        fontWeight: "700",
        color:
          colors.onBrandPrimary,
      },

      experiencePeriod: {
        fontFamily:
          fonts.sans,
        fontSize: 12,
        color:
          colors.muted,
      },

      experienceDescription: {
        fontFamily:
          fonts.sans,
        fontSize: 13,
        lineHeight: 19,
        color:
          colors.onSurface,
      },

      removeText: {
        fontFamily:
          fonts.sans,
        fontSize: 13,
        color:
          colors.plum,
        fontWeight: "700",
      },

      formCard: {
        padding:
          spacing.lg,
        borderRadius:
          radius.lg,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.border,
        gap: spacing.md,
      },

      formTitle: {
        fontFamily:
          fonts.sans,
        fontSize: 16,
        fontWeight: "700",
        color:
          colors.onSurface,
      },

      input: {
        minHeight: 50,
        paddingHorizontal:
          spacing.md,
        paddingVertical:
          spacing.sm,
        borderRadius:
          radius.md,
        borderWidth: 1,
        borderColor:
          colors.border,
        backgroundColor:
          colors.surface,
        fontFamily:
          fonts.sans,
        fontSize: 14,
        color:
          colors.onSurface,
      },

      textArea: {
        minHeight: 100,
      },

      switchRow: {
        minHeight: 52,
        flexDirection: "row",
        alignItems: "center",
        justifyContent:
          "space-between",
        gap: spacing.md,
      },

      switchCopy: {
        flex: 1,
        gap: 2,
      },

      switchTitle: {
        fontFamily:
          fonts.sans,
        fontSize: 14,
        fontWeight: "600",
        color:
          colors.onSurface,
      },

      fieldHint: {
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 17,
        color:
          colors.muted,
      },

      publishCard: {
        padding:
          spacing.lg,
        borderRadius:
          radius.xl,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.border,
        gap: spacing.md,
      },
    }),
  );
