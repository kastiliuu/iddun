import React, {
  useEffect,
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
import { Image } from "expo-image";
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import * as Haptics from "expo-haptics";

import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import { useToast } from "@/components/Toast";

import {
  getCurrentUser,
} from "@/api/auth";

import {
  getProfessionalOnboarding,
  saveEstablishmentDraft,
  saveProfessionalDraft,
} from "@/api/onboarding";

import {
  store,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

type AccountType =
  | "professional"
  | "establishment";

type CategoryOption = {
  id: string;
  label: string;
};

const categoryOptions: CategoryOption[] = [
  {
    id: "cabelo",
    label: "Cabelo",
  },
  {
    id: "unhas",
    label: "Unhas",
  },
  {
    id: "barbearia",
    label: "Barbearia",
  },
  {
    id: "estetica",
    label: "Estética",
  },
  {
    id: "maquiagem",
    label: "Maquiagem",
  },
  {
    id: "sobrancelhas",
    label: "Sobrancelhas",
  },
  {
    id: "tatuagem",
    label: "Tatuagem",
  },
  {
    id: "massagem",
    label: "Massagem",
  },
];

export default function SignupProfessionalScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const toast = useToast();

  const params =
    useLocalSearchParams<{
      name?: string;
      email?: string;
    }>();

  const [accountType, setAccountType] =
    useState<AccountType>(
      "professional",
    );

  const [name, setName] =
    useState(
      params.name ??
        "",
    );

  const [businessName, setBusinessName] =
    useState("");

  const [email, setEmail] =
    useState(
      params.email ??
        "",
    );

  const [phone, setPhone] =
    useState("");

  const [city, setCity] =
    useState(
      "Curitiba",
    );

  const [state, setState] =
    useState(
      "PR",
    );

  const [neighborhood, setNeighborhood] =
    useState("");

  const [specialty, setSpecialty] =
    useState("");

  const [selectedCategories, setSelectedCategories] =
    useState<string[]>([]);

  const [bio, setBio] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  useEffect(
    () => {
      let mounted = true;

      const hydrate =
        async () => {
          const currentUser =
            store.getUser();

          if (
            mounted &&
            currentUser
          ) {
            setName(
              (value) =>
                value ||
                currentUser.name,
            );
            setEmail(
              (value) =>
                value ||
                currentUser.email,
            );
          }

          try {
            const response =
              await getProfessionalOnboarding();

            if (
              !mounted ||
              !response.profile
            ) {
              return;
            }

            const profile =
              response.profile;

            setAccountType(
              "professional",
            );
            setName(
              profile.displayName,
            );
            setSpecialty(
              profile.primarySpecialty ||
                "",
            );
            setSelectedCategories(
              profile.categories,
            );
            setCity(
              profile.city ||
                "Curitiba",
            );
            setState(
              profile.state ||
                "PR",
            );
            setBio(
              profile.bio,
            );
            setPhone(
              profile.phone,
            );
          } catch {
            // Uma falha de rede não apaga o que a pessoa já digitou.
          }
        };

      void hydrate();

      return () => {
        mounted = false;
      };
    },
    [],
  );

  const isEstablishment =
    accountType ===
    "establishment";

  const displayName =
    isEstablishment
      ? businessName.trim()
      : name.trim();

  const canContinue =
    useMemo(() => {
      if (!name.trim()) {
        return false;
      }

      if (!email.trim()) {
        return false;
      }

      if (!city.trim()) {
        return false;
      }

      if (
        state.trim().length !== 2
      ) {
        return false;
      }

      if (!specialty.trim()) {
        return false;
      }

      if (
        selectedCategories.length ===
        0
      ) {
        return false;
      }

      if (
        isEstablishment &&
        !businessName.trim()
      ) {
        return false;
      }

      return true;
    }, [
      name,
      email,
      city,
      state,
      specialty,
      selectedCategories,
      isEstablishment,
      businessName,
    ]);

  const toggleCategory = (
    categoryId: string,
  ) => {
    Haptics.selectionAsync().catch(
      () => {},
    );

    setSelectedCategories(
      (current) => {
        if (
          current.includes(
            categoryId,
          )
        ) {
          return current.filter(
            (item) =>
              item !==
              categoryId,
          );
        }

        return [
          ...current,
          categoryId,
        ];
      },
    );
  };

  const handleSubmit =
    async () => {
      if (!canContinue) {
        toast.show({
          title:
            "Complete seu perfil",
          body:
            "Preencha os campos obrigatórios antes de continuar.",
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

        if (isEstablishment) {
          const firstCategory =
            selectedCategories[0];

          const categoryMap:
            Record<string, string> = {
              cabelo: "salao",
              unhas: "unhas",
              barbearia: "barbearia",
              estetica: "estetica",
              maquiagem: "salao",
              sobrancelhas: "salao",
              tatuagem: "tatuagem",
              massagem: "bem-estar",
            };

          await saveEstablishmentDraft({
            name:
              businessName.trim(),
            category:
              categoryMap[
                firstCategory
              ] || "multisservicos",
            city: city.trim(),
            state:
              state.trim().toUpperCase(),
            description:
              bio.trim(),
            phone:
              phone.trim(),
            neighborhood:
              neighborhood.trim(),
          });

          toast.show({
            title:
              "Estabelecimento salvo",
            body:
              "Seu rascunho está salvo no IDDUN e pode ser retomado depois.",
            icon:
              "check",
          });

          router.replace(
            "/(tabs)/profile",
          );
        } else {
          await saveProfessionalDraft({
            displayName:
              name.trim(),
            primarySpecialty:
              specialty.trim(),
            categories:
              selectedCategories,
            city:
              city.trim(),
            state:
              state.trim().toUpperCase(),
            bio:
              bio.trim(),
            phone:
              phone.trim(),
          });

          await getCurrentUser();

          toast.show({
            title:
              "Perfil salvo",
            body:
              "Seu rascunho profissional agora é real e fica salvo na sua conta.",
            icon:
              "check",
          });

          router.replace(
            "/professional-onboarding",
          );
        }
      } finally {
        setLoading(false);
      }
    };

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
                  "/(tabs)/profile",
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

          <Image
            source={require(
              "../../../assets/branding/iddun-logo-white.png",
            )}
            style={
              styles.logo
            }
            contentFit="contain"
            accessibilityLabel="IDDUN"
          />

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
            IDDUN PROFISSIONAL
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Transforme seu trabalho em presença.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Crie seu perfil profissional, publique trabalhos, ofereça serviços e seja descoberto por novos clientes.
          </Text>
        </View>

        <View
          style={
            styles.typeSection
          }
        >
          <Text
            style={
              styles.fieldLabel
            }
          >
            Como você trabalha?
          </Text>

          <View
            style={
              styles.typeOptions
            }
          >
            <Pressable
              accessibilityRole="button"
              accessibilityState={{
                selected:
                  accountType ===
                  "professional",
              }}
              onPress={() =>
                setAccountType(
                  "professional",
                )
              }
              style={({
                pressed,
              }) => [
                styles.typeCard,

                accountType ===
                  "professional" &&
                  styles.typeCardSelected,

                pressed &&
                  styles.pressed,
              ]}
            >
              <View
                style={
                  styles.typeIcon
                }
              >
                <Icon
                  name="user"
                  size={20}
                  color={
                    accountType ===
                    "professional"
                      ? colors.plum
                      : colors.muted
                  }
                />
              </View>

              <Text
                style={
                  styles.typeTitle
                }
              >
                Profissional
              </Text>

              <Text
                style={
                  styles.typeDescription
                }
              >
                Trabalho de forma independente ou dentro de um espaço.
              </Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              accessibilityState={{
                selected:
                  accountType ===
                  "establishment",
              }}
              onPress={() =>
                setAccountType(
                  "establishment",
                )
              }
              style={({
                pressed,
              }) => [
                styles.typeCard,

                accountType ===
                  "establishment" &&
                  styles.typeCardSelected,

                pressed &&
                  styles.pressed,
              ]}
            >
              <View
                style={
                  styles.typeIcon
                }
              >
                <Icon
                  name="home"
                  size={20}
                  color={
                    accountType ===
                    "establishment"
                      ? colors.plum
                      : colors.muted
                  }
                />
              </View>

              <Text
                style={
                  styles.typeTitle
                }
              >
                Estabelecimento
              </Text>

              <Text
                style={
                  styles.typeDescription
                }
              >
                Salão, studio, barbearia, clínica ou outro espaço com equipe.
              </Text>
            </Pressable>
          </View>
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
                styles.fieldLabel
              }
            >
              Seu nome *
            </Text>

            <TextInput
              value={name}
              onChangeText={
                setName
              }
              placeholder="Nome completo"
              placeholderTextColor={
                colors.muted
              }
              autoCapitalize="words"
              style={
                styles.input
              }
            />
          </View>

          {isEstablishment ? (
            <View
              style={
                styles.field
              }
            >
              <Text
                style={
                  styles.fieldLabel
                }
              >
                Nome do estabelecimento *
              </Text>

              <TextInput
                value={
                  businessName
                }
                onChangeText={
                  setBusinessName
                }
                placeholder="Ex.: Atelier Lumi"
                placeholderTextColor={
                  colors.muted
                }
                autoCapitalize="words"
                style={
                  styles.input
                }
              />
            </View>
          ) : null}

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.fieldLabel
              }
            >
              E-mail *
            </Text>

            <TextInput
              value={email}
              onChangeText={
                setEmail
              }
              placeholder="seu@email.com"
              placeholderTextColor={
                colors.muted
              }
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              editable={false}
              style={[
                styles.input,
                styles.inputDisabled,
              ]}
            />
          </View>

          <View
            style={
              styles.field
            }
          >
            <Text
              style={
                styles.fieldLabel
              }
            >
              Telefone
            </Text>

            <TextInput
              value={phone}
              onChangeText={
                setPhone
              }
              placeholder="(41) 99999-9999"
              placeholderTextColor={
                colors.muted
              }
              keyboardType="phone-pad"
              style={
                styles.input
              }
            />
          </View>

          <View
            style={
              styles.row
            }
          >
            <View
              style={[
                styles.field,
                styles.rowField,
              ]}
            >
              <Text
                style={
                  styles.fieldLabel
                }
              >
                Cidade *
              </Text>

              <TextInput
                value={city}
                onChangeText={
                  setCity
                }
                placeholder="Cidade"
                placeholderTextColor={
                  colors.muted
                }
                style={
                  styles.input
                }
              />
            </View>

            <View
              style={[
                styles.field,
                styles.rowField,
              ]}
            >
              <Text
                style={
                  styles.fieldLabel
                }
              >
                UF *
              </Text>

              <TextInput
                value={state}
                onChangeText={(value) =>
                  setState(
                    value
                      .replace(
                        /[^a-zA-Z]/g,
                        "",
                      )
                      .slice(0, 2)
                      .toUpperCase(),
                  )
                }
                placeholder="PR"
                placeholderTextColor={
                  colors.muted
                }
                autoCapitalize="characters"
                maxLength={2}
                style={
                  styles.input
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
                styles.fieldLabel
              }
            >
              Bairro
            </Text>

            <TextInput
              value={neighborhood}
              onChangeText={
                setNeighborhood
              }
              placeholder="Bairro"
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
                styles.fieldLabel
              }
            >
              Especialidade *
            </Text>

            <TextInput
              value={
                specialty
              }
              onChangeText={
                setSpecialty
              }
              placeholder={
                isEstablishment
                  ? "Ex.: Hair & Beauty Studio"
                  : "Ex.: Nail Designer"
              }
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
                styles.fieldLabel
              }
            >
              Categorias *
            </Text>

            <Text
              style={
                styles.fieldHint
              }
            >
              Escolha uma ou mais áreas do seu trabalho.
            </Text>

            <View
              style={
                styles.categories
              }
            >
              {categoryOptions.map(
                (category) => {
                  const selected =
                    selectedCategories.includes(
                      category.id,
                    );

                  return (
                    <Pressable
                      key={
                        category.id
                      }
                      accessibilityRole="button"
                      accessibilityState={{
                        selected,
                      }}
                      onPress={() =>
                        toggleCategory(
                          category.id,
                        )
                      }
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
                            colors.onBrandPrimary
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
                        {
                          category.label
                        }
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
                styles.fieldLabel
              }
            >
              Bio
            </Text>

            <TextInput
              value={bio}
              onChangeText={
                setBio
              }
              placeholder={
                isEstablishment
                  ? "Conte um pouco sobre o espaço, conceito e experiência..."
                  : "Conte um pouco sobre você, sua experiência e estilo de trabalho..."
              }
              placeholderTextColor={
                colors.muted
              }
              multiline
              maxLength={300}
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
              {bio.length}/300
            </Text>
          </View>
        </View>

        <View
          style={
            styles.previewCard
          }
        >
          <Text
            style={
              styles.previewEyebrow
            }
          >
            PRÉVIA DO PERFIL
          </Text>

          <View
            style={
              styles.previewHeader
            }
          >
            <View
              style={
                styles.previewAvatar
              }
            >
              <Text
                style={
                  styles.previewAvatarText
                }
              >
                {(
                  displayName ||
                  "I"
                )
                  .charAt(0)
                  .toUpperCase()}
              </Text>
            </View>

            <View
              style={
                styles.previewContent
              }
            >
              <Text
                style={
                  styles.previewName
                }
                numberOfLines={1}
              >
                {displayName ||
                  "Seu perfil"}
              </Text>

              <Text
                style={
                  styles.previewSpecialty
                }
                numberOfLines={1}
              >
                {specialty ||
                  "Sua especialidade"}
              </Text>

              <View
                style={
                  styles.previewMeta
                }
              >
                <Icon
                  name="map-pin"
                  size={11}
                  color={
                    colors.muted
                  }
                />

                <Text
                  style={
                    styles.previewMetaText
                  }
                  numberOfLines={1}
                >
                  {neighborhood
                    ? `${neighborhood} · ${city}`
                    : city}
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
            name="shield"
            size={19}
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
              Seu perfil ainda poderá ser editado
            </Text>

            <Text
              style={
                styles.infoText
              }
            >
              Depois do cadastro você poderá adicionar foto, capa, serviços, portfólio, horários e outras informações profissionais.
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
              isEstablishment
                ? "Criar estabelecimento"
                : "Criar perfil profissional"
            }
            onPress={
              handleSubmit
            }
            disabled={
              !canContinue
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

const useStyles = makeStyles(
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

    headerPlaceholder: {
      width:
        touch.minimum,

      height:
        touch.minimum,
    },

    logo: {
      width: 104,
      height: 32,
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
      maxWidth: 350,

      marginTop:
        spacing.sm,

      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 32,
      lineHeight: 38,

      letterSpacing: -0.4,
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

    typeSection: {
      marginTop:
        spacing.xxl,
    },

    typeOptions: {
      marginTop:
        spacing.sm,

      gap:
        spacing.sm,
    },

    typeCard: {
      minHeight: 112,

      padding:
        spacing.lg,

      borderRadius:
        radius.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    typeCardSelected: {
      backgroundColor:
        colors.plumSoft,

      borderColor:
        colors.plum,
    },

    typeIcon: {
      width: 40,
      height: 40,

      borderRadius:
        radius.md,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.glassSoft,
    },

    typeTitle: {
      marginTop:
        spacing.md,

      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 14,
      lineHeight: 18,
    },

    typeDescription: {
      marginTop:
        spacing.xs,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 17,
    },

    form: {
      marginTop:
        spacing.xxxl,

      gap:
        spacing.lg,
    },

    field: {
      gap:
        spacing.sm,
    },

    row: {
      flexDirection:
        "row",

      gap:
        spacing.sm,
    },

    rowField: {
      flex: 1,
    },

    fieldLabel: {
      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sansMedium,

      fontSize: 11,
      lineHeight: 15,
    },

    fieldHint: {
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
      minHeight: 116,

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
      lineHeight: 15,
    },

    categoryTextSelected: {
      color:
        colors.onBrandPrimary,
    },

    previewCard: {
      marginTop:
        spacing.xxxl,

      padding:
        spacing.lg,

      borderRadius:
        radius.md,

      backgroundColor:
        colors.surfaceSecondary,

      borderWidth: 1,

      borderColor:
        colors.glassBorder,
    },

    previewEyebrow: {
      color:
        colors.plum,

      fontFamily:
        fonts.sansMedium,

      fontSize: 9,
      lineHeight: 12,

      letterSpacing: 1.2,
    },

    previewHeader: {
      marginTop:
        spacing.lg,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap:
        spacing.md,
    },

    previewAvatar: {
      width: 58,
      height: 58,

      borderRadius: 29,

      alignItems:
        "center",

      justifyContent:
        "center",

      backgroundColor:
        colors.plumSoft,

      borderWidth: 1,

      borderColor:
        colors.plum,
    },

    previewAvatarText: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.display,

      fontSize: 21,
      lineHeight: 26,
    },

    previewContent: {
      flex: 1,

      minWidth: 0,
    },

    previewName: {
      color:
        colors.onSurface,

      fontFamily:
        fonts.sansSemiBold,

      fontSize: 15,
      lineHeight: 19,
    },

    previewSpecialty: {
      marginTop: 2,

      color:
        colors.onSurfaceSecondary,

      fontFamily:
        fonts.sans,

      fontSize: 11,
      lineHeight: 14,
    },

    previewMeta: {
      marginTop:
        spacing.xs,

      flexDirection:
        "row",

      alignItems:
        "center",

      gap:
        spacing.xs,
    },

    previewMetaText: {
      flex: 1,

      color:
        colors.muted,

      fontFamily:
        fonts.sans,

      fontSize: 10,
      lineHeight: 13,
    },

    infoCard: {
      marginTop:
        spacing.lg,

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

    bottomSpace: {
      height: 64,
    },

    pressed: {
      opacity: 0.76,
    },
  }),
);