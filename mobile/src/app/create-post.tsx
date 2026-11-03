import React, {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  ActivityIndicator,
  Pressable,
  ScrollView,
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
  createPost,
  getCreatorOptions,
  type CreatorOptions,
  type WorkPostAuthorKind,
} from "@/api/feed";

import type {
  UploadableImage,
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
  type MediaSource,
} from "@/media/imagePipeline";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";


const MAX_IMAGES = 10;

const AUTHOR_LABEL: Record<WorkPostAuthorKind, string> = {
  client: "Cliente",
  professional: "Profissional",
  establishment: "Empresa",
};


export default function CreatePostScreen() {
  const styles =
    useStyles();

  const { colors } =
    useTheme();

  const router =
    useRouter();

  const toast =
    useToast();

  const [
    options,
    setOptions,
  ] =
    useState<CreatorOptions | null>(
      null,
    );

  const [
    loading,
    setLoading,
  ] =
    useState(true);

  // Carrossel até 10 fotos, com texto alternativo (PR 3; D-SOC-02).
  const [
    images,
    setImages,
  ] =
    useState<
      {
        image: UploadableImage;
        alt: string;
      }[]
    >([]);

  const [
    caption,
    setCaption,
  ] =
    useState("");

  const [
    authorType,
    setAuthorType,
  ] =
    useState<WorkPostAuthorKind | null>(
      null,
    );

  const [
    authorId,
    setAuthorId,
  ] =
    useState<number | null>(
      null,
    );

  const [
    experienceId,
    setExperienceId,
  ] =
    useState<number | null>(
      null,
    );

  const [
    mediaBusy,
    setMediaBusy,
  ] =
    useState(false);

  const [
    publishing,
    setPublishing,
  ] =
    useState(false);

  useEffect(
    () => {
      let mounted =
        true;

      getCreatorOptions()
        .then(
          (response) => {
            if (!mounted) {
              return;
            }

            setOptions(
              response,
            );

            const first =
              response.authors[
                0
              ];

            if (first) {
              setAuthorType(
                first.type,
              );
              setAuthorId(
                first.id,
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
                "Não foi possível carregar o Creator",
              body:
                error instanceof
                  Error
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
              setLoading(
                false,
              );
            }
          },
        );

      return () => {
        mounted = false;
      };
    },
    [toast],
  );

  const experiences =
    useMemo(
      () =>
        (
          options
            ?.experiences ??
          []
        ).filter(
          (item) =>
            item.authorType ===
              authorType &&
            item.authorId ===
              authorId,
        ),
      [
        options,
        authorType,
        authorId,
      ],
    );

  const chooseImage =
    async (
      source:
        MediaSource,
    ) => {
      if (mediaBusy) {
        return;
      }

      if (images.length >= MAX_IMAGES) {
        toast.show({
          title: "Limite de fotos",
          body: `Uma publicação pode ter até ${MAX_IMAGES} fotos.`,
          icon: "alert-circle",
        });
        return;
      }

      try {
        setMediaBusy(
          true,
        );

        const prepared =
          await pickAndPrepareImage(
            source,
            "post",
          );

        if (prepared) {
          setImages(
            (current) => [
              ...current,
              {
                image: prepared,
                alt: "",
              },
            ].slice(0, MAX_IMAGES),
          );
        }
      } catch (error) {
        toast.show({
          title:
            "Não foi possível escolher a imagem",
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
          false,
        );
      }
    };

  const selectAuthor =
    (
      type:
        WorkPostAuthorKind,
      id: number,
    ) => {
      setAuthorType(
        type,
      );
      setAuthorId(
        id,
      );
      setExperienceId(
        null,
      );
    };

  const publish =
    async () => {
      if (
        (!images.length &&
          !caption.trim()) ||
        !authorType ||
        !authorId
      ) {
        toast.show({
          title:
            "Complete a publicação",
          body:
            "Escreva um texto ou adicione uma foto.",
          icon:
            "alert-circle",
        });
        return;
      }

      try {
        setPublishing(
          true,
        );

        const response =
          await createPost({
            authorType,
            authorId,
            images,
            caption:
              caption.trim(),
            experienceId:
              authorType === "client"
                ? null
                : experienceId,
            status:
              "published",
          });

        toast.show({
          title:
            "Publicado no IDDUN",
          body:
            "Seu trabalho já pode aparecer no feed.",
          icon:
            "check",
        });

        router.replace(
          `/post/${response.post.id}`,
        );
      } catch (error) {
        toast.show({
          title:
            "Não foi possível publicar",
          body:
            error instanceof Error
              ? error.message
              : "Revise os dados e tente novamente.",
          icon:
            "alert-circle",
        });
      } finally {
        setPublishing(
          false,
        );
      }
    };

  if (loading) {
    return (
      <View
        style={
          styles.center
        }
        accessibilityRole="progressbar"
        accessibilityLabel="Carregando Creator"
      >
        <ActivityIndicator
          color={
            colors.plum
          }
        />
      </View>
    );
  }

  const hasAuthors =
    Boolean(
      options?.authors
        .length,
    );

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
                  "/create",
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
            Nova publicação
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
            CREATOR
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Mostre o trabalho. O IDDUN faz a descoberta.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Compartilhe um resultado real e, se quiser, conecte a publicação ao serviço que a pessoa pode agendar.
          </Text>
        </View>

        {!hasAuthors ? (
          <View
            style={
              styles.emptyCard
            }
          >
            <Icon
              name="briefcase"
              size={24}
              color={
                colors.plum
              }
            />

            <Text
              style={
                styles.emptyTitle
              }
            >
              Nenhum perfil público disponível
            </Text>

            <Text
              style={
                styles.emptyText
              }
            >
              Complete e publique seu perfil profissional ou estabelecimento antes de publicar trabalhos no feed.
            </Text>

            <Button
              title="Voltar ao painel"
              variant="secondary"
              fullWidth
              onPress={() =>
                router.replace(
                  "/create",
                )
              }
            />
          </View>
        ) : (
          <>
            <View
              style={
                styles.section
              }
            >
              <Text
                style={
                  styles.sectionLabel
                }
              >
                {`FOTOS (${images.length}/${MAX_IMAGES})`}
              </Text>

              {images.length ? (
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.thumbs}
                >
                  {images.map((item, index) => (
                    <View
                      key={`${item.image.uri}-${index}`}
                      style={styles.thumb}
                    >
                      <Image
                        source={{ uri: item.image.uri }}
                        style={styles.thumbImage}
                        contentFit="cover"
                        accessibilityLabel={`Foto ${index + 1} de ${images.length}`}
                      />
                      <TextInput
                        value={item.alt}
                        onChangeText={(value) =>
                          setImages((current) =>
                            current.map((entry, position) =>
                              position === index
                                ? { ...entry, alt: value }
                                : entry,
                            ),
                          )
                        }
                        placeholder="Descreva a foto"
                        placeholderTextColor={colors.muted}
                        maxLength={300}
                        style={styles.altInput}
                        accessibilityLabel={`Texto alternativo da foto ${index + 1}`}
                      />
                      <View style={styles.thumbControls}>
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Mover foto ${index + 1} para antes`}
                          disabled={index === 0}
                          onPress={() =>
                            setImages((current) => {
                              const next = [...current];
                              [next[index - 1], next[index]] = [next[index], next[index - 1]];
                              return next;
                            })
                          }
                          style={[styles.thumbButton, index === 0 && styles.thumbButtonDisabled]}
                        >
                          <Icon name="arrow-left" size={16} color={colors.onSurface} />
                        </Pressable>
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Mover foto ${index + 1} para depois`}
                          disabled={index === images.length - 1}
                          onPress={() =>
                            setImages((current) => {
                              const next = [...current];
                              [next[index + 1], next[index]] = [next[index], next[index + 1]];
                              return next;
                            })
                          }
                          style={[
                            styles.thumbButton,
                            index === images.length - 1 && styles.thumbButtonDisabled,
                          ]}
                        >
                          <Icon name="arrow-right" size={16} color={colors.onSurface} />
                        </Pressable>
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Remover foto ${index + 1}`}
                          onPress={() =>
                            setImages((current) =>
                              current.filter((_, position) => position !== index),
                            )
                          }
                          style={styles.thumbButton}
                        >
                          <Icon name="x" size={16} color={colors.onSurface} />
                        </Pressable>
                      </View>
                    </View>
                  ))}
                </ScrollView>
              ) : (
                <View
                  style={
                    styles.imagePlaceholder
                  }
                >
                  <Icon
                    name="image"
                    size={30}
                    color={
                      colors.muted
                    }
                  />

                  <Text
                    style={
                      styles.placeholderTitle
                    }
                  >
                    Fotos são opcionais
                  </Text>

                  <Text
                    style={
                      styles.placeholderText
                    }
                  >
                    {`Até ${MAX_IMAGES} fotos, na ordem que você escolher. Também dá para publicar só texto.`}
                  </Text>
                </View>
              )}

              <View
                style={
                  styles.mediaActions
                }
              >
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Escolher imagem da galeria"
                  disabled={
                    mediaBusy
                  }
                  onPress={() =>
                    void chooseImage(
                      "library",
                    )
                  }
                  style={
                    styles.mediaButton
                  }
                >
                  <Icon
                    name="image"
                    size={17}
                    color={
                      colors.plum
                    }
                  />

                  <Text
                    style={
                      styles.mediaButtonText
                    }
                  >
                    Galeria
                  </Text>
                </Pressable>

                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Tirar uma foto"
                  disabled={
                    mediaBusy
                  }
                  onPress={() =>
                    void chooseImage(
                      "camera",
                    )
                  }
                  style={
                    styles.mediaButton
                  }
                >
                  <Icon
                    name="camera"
                    size={17}
                    color={
                      colors.plum
                    }
                  />

                  <Text
                    style={
                      styles.mediaButtonText
                    }
                  >
                    Câmera
                  </Text>
                </Pressable>
              </View>

              {mediaBusy ? (
                <View
                  style={
                    styles.loadingRow
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
                      styles.hint
                    }
                  >
                    Preparando imagem...
                  </Text>
                </View>
              ) : null}
            </View>

            <View
              style={
                styles.section
              }
            >
              <Text
                style={
                  styles.sectionLabel
                }
              >
                PUBLICAR COMO
              </Text>

              <View
                style={
                  styles.choiceList
                }
              >
                {options?.authors.map(
                  (author) => {
                    const selected =
                      author.type ===
                        authorType &&
                      author.id ===
                        authorId;

                    return (
                      <Pressable
                        key={
                          author.type
                          + "-"
                          + author.id
                        }
                        accessibilityRole="button"
                        accessibilityState={{
                          selected,
                        }}
                        onPress={() =>
                          selectAuthor(
                            author.type,
                            author.id,
                          )
                        }
                        style={[
                          styles.choice,
                          selected &&
                            styles.choiceSelected,
                        ]}
                      >
                        <Icon
                          name={
                            author.type ===
                            "establishment"
                              ? "home"
                              : author.type ===
                                  "professional"
                                ? "briefcase"
                                : "user"
                          }
                          size={17}
                          color={
                            selected
                              ? colors.plum
                              : colors.muted
                          }
                        />

                        <Text
                          style={[
                            styles.choiceText,
                            selected &&
                              styles.choiceTextSelected,
                          ]}
                          numberOfLines={1}
                        >
                          {`${author.name} · ${AUTHOR_LABEL[author.type]}`}
                        </Text>
                      </Pressable>
                    );
                  },
                )}
              </View>
            </View>

            <View
              style={
                styles.section
              }
            >
              <Text
                style={
                  styles.sectionLabel
                }
              >
                TEXTO
              </Text>

              <TextInput
                value={
                  caption
                }
                onChangeText={
                  setCaption
                }
                placeholder="Conte o que torna esse trabalho especial..."
                placeholderTextColor={
                  colors.muted
                }
                multiline
                maxLength={1200}
                textAlignVertical="top"
                style={
                  styles.textArea
                }
                accessibilityLabel="Legenda da publicação"
              />

              <Text
                style={
                  styles.counter
                }
              >
                {caption.length}/1200
              </Text>
            </View>

            {authorType !== "client" ? (
            <View
              style={
                styles.section
              }
            >
              <Text
                style={
                  styles.sectionLabel
                }
              >
                SERVIÇO RELACIONADO
              </Text>

              <Text
                style={
                  styles.hint
                }
              >
                Opcional. Vincular um serviço cria um caminho direto da inspiração para o agendamento.
              </Text>

              <Pressable
                accessibilityRole="button"
                accessibilityState={{
                  selected:
                    experienceId ===
                    null,
                }}
                onPress={() =>
                  setExperienceId(
                    null,
                  )
                }
                style={[
                  styles.choice,
                  experienceId ===
                    null &&
                    styles.choiceSelected,
                ]}
              >
                <Icon
                  name="minus"
                  size={17}
                  color={
                    experienceId ===
                    null
                      ? colors.plum
                      : colors.muted
                  }
                />

                <Text
                  style={[
                    styles.choiceText,
                    experienceId ===
                      null &&
                      styles.choiceTextSelected,
                  ]}
                >
                  Sem serviço vinculado
                </Text>
              </Pressable>

              {experiences.map(
                (experience) => {
                  const selected =
                    experience.id ===
                    experienceId;

                  return (
                    <Pressable
                      key={
                        experience.id
                      }
                      accessibilityRole="button"
                      accessibilityState={{
                        selected,
                      }}
                      onPress={() =>
                        setExperienceId(
                          experience.id,
                        )
                      }
                      style={[
                        styles.choice,
                        selected &&
                          styles.choiceSelected,
                      ]}
                    >
                      <Icon
                        name="scissors"
                        size={17}
                        color={
                          selected
                            ? colors.plum
                            : colors.muted
                        }
                      />

                      <Text
                        style={[
                          styles.choiceText,
                          selected &&
                            styles.choiceTextSelected,
                        ]}
                        numberOfLines={2}
                      >
                        {experience.title}
                      </Text>
                    </Pressable>
                  );
                },
              )}
            </View>
            ) : null}

            <View
              style={
                styles.publishCard
              }
            >
              <Text
                style={
                  styles.publishTitle
                }
              >
                Pronto para aparecer no feed?
              </Text>

              <Text
                style={
                  styles.hint
                }
              >
                Audiência: Público. Você poderá editar a legenda ou remover a publicação depois.
              </Text>

              <Button
                title="Publicar"
                fullWidth
                loading={
                  publishing
                }
                disabled={
                  (!images.length &&
                    !caption.trim()) ||
                  !authorType ||
                  !authorId
                }
                onPress={() =>
                  void publish()
                }
              />
            </View>
          </>
        )}

        <View
          style={
            styles.bottomSpace
          }
        />
      </ScrollView>
    </View>
  );
}


const useStyles =
  makeStyles(
    (colors) => ({
      thumbs: {
        gap: spacing.md,
      },

      thumb: {
        width: 148,
        gap: spacing.sm,
      },

      thumbImage: {
        width: 148,
        height: 148,
        borderRadius: radius.md,
      },

      altInput: {
        minHeight: 44,
        paddingHorizontal: spacing.sm,
        borderRadius: radius.sm,
        borderWidth: 1,
        borderColor: colors.glassBorderStrong,
        color: colors.onSurface,
        fontFamily: fonts.sans,
        fontSize: 13,
      },

      thumbControls: {
        flexDirection: "row",
        gap: spacing.xs,
      },

      thumbButton: {
        width: 44,
        height: 44,
        alignItems: "center",
        justifyContent: "center",
        borderRadius: radius.sm,
        backgroundColor: colors.glassSoft,
      },

      thumbButtonDisabled: {
        opacity: 0.4,
      },

      container: {
        flex: 1,
        backgroundColor:
          colors.surface,
      },

      content: {
        paddingHorizontal:
          spacing.lg,
        paddingBottom: 48,
      },

      center: {
        flex: 1,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.surface,
      },

      header: {
        minHeight: 64,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "space-between",
      },

      headerButton: {
        width: 44,
        height: 44,
        alignItems:
          "center",
        justifyContent:
          "center",
      },

      headerPlaceholder: {
        width: 44,
        height: 44,
      },

      headerTitle: {
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 15,
        color:
          colors.onSurface,
      },

      hero: {
        marginTop:
          spacing.md,
      },

      eyebrow: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 10,
        letterSpacing: 1.4,
        color:
          colors.plum,
      },

      title: {
        maxWidth: 350,
        marginTop:
          spacing.sm,
        fontFamily:
          fonts.display,
        fontSize: 32,
        lineHeight: 38,
        color:
          colors.onSurface,
      },

      description: {
        maxWidth: 350,
        marginTop:
          spacing.md,
        fontFamily:
          fonts.sans,
        fontSize: 13,
        lineHeight: 20,
        color:
          colors.onSurfaceSecondary,
      },

      section: {
        marginTop:
          spacing.xxl,
        gap: spacing.md,
      },

      sectionLabel: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 10,
        letterSpacing: 1.3,
        color:
          colors.plum,
      },

      preview: {
        width: "100%",
        aspectRatio: 4 / 5,
        borderRadius:
          radius.lg,
        backgroundColor:
          colors.graphite,
      },

      imagePlaceholder: {
        width: "100%",
        minHeight: 280,
        padding:
          spacing.xl,
        borderRadius:
          radius.lg,
        borderWidth: 1,
        borderStyle:
          "dashed",
        borderColor:
          colors.border,
        backgroundColor:
          colors.surfaceSecondary,
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.sm,
      },

      placeholderTitle: {
        marginTop:
          spacing.sm,
        textAlign:
          "center",
        fontFamily:
          fonts.display,
        fontSize: 20,
        color:
          colors.onSurface,
      },

      placeholderText: {
        textAlign:
          "center",
        fontFamily:
          fonts.sans,
        fontSize: 12,
        color:
          colors.muted,
      },

      mediaActions: {
        flexDirection:
          "row",
        gap: spacing.sm,
      },

      mediaButton: {
        flex: 1,
        minHeight: 46,
        borderRadius:
          radius.pill,
        borderWidth: 1,
        borderColor:
          colors.border,
        backgroundColor:
          colors.surfaceSecondary,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "center",
        gap: spacing.sm,
      },

      mediaButtonText: {
        fontFamily:
          fonts.sansMedium,
        fontSize: 12,
        color:
          colors.onSurface,
      },

      loadingRow: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.sm,
      },

      choiceList: {
        gap: spacing.sm,
      },

      choice: {
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
          colors.surfaceSecondary,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.sm,
      },

      choiceSelected: {
        borderColor:
          colors.plum,
        backgroundColor:
          colors.plumSoft,
      },

      choiceText: {
        flex: 1,
        fontFamily:
          fonts.sansMedium,
        fontSize: 13,
        color:
          colors.onSurfaceSecondary,
      },

      choiceTextSelected: {
        color:
          colors.onSurface,
      },

      textArea: {
        minHeight: 130,
        padding:
          spacing.md,
        borderRadius:
          radius.md,
        borderWidth: 1,
        borderColor:
          colors.border,
        backgroundColor:
          colors.surfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 14,
        lineHeight: 20,
        color:
          colors.onSurface,
      },

      counter: {
        alignSelf:
          "flex-end",
        fontFamily:
          fonts.sans,
        fontSize: 10,
        color:
          colors.muted,
      },

      hint: {
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 18,
        color:
          colors.muted,
      },

      publishCard: {
        marginTop:
          spacing.xxl,
        padding:
          spacing.lg,
        borderRadius:
          radius.lg,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
        backgroundColor:
          colors.surfaceSecondary,
        gap: spacing.md,
      },

      publishTitle: {
        fontFamily:
          fonts.display,
        fontSize: 22,
        color:
          colors.onSurface,
      },

      emptyCard: {
        marginTop:
          spacing.xxl,
        padding:
          spacing.xl,
        borderRadius:
          radius.lg,
        borderWidth: 1,
        borderColor:
          colors.border,
        backgroundColor:
          colors.surfaceSecondary,
        alignItems:
          "center",
        gap: spacing.md,
      },

      emptyTitle: {
        fontFamily:
          fonts.display,
        fontSize: 22,
        textAlign:
          "center",
        color:
          colors.onSurface,
      },

      emptyText: {
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 18,
        textAlign:
          "center",
        color:
          colors.muted,
      },

      bottomSpace: {
        height: 40,
      },
    }),
  );
