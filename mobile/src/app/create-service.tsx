import React, {
  useMemo,
  useState,
} from "react";
import {
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import * as Haptics from "expo-haptics";

import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toast";

import {
  getServiceById,
} from "@/mocks/data";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import {
  createService,
  updateService,
} from "@/api/services";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

const categoryOptions = [
  "Cabelo",
  "Unhas",
  "Barbearia",
  "Estética",
  "Maquiagem",
  "Sobrancelhas",
  "Tatuagem",
  "Massagem",
];

const durationOptions = [
  30,
  45,
  60,
  90,
  120,
  150,
  180,
];

function onlyNumbers(
  value: string,
) {
  return value.replace(
    /[^0-9]/g,
    "",
  );
}

function currencyInputToNumber(
  value: string,
) {
  const digits =
    onlyNumbers(value);

  if (!digits) {
    return 0;
  }

  return (
    Number(digits) / 100
  );
}

function numberToCurrencyInput(
  value: number,
) {
  return Math.round(
    value * 100,
  ).toString();
}

function formatCurrencyInput(
  value: string,
) {
  const number =
    currencyInputToNumber(
      value,
    );

  return new Intl.NumberFormat(
    "pt-BR",
    {
      style: "currency",
      currency: "BRL",
    },
  ).format(number);
}

export default function CreateServiceScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const params =
    useLocalSearchParams<{
      serviceId?: string;
    }>();

  const user =
    store.getUser();

  const existingService =
    useMemo(
      () =>
        params.serviceId
          ? getServiceById(
              params.serviceId,
            )
          : undefined,
      [params.serviceId],
    );

  const isEditing =
    Boolean(existingService);

  const [name, setName] =
    useState(
      existingService?.name ??
        "",
    );

  const [description, setDescription] =
    useState(
      existingService?.description ??
        "",
    );

  const [category, setCategory] =
    useState(
      existingService?.category ??
        "",
    );

  const [priceInput, setPriceInput] =
    useState(
      existingService
        ? numberToCurrencyInput(
            existingService.price,
          )
        : "",
    );

  const [durationMinutes, setDurationMinutes] =
    useState(
      existingService?.durationMinutes ??
        60,
    );

  const [location, setLocation] =
    useState(
      existingService?.location ??
        "",
    );

  const [imageUrl, setImageUrl] =
    useState(
      existingService?.image ??
        "",
    );

  const [loading, setLoading] =
    useState(false);

  const canManage =
    user?.role ===
      "professional" ||
    user?.role ===
      "establishment";

  const price =
    currencyInputToNumber(
      priceInput,
    );

  const canSubmit =
    name.trim().length >= 2 &&
    description.trim().length >= 5 &&
    category.length > 0 &&
    price > 0 &&
    durationMinutes > 0;

  const handlePriceChange = (
    value: string,
  ) => {
    setPriceInput(
      onlyNumbers(value),
    );
  };

  const handleSubmit =
    async () => {
      if (!canSubmit) {
        toast.show({
          title:
            "Revise o serviço",
          body:
            "Preencha nome, descrição, categoria, valor e duração.",
          icon:
            "alert-circle",
        });

        return;
      }

      try {
        setLoading(true);

        Haptics.impactAsync(
          Haptics
            .ImpactFeedbackStyle
            .Medium,
        ).catch(() => {});

        const payload = {
          name:
            name.trim(),

          description:
            description.trim(),

          category,

          price,

          durationMinutes,

          location:
            location.trim() ||
            null,

          imageUrl:
            imageUrl.trim() ||
            null,
        };

        if (
          isEditing &&
          existingService
        ) {
          await updateService(
            existingService.id,
            payload,
          );

          toast.show({
            title:
              "Serviço atualizado",
            body:
              "As alterações foram salvas.",
            icon:
              "check",
          });
        } else {
          await createService(
            payload,
          );

          toast.show({
            title:
              "Serviço criado",
            body:
              "Seu novo serviço já pode ser preparado para receber horários.",
            icon:
              "check",
          });
        }

        router.replace(
          "/manage-services",
        );
      } catch (error) {
        toast.show({
          title:
            "Não foi possível salvar",
          body:
            error instanceof Error
              ? error.message
              : "Tente novamente em alguns instantes.",
          icon:
            "alert-circle",
        });
      } finally {
        setLoading(false);
      }
    };

  if (!user || !canManage) {
    return (
      <View
        style={
          styles.container
        }
      >
        <View
          style={
            styles.simpleHeader
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
                  "/(tabs)/create",
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
        </View>

        <View
          style={
            styles.restricted
          }
        >
          <View
            style={
              styles.restrictedIcon
            }
          >
            <Icon
              name="lock"
              size={25}
              color={
                colors.plum
              }
            />
          </View>

          <Text
            style={
              styles.restrictedTitle
            }
          >
            Área profissional
          </Text>

          <Text
            style={
              styles.restrictedText
            }
          >
            Apenas profissionais e estabelecimentos podem cadastrar serviços.
          </Text>

          <Button
            title="Voltar"
            variant="secondary"
            onPress={() =>
              router.replace(
                "/(tabs)/create",
              )
            }
            fullWidth
          />
        </View>
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
        showsVerticalScrollIndicator={
          false
        }
        keyboardShouldPersistTaps="handled"
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
                  "/manage-services",
                );
              }
            }}
            style={({
              pressed,
            }) => [
              styles.headerButton,
              pressed &&
                styles.pressed,
            ]}
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
            {isEditing
              ? "Editar serviço"
              : "Novo serviço"}
          </Text>

          <View
            style={
              styles.headerPlaceholder
            }
          />
        </View>

        <View
          style={
            styles.intro
          }
        >
          <Text
            style={
              styles.eyebrow
            }
          >
            SERVIÇOS
          </Text>

          <Text
            style={
              styles.title
            }
          >
            {isEditing
              ? "Ajuste os detalhes."
              : "Crie uma experiência."}
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Informações claras ajudam o cliente a entender exatamente o que será agendado.
          </Text>
        </View>

        <View
          style={
            styles.form
          }
        >
          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Nome do serviço *
            </Text>

            <TextInput
              value={name}
              onChangeText={
                setName
              }
              placeholder="Ex.: Alongamento em Fibra"
              placeholderTextColor={
                colors.muted
              }
              autoCapitalize="sentences"
              maxLength={80}
              style={
                styles.input
              }
            />

            <Text
              style={
                styles.counter
              }
            >
              {name.length}/80
            </Text>
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Categoria *
            </Text>

            <View
              style={
                styles.categories
              }
            >
              {categoryOptions.map(
                (item) => {
                  const selected =
                    category ===
                    item;

                  return (
                    <Pressable
                      key={
                        item
                      }
                      accessibilityRole="button"
                      accessibilityState={{
                        selected,
                      }}
                      onPress={() => {
                        setCategory(
                          item,
                        );

                        Haptics.selectionAsync().catch(
                          () => {},
                        );
                      }}
                      style={({
                        pressed,
                      }) => [
                        styles.categoryChip,

                        selected &&
                          styles.categoryChipSelected,

                        pressed &&
                          styles.pressed,
                      ]}
                    >
                      {selected ? (
                        <Icon
                          name="check"
                          size={13}
                          color={
                            colors
                              .onBrandPrimary
                          }
                        />
                      ) : null}

                      <Text
                        style={[
                          styles.categoryText,

                          selected &&
                            styles.categoryTextSelected,
                        ]}
                      >
                        {item}
                      </Text>
                    </Pressable>
                  );
                },
              )}
            </View>
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Descrição *
            </Text>

            <TextInput
              value={
                description
              }
              onChangeText={
                setDescription
              }
              placeholder="Explique como funciona o serviço, técnicas utilizadas e o que está incluído."
              placeholderTextColor={
                colors.muted
              }
              multiline
              maxLength={500}
              textAlignVertical="top"
              style={[
                styles.input,
                styles.textArea,
              ]}
            />

            <Text
              style={
                styles.counter
              }
            >
              {description.length}/500
            </Text>
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Valor *
            </Text>

            <View
              style={
                styles.priceInputWrap
              }
            >
              <Text
                style={
                  styles.pricePrefix
                }
              >
                R$
              </Text>

              <TextInput
                value={
                  priceInput
                    ? formatCurrencyInput(
                        priceInput,
                      ).replace(
                        "R$",
                        "",
                      ).trim()
                    : ""
                }
                onChangeText={
                  handlePriceChange
                }
                placeholder="0,00"
                placeholderTextColor={
                  colors.muted
                }
                keyboardType="numeric"
                style={
                  styles.priceInput
                }
              />
            </View>
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Duração *
            </Text>

            <Text
              style={
                styles.hint
              }
            >
              Tempo total reservado na agenda.
            </Text>

            <View
              style={
                styles.durationGrid
              }
            >
              {durationOptions.map(
                (minutes) => {
                  const selected =
                    durationMinutes ===
                    minutes;

                  const label =
                    minutes < 60
                      ? `${minutes} min`
                      : minutes %
                            60 ===
                          0
                        ? `${minutes / 60}h`
                        : `${Math.floor(
                            minutes /
                              60,
                          )}h ${
                            minutes %
                            60
                          }min`;

                  return (
                    <Pressable
                      key={
                        minutes
                      }
                      accessibilityRole="button"
                      accessibilityState={{
                        selected,
                      }}
                      onPress={() => {
                        setDurationMinutes(
                          minutes,
                        );

                        Haptics.selectionAsync().catch(
                          () => {},
                        );
                      }}
                      style={({
                        pressed,
                      }) => [
                        styles.durationButton,

                        selected &&
                          styles.durationButtonSelected,

                        pressed &&
                          styles.pressed,
                      ]}
                    >
                      <Text
                        style={[
                          styles.durationText,

                          selected &&
                            styles.durationTextSelected,
                        ]}
                      >
                        {label}
                      </Text>
                    </Pressable>
                  );
                },
              )}
            </View>
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Local
            </Text>

            <TextInput
              value={location}
              onChangeText={
                setLocation
              }
              placeholder="Ex.: Batel · Curitiba"
              placeholderTextColor={
                colors.muted
              }
              style={
                styles.input
              }
            />
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.label
              }
            >
              Imagem
            </Text>

            <Text
              style={
                styles.hint
              }
            >
              Por enquanto usamos URL. O upload real de imagens entra na integração de storage.
            </Text>

            <TextInput
              value={imageUrl}
              onChangeText={
                setImageUrl
              }
              placeholder="https://..."
              placeholderTextColor={
                colors.muted
              }
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              style={
                styles.input
              }
            />
          </View>
        </View>

        <View
          style={
            styles.preview
          }
        >
          <Text
            style={
              styles.previewEyebrow
            }
          >
            PRÉVIA
          </Text>

          <View
            style={
              styles.previewCard
            }
          >
            <View
              style={
                styles.previewIcon
              }
            >
              <Icon
                name="scissors"
                size={21}
                color={
                  colors.plum
                }
              />
            </View>

            <View
              style={
                styles.previewContent
              }
            >
              <Text
                style={
                  styles.previewCategory
                }
              >
                {category
                  ? category.toUpperCase()
                  : "CATEGORIA"}
              </Text>

              <Text
                style={
                  styles.previewName
                }
                numberOfLines={1}
              >
                {name.trim() ||
                  "Nome do serviço"}
              </Text>

              <View
                style={
                  styles.previewMeta
                }
              >
                <Text
                  style={
                    styles.previewPrice
                  }
                >
                  {price > 0
                    ? new Intl.NumberFormat(
                        "pt-BR",
                        {
                          style:
                            "currency",
                          currency:
                            "BRL",
                        },
                      ).format(
                        price,
                      )
                    : "R$ 0,00"}
                </Text>

                <View
                  style={
                    styles.dot
                  }
                />

                <Text
                  style={
                    styles.previewDuration
                  }
                >
                  {durationMinutes <
                  60
                    ? `${durationMinutes} min`
                    : `${Math.floor(
                        durationMinutes /
                          60,
                      )}h${
                        durationMinutes %
                          60
                          ? ` ${
                              durationMinutes %
                              60
                            }min`
                          : ""
                      }`}
                </Text>
              </View>
            </View>
          </View>
        </View>

        <View
          style={
            styles.infoCard
          }
        >
          <Icon
            name="info"
            size={18}
            color={
              colors.plum
            }
          />

          <View
            style={
              styles.infoContent
            }
          >
            <Text
              style={
                styles.infoTitle
              }
            >
              O serviço não abre agenda sozinho
            </Text>

            <Text
              style={
                styles.infoText
              }
            >
              Depois de cadastrar o serviço, você poderá definir horários e disponibilidades separadamente.
            </Text>
          </View>
        </View>

        <View
          style={
            styles.submitArea
          }
        >
          <Button
            title={
              isEditing
                ? "Salvar alterações"
                : "Criar serviço"
            }
            onPress={
              handleSubmit
            }
            disabled={
              !canSubmit
            }
            loading={
              loading
            }
            fullWidth
          />
        </View>

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
      container: {
        flex: 1,
        backgroundColor:
          colors.surface,
      },

      content: {
        paddingTop: 54,
        paddingHorizontal:
          spacing.lg,
      },

      simpleHeader: {
        paddingTop: 54,
        paddingHorizontal:
          spacing.lg,
      },

      header: {
        minHeight: 52,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "space-between",
      },

      headerButton: {
        width:
          touch.minimum,
        height:
          touch.minimum,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.glassSoft,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      headerTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 13,
        lineHeight: 17,
      },

      headerPlaceholder: {
        width:
          touch.minimum,
        height:
          touch.minimum,
      },

      intro: {
        marginTop:
          spacing.xl,
      },

      eyebrow: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 10,
        lineHeight: 14,
        letterSpacing: 1.5,
      },

      title: {
        marginTop:
          spacing.sm,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 32,
        lineHeight: 38,
      },

      description: {
        maxWidth: 340,
        marginTop:
          spacing.md,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 13,
        lineHeight: 20,
      },

      form: {
        marginTop:
          spacing.xxxl,
        gap:
          spacing.xl,
      },

      field: {
        gap:
          spacing.sm,
      },

      label: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
        lineHeight: 15,
      },

      hint: {
        marginTop: -4,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 15,
      },

      input: {
        minHeight: 50,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.md,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sans,
        fontSize: 13,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      textArea: {
        minHeight: 136,
        paddingTop:
          spacing.md,
        paddingBottom:
          spacing.md,
      },

      counter: {
        alignSelf:
          "flex-end",
        marginTop: -4,
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 9,
        lineHeight: 12,
      },

      categories: {
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap:
          spacing.sm,
      },

      categoryChip: {
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.pill,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "center",
        gap:
          spacing.xs,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      categoryChipSelected: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },

      categoryText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },

      categoryTextSelected: {
        color:
          colors.onBrandPrimary,
      },

      priceInputWrap: {
        minHeight: 50,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "center",
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      pricePrefix: {
        marginRight:
          spacing.sm,
        color:
          colors.muted,
        fontFamily:
          fonts.sansMedium,
        fontSize: 13,
      },

      priceInput: {
        flex: 1,
        minHeight: 48,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 15,
      },

      durationGrid: {
        flexDirection:
          "row",
        flexWrap:
          "wrap",
        gap:
          spacing.sm,
      },

      durationButton: {
        minWidth: 76,
        minHeight:
          touch.minimum,
        paddingHorizontal:
          spacing.md,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      durationButtonSelected: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },

      durationText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },

      durationTextSelected: {
        color:
          colors.onBrandPrimary,
      },

      preview: {
        marginTop:
          spacing.xxxl,
      },

      previewEyebrow: {
        marginBottom:
          spacing.sm,
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        lineHeight: 12,
        letterSpacing: 1.2,
      },

      previewCard: {
        minHeight: 90,
        padding:
          spacing.md,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      previewIcon: {
        width: 52,
        height: 52,
        borderRadius:
          radius.md,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plumSoft,
      },

      previewContent: {
        flex: 1,
        minWidth: 0,
      },

      previewCategory: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 8,
        lineHeight: 11,
        letterSpacing: 0.8,
      },

      previewName: {
        marginTop: 2,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 14,
        lineHeight: 18,
      },

      previewMeta: {
        marginTop:
          spacing.xs,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.sm,
      },

      previewPrice: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },

      previewDuration: {
        color:
          colors.muted,
        fontFamily:
          fonts.sans,
        fontSize: 10,
      },

      dot: {
        width: 3,
        height: 3,
        borderRadius: 2,
        backgroundColor:
          colors.muted,
      },

      infoCard: {
        marginTop:
          spacing.xxl,
        padding:
          spacing.lg,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "flex-start",
        gap:
          spacing.md,
        backgroundColor:
          colors.plumSoft,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      infoContent: {
        flex: 1,
      },

      infoTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 12,
        lineHeight: 16,
      },

      infoText: {
        marginTop:
          spacing.xs,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 16,
      },

      submitArea: {
        marginTop:
          spacing.xxl,
      },

      restricted: {
        marginTop: 150,
        paddingHorizontal:
          spacing.lg,
        alignItems:
          "center",
      },

      restrictedIcon: {
        width: 64,
        height: 64,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plumSoft,
      },

      restrictedTitle: {
        marginTop:
          spacing.lg,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 26,
        lineHeight: 32,
      },

      restrictedText: {
        maxWidth: 320,
        marginTop:
          spacing.sm,
        marginBottom:
          spacing.xl,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 18,
        textAlign:
          "center",
      },

      bottomSpace: {
        height: 72,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );