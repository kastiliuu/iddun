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
import { Image } from "expo-image";
import { useRouter } from "expo-router";

import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";

import {
  getServicesByAuthorId,
} from "@/mocks/data";

import {
  store,
  useStoreVersion,
} from "@/store/local";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

function formatCurrency(
  value: number,
) {
  return new Intl.NumberFormat(
    "pt-BR",
    {
      style: "currency",
      currency: "BRL",
    },
  ).format(value);
}

function formatDuration(
  minutes: number,
) {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours =
    Math.floor(
      minutes / 60,
    );

  const remaining =
    minutes % 60;

  if (remaining === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remaining}min`;
}

export default function ManageServicesScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();

  const user =
    store.getUser();

  const [search, setSearch] =
    useState("");

  const canManage =
    user?.role ===
      "professional" ||
    user?.role ===
      "establishment";

  const profileId =
    user?.profileId;

  const services =
    useMemo(() => {
      if (!profileId) {
        return [];
      }

      return getServicesByAuthorId(
        profileId,
      );
    }, [profileId]);

  const filteredServices =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      if (!query) {
        return services;
      }

      return services.filter(
        (service) =>
          service.name
            .toLowerCase()
            .includes(query) ||
          service.category
            .toLowerCase()
            .includes(query),
      );
    }, [
      search,
      services,
    ]);

  if (!user) {
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

        <EmptyState
          title="Entre para continuar"
          description="Você precisa estar conectado para gerenciar serviços."
          actionLabel="Entrar"
          onActionPress={() =>
            router.push(
              "/login",
            )
          }
        />
      </View>
    );
  }

  if (!canManage) {
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
            onPress={() =>
              router.back()
            }
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

        <EmptyState
          title="Área profissional"
          description="O gerenciamento de serviços está disponível para profissionais e estabelecimentos."
          actionLabel="Tornar-me profissional"
          onActionPress={() =>
            router.push(
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
                  "/(tabs)/create",
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
              "../../assets/branding/iddun-logo-white.png",
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
            MEU NEGÓCIO
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Serviços
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Organize o que você oferece, valores, duração e disponibilidade.
          </Text>
        </View>

        <View
          style={
            styles.stats
          }
        >
          <View
            style={
              styles.stat
            }
          >
            <Text
              style={
                styles.statValue
              }
            >
              {services.length}
            </Text>

            <Text
              style={
                styles.statLabel
              }
            >
              Serviços
            </Text>
          </View>

          <View
            style={
              styles.statDivider
            }
          />

          <View
            style={
              styles.stat
            }
          >
            <Text
              style={
                styles.statValue
              }
            >
              {
                services.filter(
                  (service) =>
                    Boolean(
                      service.availabilityLabel,
                    ),
                ).length
              }
            </Text>

            <Text
              style={
                styles.statLabel
              }
            >
              Com horário
            </Text>
          </View>
        </View>

        <View
          style={
            styles.actions
          }
        >
          <Button
            title="Novo serviço"
            onPress={() =>
              router.push(
                "/create-service",
              )
            }
            fullWidth
          />
        </View>

        {services.length >
        0 ? (
          <View
            style={
              styles.searchWrap
            }
          >
            <Icon
              name="search"
              size={18}
              color={
                colors.muted
              }
            />

            <TextInput
              value={search}
              onChangeText={
                setSearch
              }
              placeholder="Buscar serviço"
              placeholderTextColor={
                colors.muted
              }
              autoCorrect={false}
              style={
                styles.searchInput
              }
            />

            {search ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Limpar busca"
                onPress={() =>
                  setSearch("")
                }
                style={
                  styles.clearButton
                }
              >
                <Icon
                  name="x"
                  size={17}
                  color={
                    colors.muted
                  }
                />
              </Pressable>
            ) : null}
          </View>
        ) : null}

        <View
          style={
            styles.sectionHeader
          }
        >
          <Text
            style={
              styles.sectionTitle
            }
          >
            Seus serviços
          </Text>

          {services.length >
          0 ? (
            <Text
              style={
                styles.sectionCount
              }
            >
              {
                filteredServices.length
              }
            </Text>
          ) : null}
        </View>

        {filteredServices.length >
        0 ? (
          <View
            style={
              styles.serviceList
            }
          >
            {filteredServices.map(
              (service) => (
                <View
                  key={
                    service.id
                  }
                  style={
                    styles.serviceCard
                  }
                >
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={`Abrir ${service.name}`}
                    onPress={() =>
                      router.push(
                        `/service/${service.id}`,
                      )
                    }
                    style={({
                      pressed,
                    }) => [
                      styles.serviceMain,
                      pressed &&
                        styles.pressed,
                    ]}
                  >
                    <Image
                      source={{
                        uri:
                          service.image,
                      }}
                      style={
                        styles.serviceImage
                      }
                      contentFit="cover"
                      transition={
                        180
                      }
                    />

                    <View
                      style={
                        styles.serviceContent
                      }
                    >
                      <Text
                        style={
                          styles.serviceCategory
                        }
                      >
                        {service.category.toUpperCase()}
                      </Text>

                      <Text
                        style={
                          styles.serviceName
                        }
                        numberOfLines={
                          1
                        }
                      >
                        {
                          service.name
                        }
                      </Text>

                      <View
                        style={
                          styles.serviceMeta
                        }
                      >
                        <Text
                          style={
                            styles.servicePrice
                          }
                        >
                          {formatCurrency(
                            service.price,
                          )}
                        </Text>

                        <View
                          style={
                            styles.dot
                          }
                        />

                        <Text
                          style={
                            styles.serviceDuration
                          }
                        >
                          {formatDuration(
                            service.durationMinutes,
                          )}
                        </Text>
                      </View>

                      {service.availabilityLabel ? (
                        <View
                          style={
                            styles.availability
                          }
                        >
                          <View
                            style={
                              styles.availabilityDot
                            }
                          />

                          <Text
                            style={
                              styles.availabilityText
                            }
                            numberOfLines={
                              1
                            }
                          >
                            {
                              service.availabilityLabel
                            }
                          </Text>
                        </View>
                      ) : null}
                    </View>

                    <Icon
                      name="chevron-right"
                      size={18}
                      color={
                        colors.muted
                      }
                    />
                  </Pressable>

                  <View
                    style={
                      styles.cardActions
                    }
                  >
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`Editar ${service.name}`}
                      onPress={() =>
                        router.push({
                          pathname:
                            "/create-service",
                          params: {
                            serviceId:
                              service.id,
                          },
                        })
                      }
                      style={({
                        pressed,
                      }) => [
                        styles.cardAction,
                        pressed &&
                          styles.pressed,
                      ]}
                    >
                      <Icon
                        name="edit-2"
                        size={15}
                        color={
                          colors.onSurfaceSecondary
                        }
                      />

                      <Text
                        style={
                          styles.cardActionText
                        }
                      >
                        Editar
                      </Text>
                    </Pressable>

                    <View
                      style={
                        styles.actionDivider
                      }
                    />

                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel={`Abrir horários de ${service.name}`}
                      onPress={() =>
                        router.push({
                          pathname:
                            "/open-slot",
                          params: {
                            serviceId:
                              service.id,
                          },
                        })
                      }
                      style={({
                        pressed,
                      }) => [
                        styles.cardAction,
                        pressed &&
                          styles.pressed,
                      ]}
                    >
                      <Icon
                        name="clock"
                        size={15}
                        color={
                          colors.plum
                        }
                      />

                      <Text
                        style={[
                          styles.cardActionText,
                          styles.cardActionPrimary,
                        ]}
                      >
                        Abrir horário
                      </Text>
                    </Pressable>
                  </View>
                </View>
              ),
            )}
          </View>
        ) : services.length >
          0 ? (
          <EmptyState
            title="Nenhum resultado"
            description="Não encontramos serviços com esse termo."
            actionLabel="Limpar busca"
            onActionPress={() =>
              setSearch("")
            }
            compact
          />
        ) : (
          <View
            style={
              styles.emptyCard
            }
          >
            <View
              style={
                styles.emptyIcon
              }
            >
              <Icon
                name="scissors"
                size={24}
                color={
                  colors.plum
                }
              />
            </View>

            <Text
              style={
                styles.emptyTitle
              }
            >
              Comece pelo seu primeiro serviço
            </Text>

            <Text
              style={
                styles.emptyDescription
              }
            >
              Cadastre nome, valor, duração e outras informações para começar a receber agendamentos.
            </Text>

            <Button
              title="Cadastrar serviço"
              onPress={() =>
                router.push(
                  "/create-service",
                )
              }
              variant="secondary"
              fullWidth
            />
          </View>
        )}

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
              Serviços alimentam vários pontos do IDDUN
            </Text>

            <Text
              style={
                styles.infoText
              }
            >
              Um serviço pode aparecer no perfil, em publicações, no Descobrir e no IDDUN Now quando houver disponibilidade.
            </Text>
          </View>
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

      stats: {
        minHeight: 76,

        marginTop:
          spacing.xxl,

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

      stat: {
        flex: 1,

        alignItems:
          "center",

        justifyContent:
          "center",
      },

      statValue: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 21,
        lineHeight: 26,
      },

      statLabel: {
        marginTop: 2,

        color:
          colors.muted,

        fontFamily:
          fonts.sans,

        fontSize: 9,
        lineHeight: 12,
      },

      statDivider: {
        width: 1,
        height: 34,

        backgroundColor:
          colors.divider,
      },

      actions: {
        marginTop:
          spacing.lg,
      },

      searchWrap: {
        minHeight: 50,

        marginTop:
          spacing.xl,

        paddingHorizontal:
          spacing.md,

        borderRadius:
          radius.md,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,

        backgroundColor:
          colors.surfaceSecondary,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      searchInput: {
        flex: 1,

        color:
          colors.onSurface,

        fontFamily:
          fonts.sans,

        fontSize: 13,
      },

      clearButton: {
        width:
          touch.minimum,

        height:
          touch.minimum,

        alignItems:
          "center",

        justifyContent:
          "center",
      },

      sectionHeader: {
        marginTop:
          spacing.xxxl,

        flexDirection:
          "row",

        alignItems:
          "center",

        justifyContent:
          "space-between",
      },

      sectionTitle: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 23,
        lineHeight: 28,
      },

      sectionCount: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 12,
      },

      serviceList: {
        marginTop:
          spacing.lg,

        gap: spacing.md,
      },

      serviceCard: {
        overflow:
          "hidden",

        borderRadius:
          radius.md,

        backgroundColor:
          colors.surfaceSecondary,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      serviceMain: {
        minHeight: 106,

        padding:
          spacing.md,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.md,
      },

      serviceImage: {
        width: 76,
        height: 76,

        borderRadius:
          radius.md,

        backgroundColor:
          colors.surfaceTertiary,
      },

      serviceContent: {
        flex: 1,
        minWidth: 0,
      },

      serviceCategory: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 8,
        lineHeight: 11,

        letterSpacing: 0.8,
      },

      serviceName: {
        marginTop: 3,

        color:
          colors.onSurface,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 14,
        lineHeight: 18,
      },

      serviceMeta: {
        marginTop:
          spacing.xs,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,
      },

      servicePrice: {
        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sansMedium,

        fontSize: 11,
      },

      serviceDuration: {
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

      availability: {
        marginTop:
          spacing.sm,

        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.xs,
      },

      availabilityDot: {
        width: 6,
        height: 6,

        borderRadius: 3,

        backgroundColor:
          colors.plum,
      },

      availabilityText: {
        flex: 1,

        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 9,
        lineHeight: 12,
      },

      cardActions: {
        minHeight: 48,

        borderTopWidth: 1,

        borderTopColor:
          colors.divider,

        flexDirection:
          "row",
      },

      cardAction: {
        flex: 1,

        minHeight: 48,

        flexDirection:
          "row",

        alignItems:
          "center",

        justifyContent:
          "center",

        gap: spacing.sm,
      },

      cardActionText: {
        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sansMedium,

        fontSize: 10,
      },

      cardActionPrimary: {
        color:
          colors.plum,
      },

      actionDivider: {
        width: 1,

        marginVertical:
          spacing.sm,

        backgroundColor:
          colors.divider,
      },

      emptyCard: {
        marginTop:
          spacing.lg,

        padding:
          spacing.xl,

        borderRadius:
          radius.md,

        alignItems:
          "center",

        backgroundColor:
          colors.surfaceSecondary,

        borderWidth: 1,

        borderColor:
          colors.glassBorder,
      },

      emptyIcon: {
        width: 56,
        height: 56,

        borderRadius:
          radius.pill,

        alignItems:
          "center",

        justifyContent:
          "center",

        backgroundColor:
          colors.plumSoft,
      },

      emptyTitle: {
        marginTop:
          spacing.lg,

        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 21,
        lineHeight: 27,

        textAlign:
          "center",
      },

      emptyDescription: {
        maxWidth: 300,

        marginTop:
          spacing.sm,

        marginBottom:
          spacing.lg,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sans,

        fontSize: 11,
        lineHeight: 17,

        textAlign:
          "center",
      },

      infoCard: {
        marginTop:
          spacing.xxxl,

        padding:
          spacing.lg,

        borderRadius:
          radius.md,

        flexDirection:
          "row",

        alignItems:
          "flex-start",

        gap: spacing.md,

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

      bottomSpace: {
        height: 72,
      },

      pressed: {
        opacity: 0.76,
      },
    }),
  );