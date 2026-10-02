import React, {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  Image,
} from "expo-image";

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
  deleteProfessionalPortfolioItem,
  reorderProfessionalPortfolio,
  updateProfessionalCoverFocus,
  uploadProfessionalAvatar,
  uploadProfessionalCover,
  uploadProfessionalPortfolioItem,
} from "@/api/media";

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
  MediaPermissionError,
  pickAndPrepareImage,
  type MediaKind,
  type MediaSource,
} from "@/media/imagePipeline";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";


const COVER_FOCUS_POINTS = [
  {
    x: 15,
    y: 15,
    label:
      "Topo esquerdo",
  },
  {
    x: 50,
    y: 15,
    label:
      "Topo central",
  },
  {
    x: 85,
    y: 15,
    label:
      "Topo direito",
  },
  {
    x: 15,
    y: 50,
    label:
      "Centro esquerdo",
  },
  {
    x: 50,
    y: 50,
    label:
      "Centro",
  },
  {
    x: 85,
    y: 50,
    label:
      "Centro direito",
  },
  {
    x: 15,
    y: 85,
    label:
      "Base esquerda",
  },
  {
    x: 50,
    y: 85,
    label:
      "Base central",
  },
  {
    x: 85,
    y: 85,
    label:
      "Base direita",
  },
] as const;


type MediaSourceActionsProps = {
  disabled: boolean;
  onLibrary: () => void;
  onCamera: () => void;
};

function MediaSourceActions({
  disabled,
  onLibrary,
  onCamera,
}: MediaSourceActionsProps) {
  const styles =
    useStyles();

  const { colors } =
    useTheme();

  return (
    <View
      style={
        styles.mediaActions
      }
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Escolher imagem da galeria"
        accessibilityState={{
          disabled,
        }}
        disabled={disabled}
        onPress={
          onLibrary
        }
        style={({ pressed }) => [
          styles.mediaAction,
          disabled &&
            styles.mediaActionDisabled,
          pressed &&
            !disabled &&
            styles.mediaActionPressed,
        ]}
      >
        <Icon
          name="image"
          size={16}
          color={
            colors.plum
          }
        />

        <Text
          style={
            styles.mediaActionText
          }
        >
          Galeria
        </Text>
      </Pressable>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Tirar uma foto"
        accessibilityState={{
          disabled,
        }}
        disabled={disabled}
        onPress={
          onCamera
        }
        style={({ pressed }) => [
          styles.mediaAction,
          disabled &&
            styles.mediaActionDisabled,
          pressed &&
            !disabled &&
            styles.mediaActionPressed,
        ]}
      >
        <Icon
          name="camera"
          size={16}
          color={
            colors.plum
          }
        />

        <Text
          style={
            styles.mediaActionText
          }
        >
          Câmera
        </Text>
      </Pressable>
    </View>
  );
}


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
    mediaBusy,
    setMediaBusy,
  ] =
    useState<MediaKind | null>(
      null,
    );

  const [
    coverFocusBusy,
    setCoverFocusBusy,
  ] =
    useState(false);

  const [
    companyName,
    setCompanyName,
  ] =
    useState("");

  const [
    establishmentId,
    setEstablishmentId,
  ] =
    useState<number | null>(
      null,
    );

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
      let mounted =
        true;

      getProfessionalOnboarding()
        .then(
          (response) => {
            if (mounted) {
              setProfile(
                response.profile,
              );
            }
          },
        )
        .catch(
          (error) => {
            if (!mounted) {
              return;
            }

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
          },
        )
        .finally(
          () => {
            if (mounted) {
              setLoading(false);
            }
          },
        );

      return () => {
        mounted = false;
      };
    },
    [toast],
  );

  const handleMediaUpload =
    async (
      kind: MediaKind,
      source: MediaSource,
    ) => {
      if (mediaBusy) {
        return;
      }

      try {
        const image =
          await pickAndPrepareImage(
            source,
            kind,
          );

        if (!image) {
          return;
        }

        setMediaBusy(
          kind,
        );

        if (kind === "avatar") {
          await uploadProfessionalAvatar(
            image,
          );
        } else if (
          kind === "cover"
        ) {
          await uploadProfessionalCover(
            image,
          );
        } else {
          await uploadProfessionalPortfolioItem(
            image,
          );
        }

        await load();

        toast.show({
          title:
            kind === "portfolio"
              ? "Trabalho adicionado"
              : kind === "avatar"
                ? "Foto atualizada"
                : "Capa atualizada",
          body:
            "A imagem foi salva no seu perfil.",
          icon:
            "check",
        });
      } catch (error) {
        toast.show({
          title:
            "Não foi possível salvar a imagem",
          body:
            error instanceof
              MediaPermissionError ||
            error instanceof Error
              ? error.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setMediaBusy(
          null,
        );
      }
    };

  const handleCoverFocus =
    async (
      focusX: number,
      focusY: number,
    ) => {
      if (
        coverFocusBusy ||
        !profile?.coverUrl
      ) {
        return;
      }

      try {
        setCoverFocusBusy(
          true,
        );

        await updateProfessionalCoverFocus(
          focusX,
          focusY,
        );

        setProfile(
          (current) =>
            current
              ? {
                  ...current,
                  coverFocusX:
                    focusX,
                  coverFocusY:
                    focusY,
                }
              : current,
        );
      } catch (error) {
        toast.show({
          title:
            "Não foi possível ajustar a capa",
          body:
            error instanceof Error
              ? error.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setCoverFocusBusy(
          false,
        );
      }
    };

  const removePortfolioItem =
    (
      itemId: number,
    ) => {
      Alert.alert(
        "Remover trabalho?",
        (
          "A imagem será removida do "
          + "seu portfólio."
        ),
        [
          {
            text: "Cancelar",
            style: "cancel",
          },
          {
            text: "Remover",
            style:
              "destructive",
            onPress: () => {
              void (
                async () => {
                  try {
                    await deleteProfessionalPortfolioItem(
                      itemId,
                    );

                    await load();

                    toast.show({
                      title:
                        "Trabalho removido",
                      icon:
                        "check",
                    });
                  } catch (
                    error
                  ) {
                    toast.show({
                      title:
                        "Não foi possível remover",
                      body:
                        error instanceof
                          Error
                          ? error.message
                          : "Tente novamente.",
                      icon:
                        "alert-circle",
                    });
                  }
                }
              )();
            },
          },
        ],
      );
    };

  const movePortfolioItem =
    async (
      itemId: number,
      direction: -1 | 1,
    ) => {
      const items =
        profile?.portfolio ||
        [];

      const currentIndex =
        items.findIndex(
          (item) =>
            item.id ===
            itemId,
        );

      const targetIndex =
        currentIndex +
        direction;

      if (
        currentIndex < 0 ||
        targetIndex < 0 ||
        targetIndex >=
          items.length
      ) {
        return;
      }

      const ids =
        items.map(
          (item) =>
            item.id,
        );

      [
        ids[currentIndex],
        ids[targetIndex],
      ] = [
        ids[targetIndex],
        ids[currentIndex],
      ];

      try {
        await reorderProfessionalPortfolio(
          ids,
        );
        await load();
      } catch (error) {
        toast.show({
          title:
            "Não foi possível reorganizar",
          body:
            error instanceof Error
              ? error.message
              : "Tente novamente.",
          icon:
            "alert-circle",
        });
      }
    };

  const handleAddExperience =
    async () => {
      if (
        (
          !companyName.trim() &&
          establishmentId === null
        ) ||
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
          establishmentId,
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
        setEstablishmentId(
          null,
        );
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
            MÍDIA DO PERFIL
          </Text>

          <Text
            style={
              styles.sectionTitle
            }
          >
            Mostre seu trabalho antes mesmo da primeira conversa.
          </Text>

          <Text
            style={
              styles.sectionDescription
            }
          >
            As imagens são otimizadas antes do envio e o IDDUN também valida o arquivo no servidor.
          </Text>

          <View
            style={
              styles.mediaCard
            }
          >
            <View
              style={
                styles.mediaCardHeader
              }
            >
              <View
                style={
                  styles.mediaCardCopy
                }
              >
                <Text
                  style={
                    styles.mediaCardTitle
                  }
                >
                  Foto de perfil
                </Text>

                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Obrigatória · corte quadrado · até 5 MB no servidor
                </Text>
              </View>

              {profile.avatarUrl ? (
                <Icon
                  name="check-circle"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              ) : null}
            </View>

            <View
              style={
                styles.avatarMediaRow
              }
            >
              {profile.avatarUrl ? (
                <Image
                  source={{
                    uri:
                      profile.avatarUrl,
                  }}
                  style={
                    styles.avatarMediaPreview
                  }
                  contentFit="cover"
                  transition={160}
                  accessibilityLabel={
                    `Foto de perfil de ${profile.displayName}`
                  }
                />
              ) : (
                <View
                  style={
                    styles.avatarMediaPlaceholder
                  }
                >
                  <Text
                    style={
                      styles.avatarMediaInitial
                    }
                  >
                    {profile.displayName
                      .charAt(0)
                      .toUpperCase()}
                  </Text>
                </View>
              )}

              <View
                style={
                  styles.mediaCardCopy
                }
              >
                <Text
                  style={
                    styles.mediaCardBody
                  }
                >
                  Use uma foto nítida, com seu rosto ou identidade profissional bem visível.
                </Text>
              </View>
            </View>

            <MediaSourceActions
              disabled={
                mediaBusy !==
                null
              }
              onLibrary={() =>
                void handleMediaUpload(
                  "avatar",
                  "library",
                )
              }
              onCamera={() =>
                void handleMediaUpload(
                  "avatar",
                  "camera",
                )
              }
            />

            {mediaBusy ===
            "avatar" ? (
              <View
                style={
                  styles.mediaProgress
                }
              >
                <ActivityIndicator
                  size="small"
                  color={
                    colors.plum
                  }
                />
                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Preparando e enviando foto...
                </Text>
              </View>
            ) : null}
          </View>

          <View
            style={
              styles.mediaCard
            }
          >
            <View
              style={
                styles.mediaCardHeader
              }
            >
              <View
                style={
                  styles.mediaCardCopy
                }
              >
                <Text
                  style={
                    styles.mediaCardTitle
                  }
                >
                  Capa
                </Text>

                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Opcional · composição horizontal recomendada
                </Text>
              </View>

              {profile.coverUrl ? (
                <Icon
                  name="check-circle"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              ) : null}
            </View>

            {profile.coverUrl ? (
              <>
                <View
                  style={
                    styles.coverMediaFrame
                  }
                >
                  <Image
                    source={{
                      uri:
                        profile.coverUrl,
                    }}
                    style={
                      styles.coverMediaPreview
                    }
                    contentFit="cover"
                    contentPosition={{
                      left:
                        `${profile.coverFocusX}%`,
                      top:
                        `${profile.coverFocusY}%`,
                    }}
                    transition={160}
                    accessibilityLabel={
                      `Capa do perfil de ${profile.displayName}`
                    }
                  />

                  <View
                    style={
                      styles.coverFocusGrid
                    }
                  >
                    {COVER_FOCUS_POINTS.map(
                      (
                        point,
                      ) => {
                        const selected =
                          profile.coverFocusX ===
                            point.x &&
                          profile.coverFocusY ===
                            point.y;

                        return (
                          <Pressable
                            key={
                              `${point.x}-${point.y}`
                            }
                            accessibilityRole="button"
                            accessibilityLabel={
                              `Enquadrar capa em ${point.label}`
                            }
                            accessibilityState={{
                              selected,
                              disabled:
                                coverFocusBusy,
                            }}
                            disabled={
                              coverFocusBusy
                            }
                            onPress={() =>
                              void handleCoverFocus(
                                point.x,
                                point.y,
                              )
                            }
                            style={
                              styles.coverFocusCell
                            }
                          >
                            {selected ? (
                              <View
                                style={
                                  styles.coverFocusDot
                                }
                              />
                            ) : null}
                          </Pressable>
                        );
                      },
                    )}
                  </View>
                </View>

                <View
                  style={
                    styles.coverFocusHint
                  }
                >
                  {coverFocusBusy ? (
                    <ActivityIndicator
                      size="small"
                      color={
                        colors.plum
                      }
                    />
                  ) : (
                    <Icon
                      name="move"
                      size={14}
                      color={
                        colors.plum
                      }
                    />
                  )}

                  <Text
                    style={
                      styles.fieldHint
                    }
                  >
                    Toque na região que deve permanecer em destaque no recorte da capa.
                  </Text>
                </View>
              </>
            ) : (
              <View
                style={
                  styles.coverMediaPlaceholder
                }
              >
                <Icon
                  name="image"
                  size={24}
                  color={
                    colors.muted
                  }
                />

                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Adicione uma imagem que represente seu estilo de trabalho.
                </Text>
              </View>
            )}

            <MediaSourceActions
              disabled={
                mediaBusy !==
                null
              }
              onLibrary={() =>
                void handleMediaUpload(
                  "cover",
                  "library",
                )
              }
              onCamera={() =>
                void handleMediaUpload(
                  "cover",
                  "camera",
                )
              }
            />

            {mediaBusy ===
            "cover" ? (
              <View
                style={
                  styles.mediaProgress
                }
              >
                <ActivityIndicator
                  size="small"
                  color={
                    colors.plum
                  }
                />
                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Preparando e enviando capa...
                </Text>
              </View>
            ) : null}
          </View>

          <View
            style={
              styles.mediaCard
            }
          >
            <View
              style={
                styles.mediaCardHeader
              }
            >
              <View
                style={
                  styles.mediaCardCopy
                }
              >
                <Text
                  style={
                    styles.mediaCardTitle
                  }
                >
                  Portfólio
                </Text>

                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  {profile.portfolioCount}/8 imagens · mínimo de 3 para publicar
                </Text>
              </View>

              {profile.portfolioCount >=
              3 ? (
                <Icon
                  name="check-circle"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              ) : null}
            </View>

            {profile.portfolio.length >
            0 ? (
              <View
                style={
                  styles.portfolioGrid
                }
              >
                {profile.portfolio.map(
                  (
                    item,
                    index,
                  ) => (
                    <View
                      key={
                        item.id
                      }
                      style={
                        styles.portfolioItem
                      }
                    >
                      <Image
                        source={{
                          uri:
                            item.imageUrl,
                        }}
                        style={
                          styles.portfolioImage
                        }
                        contentFit="cover"
                        transition={140}
                        accessibilityLabel={
                          item.caption ||
                          `Trabalho ${index + 1} do portfólio`
                        }
                      />

                      <View
                        style={
                          styles.portfolioOrder
                        }
                      >
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={
                            `Mover trabalho ${index + 1} para a esquerda`
                          }
                          accessibilityState={{
                            disabled:
                              index ===
                              0,
                          }}
                          disabled={
                            index ===
                              0 ||
                            mediaBusy !==
                              null
                          }
                          onPress={() =>
                            void movePortfolioItem(
                              item.id,
                              -1,
                            )
                          }
                          style={
                            styles.portfolioIconButton
                          }
                        >
                          <Icon
                            name="chevron-left"
                            size={17}
                            color={
                              index ===
                              0
                                ? colors.muted
                                : colors.onSurface
                            }
                          />
                        </Pressable>

                        <Text
                          style={
                            styles.portfolioPosition
                          }
                        >
                          {index + 1}
                        </Text>

                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={
                            `Mover trabalho ${index + 1} para a direita`
                          }
                          accessibilityState={{
                            disabled:
                              index ===
                              profile.portfolio.length -
                                1,
                          }}
                          disabled={
                            index ===
                              profile.portfolio.length -
                                1 ||
                            mediaBusy !==
                              null
                          }
                          onPress={() =>
                            void movePortfolioItem(
                              item.id,
                              1,
                            )
                          }
                          style={
                            styles.portfolioIconButton
                          }
                        >
                          <Icon
                            name="chevron-right"
                            size={17}
                            color={
                              index ===
                              profile.portfolio.length -
                                1
                                ? colors.muted
                                : colors.onSurface
                            }
                          />
                        </Pressable>

                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={
                            `Remover trabalho ${index + 1}`
                          }
                          disabled={
                            mediaBusy !==
                            null
                          }
                          onPress={() =>
                            removePortfolioItem(
                              item.id,
                            )
                          }
                          style={[
                            styles.portfolioIconButton,
                            styles.portfolioDeleteButton,
                          ]}
                        >
                          <Icon
                            name="trash-2"
                            size={15}
                            color={
                              colors.error
                            }
                          />
                        </Pressable>
                      </View>
                    </View>
                  ),
                )}
              </View>
            ) : (
              <View
                style={
                  styles.portfolioEmpty
                }
              >
                <Icon
                  name="grid"
                  size={24}
                  color={
                    colors.muted
                  }
                />

                <Text
                  style={
                    styles.mediaCardBody
                  }
                >
                  Seu portfólio ainda está vazio. Adicione pelo menos três trabalhos para liberar a publicação.
                </Text>
              </View>
            )}

            {profile.portfolioCount <
            8 ? (
              <MediaSourceActions
                disabled={
                  mediaBusy !==
                  null
                }
                onLibrary={() =>
                  void handleMediaUpload(
                    "portfolio",
                    "library",
                  )
                }
                onCamera={() =>
                  void handleMediaUpload(
                    "portfolio",
                    "camera",
                  )
                }
              />
            ) : (
              <Text
                style={
                  styles.fieldHint
                }
              >
                Você atingiu o limite de 8 imagens. Remova uma para adicionar outra.
              </Text>
            )}

            {mediaBusy ===
            "portfolio" ? (
              <View
                style={
                  styles.mediaProgress
                }
              >
                <ActivityIndicator
                  size="small"
                  color={
                    colors.plum
                  }
                />
                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Otimizando e enviando trabalho...
                </Text>
              </View>
            ) : null}
          </View>
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

            {profile.memberships.filter(
              (membership) =>
                membership.status ===
                "active",
            ).length > 0 ? (
              <View
                style={
                  styles.membershipChoices
                }
              >
                <Text
                  style={
                    styles.fieldHint
                  }
                >
                  Se esta experiência aconteceu em um vínculo confirmado no IDDUN, selecione o local para receber o selo verificado.
                </Text>

                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{
                    selected:
                      establishmentId ===
                      null,
                  }}
                  onPress={() => {
                    setEstablishmentId(
                      null,
                    );
                  }}
                  style={[
                    styles.membershipChip,
                    establishmentId ===
                      null &&
                      styles.membershipChipSelected,
                  ]}
                >
                  <Text
                    style={
                      styles.membershipChipText
                    }
                  >
                    Experiência externa
                  </Text>
                </Pressable>

                {profile.memberships
                  .filter(
                    (membership) =>
                      membership.status ===
                      "active",
                  )
                  .map(
                    (membership) => (
                      <Pressable
                        key={
                          membership.id
                        }
                        accessibilityRole="button"
                        accessibilityState={{
                          selected:
                            establishmentId ===
                            membership
                              .establishment
                              .id,
                        }}
                        onPress={() => {
                          setEstablishmentId(
                            membership
                              .establishment
                              .id,
                          );
                          setCompanyName(
                            membership
                              .establishment
                              .name,
                          );
                        }}
                        style={[
                          styles.membershipChip,
                          establishmentId ===
                            membership
                              .establishment
                              .id &&
                            styles.membershipChipSelected,
                        ]}
                      >
                        <Text
                          style={
                            styles.membershipChipText
                          }
                        >
                          {
                            membership
                              .establishment
                              .name
                          }
                        </Text>
                      </Pressable>
                    ),
                  )}
              </View>
            ) : null}

            <TextInput
              value={
                companyName
              }
              onChangeText={
                setCompanyName
              }
              editable={
                establishmentId ===
                null
              }
              placeholder="Empresa ou studio"
              placeholderTextColor={
                colors.muted
              }
              style={[
                styles.input,
                establishmentId !==
                  null &&
                  styles.inputDisabled,
              ]}
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
              : "Complete os itens pendentes acima. Tudo fica salvo para você continuar depois sem perder seus dados."}
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
          radius.lg,
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

      mediaCard: {
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

      mediaCardHeader: {
        flexDirection:
          "row",
        alignItems:
          "flex-start",
        justifyContent:
          "space-between",
        gap: spacing.md,
      },

      mediaCardCopy: {
        flex: 1,
        gap: spacing.xs,
      },

      mediaCardTitle: {
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 15,
        color:
          colors.onSurface,
      },

      mediaCardBody: {
        fontFamily:
          fonts.sans,
        fontSize: 13,
        lineHeight: 19,
        color:
          colors.onSurfaceSecondary,
      },

      mediaActions: {
        flexDirection:
          "row",
        gap: spacing.sm,
      },

      mediaAction: {
        flex: 1,
        minHeight: 46,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.pill,
        borderWidth: 1,
        borderColor:
          colors.border,
        backgroundColor:
          colors.surface,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.sm,
      },

      mediaActionPressed: {
        opacity: 0.82,
      },

      mediaActionDisabled: {
        opacity: 0.48,
      },

      mediaActionText: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 12,
        color:
          colors.onSurface,
      },

      mediaProgress: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.sm,
      },

      avatarMediaRow: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.md,
      },

      avatarMediaPreview: {
        width: 78,
        height: 78,
        borderRadius: 39,
        backgroundColor:
          colors.graphite,
      },

      avatarMediaPlaceholder: {
        width: 78,
        height: 78,
        borderRadius: 39,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plumSoft,
        borderWidth: 1,
        borderColor:
          colors.border,
      },

      avatarMediaInitial: {
        fontFamily:
          fonts.display,
        fontSize: 30,
        color:
          colors.plum,
      },

      coverMediaFrame: {
        position:
          "relative",
        width: "100%",
        aspectRatio: 16 / 7,
        borderRadius:
          radius.md,
        overflow:
          "hidden",
        backgroundColor:
          colors.graphite,
      },

      coverMediaPreview: {
        width: "100%",
        height: "100%",
        backgroundColor:
          colors.graphite,
      },

      coverFocusGrid: {
        position:
          "absolute",
        top: 0,
        right: 0,
        bottom: 0,
        left: 0,
        flexDirection:
          "row",
        flexWrap:
          "wrap",
      },

      coverFocusCell: {
        width: "33.3333%",
        height: "33.3333%",
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      coverFocusDot: {
        width: 18,
        height: 18,
        borderRadius: 9,
        backgroundColor:
          colors.plum,
        borderWidth: 3,
        borderColor:
          colors.white,
      },

      coverFocusHint: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.sm,
      },

      coverMediaPlaceholder: {
        width: "100%",
        minHeight: 132,
        padding:
          spacing.lg,
        borderRadius:
          radius.md,
        borderWidth: 1,
        borderStyle:
          "dashed",
        borderColor:
          colors.border,
        backgroundColor:
          colors.surface,
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.sm,
      },

      portfolioGrid: {
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap: spacing.sm,
      },

      portfolioItem: {
        width: "48%",
        borderRadius:
          radius.md,
        overflow:
          "hidden",
        borderWidth: 1,
        borderColor:
          colors.border,
        backgroundColor:
          colors.surface,
      },

      portfolioImage: {
        width: "100%",
        aspectRatio: 1,
        backgroundColor:
          colors.graphite,
      },

      portfolioOrder: {
        minHeight: 42,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "space-between",
        paddingHorizontal:
          spacing.xs,
      },

      portfolioIconButton: {
        width: 34,
        height: 34,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      portfolioDeleteButton: {
        backgroundColor:
          "rgba(239,68,68,0.08)",
      },

      portfolioPosition: {
        minWidth: 18,
        textAlign:
          "center",
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
        color:
          colors.muted,
      },

      portfolioEmpty: {
        minHeight: 120,
        padding:
          spacing.lg,
        borderRadius:
          radius.md,
        borderWidth: 1,
        borderStyle:
          "dashed",
        borderColor:
          colors.border,
        backgroundColor:
          colors.surface,
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.sm,
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

      inputDisabled: {
        opacity: 0.7,
      },

      membershipChoices: {
        gap: spacing.sm,
      },

      membershipChip: {
        minHeight: 42,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.pill,
        borderWidth: 1,
        borderColor:
          colors.border,
        alignItems: "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.surface,
      },

      membershipChipSelected: {
        borderColor:
          colors.plum,
        backgroundColor:
          colors.plumSoft,
      },

      membershipChipText: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 12,
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
          radius.lg,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.border,
        gap: spacing.md,
      },
    }),
  );
