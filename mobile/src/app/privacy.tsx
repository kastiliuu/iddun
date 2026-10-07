import React, {
  useMemo,
  useState,
} from "react";
import {
  Alert,
  Linking,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  useRouter,
} from "expo-router";

import {
  deleteAccount,
  resendEmailVerification,
} from "@/api/auth";
import {
  API_URL,
  ApiError,
} from "@/api/client";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
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

export default function PrivacyScreen() {
  useStoreVersion();

  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const user = store.getUser();

  const [
    password,
    setPassword,
  ] = useState("");

  const [
    confirmDeletion,
    setConfirmDeletion,
  ] = useState(false);

  const [
    deleting,
    setDeleting,
  ] = useState(false);

  const [
    resending,
    setResending,
  ] = useState(false);

  const [
    verificationMessage,
    setVerificationMessage,
  ] =
    useState<string | null>(
      null,
    );

  const canDelete =
    useMemo(
      () =>
        password.length > 0 &&
        confirmDeletion &&
        !deleting,
      [
        confirmDeletion,
        deleting,
        password,
      ],
    );

  const openPublicPage =
    async (
      path: string,
    ) => {
      try {
        await Linking.openURL(
          `${API_URL}${path}`,
        );
      } catch {
        Alert.alert(
          "Não foi possível abrir a página",
          "Tente novamente em instantes.",
        );
      }
    };

  const handleResend =
    async () => {
      setResending(true);
      setVerificationMessage(
        null,
      );

      try {
        const response =
          await resendEmailVerification();

        setVerificationMessage(
          response.message,
        );
      } catch (error) {
        Alert.alert(
          "Não foi possível reenviar",
          error instanceof Error
            ? error.message
            : "Tente novamente em instantes.",
        );
      } finally {
        setResending(false);
      }
    };

  const performDeletion =
    async () => {
      setDeleting(true);

      try {
        await deleteAccount(
          password,
        );

        Alert.alert(
          "Conta removida",
          "Seus dados pessoais foram anonimizados e sua sessão foi encerrada.",
          [
            {
              text: "Entendi",
              onPress: () =>
                router.replace(
                  "/login",
                ),
            },
          ],
        );
      } catch (error) {
        if (
          error instanceof ApiError &&
          error.code ===
            "ownership_transfer_required"
        ) {
          const details =
            error.details as
              | {
                  establishments?: string[];
                }
              | undefined;

          const names =
            details
              ?.establishments
              ?.join(", ");

          Alert.alert(
            "Transfira a titularidade antes",
            names
              ? `Você ainda é titular de: ${names}. Transfira a titularidade antes de excluir sua conta.`
              : error.message,
          );
        } else {
          Alert.alert(
            "Não foi possível excluir a conta",
            error instanceof Error
              ? error.message
              : "Tente novamente em instantes.",
          );
        }
      } finally {
        setDeleting(false);
      }
    };

  const requestDeletion =
    () => {
      if (!canDelete) {
        return;
      }

      Alert.alert(
        "Excluir sua conta?",
        "Essa ação é irreversível. Seus dados pessoais serão removidos ou anonimizados e você será desconectado.",
        [
          {
            text: "Cancelar",
            style: "cancel",
          },
          {
            text: "Excluir conta",
            style: "destructive",
            onPress: () => {
              void performDeletion();
            },
          },
        ],
      );
    };

  if (!user) {
    return (
      <View
        style={
          styles.container
        }
      >
        <EmptyState
          title="Entre para revisar sua privacidade"
          description="As configurações de conta ficam disponíveis depois do login."
          actionLabel="Entrar"
          onActionPress={() =>
            router.replace(
              "/login",
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
            Privacidade
          </Text>

          <View
            style={
              styles.headerSpacer
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
            SUA CONTA
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Seus dados, sob seu controle.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Revise segurança, documentos e opções relacionadas aos seus dados no IDDUN.
          </Text>
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
            SEGURANÇA
          </Text>

          <View
            style={
              styles.card
            }
          >
            <View
              style={
                styles.cardRow
              }
            >
              <View
                style={
                  styles.cardIcon
                }
              >
                <Icon
                  name="mail"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              </View>

              <View
                style={
                  styles.cardBody
                }
              >
                <Text
                  style={
                    styles.cardTitle
                  }
                >
                  E-mail
                </Text>
                <Text
                  style={
                    styles.cardText
                  }
                >
                  {user.emailVerified
                    ? "Confirmado"
                    : "Ainda não confirmado"}
                </Text>
              </View>
            </View>

            {!user.emailVerified ? (
              <>
                <View
                  style={
                    styles.divider
                  }
                />

                <Button
                  title="Reenviar confirmação"
                  variant="secondary"
                  compact
                  loading={
                    resending
                  }
                  onPress={() =>
                    void handleResend()
                  }
                />

                {verificationMessage ? (
                  <Text
                    style={
                      styles.infoText
                    }
                  >
                    {
                      verificationMessage
                    }
                  </Text>
                ) : null}
              </>
            ) : null}

            <View
              style={
                styles.divider
              }
            />

            <Pressable
              accessibilityRole="button"
              onPress={() =>
                router.push(
                  "/sessions",
                )
              }
              style={
                styles.linkRow
              }
            >
              <View
                style={
                  styles.cardIcon
                }
              >
                <Icon
                  name="smartphone"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              </View>

              <View
                style={
                  styles.cardBody
                }
              >
                <Text
                  style={
                    styles.cardTitle
                  }
                >
                  Dispositivos e sessões
                </Text>
                <Text
                  style={
                    styles.cardText
                  }
                >
                  Revise onde sua conta está conectada.
                </Text>
              </View>

              <Icon
                name="chevron-right"
                size={18}
                color={
                  colors.muted
                }
              />
            </Pressable>
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
            DOCUMENTOS
          </Text>

          <View
            style={
              styles.card
            }
          >
            <Pressable
              accessibilityRole="link"
              onPress={() =>
                void openPublicPage(
                  "/privacidade",
                )
              }
              style={
                styles.linkRow
              }
            >
              <View
                style={
                  styles.cardIcon
                }
              >
                <Icon
                  name="shield"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              </View>
              <View
                style={
                  styles.cardBody
                }
              >
                <Text
                  style={
                    styles.cardTitle
                  }
                >
                  Política de Privacidade
                </Text>
                <Text
                  style={
                    styles.cardText
                  }
                >
                  Como o IDDUN trata dados pessoais.
                </Text>
              </View>
              <Icon
                name="external-link"
                size={17}
                color={
                  colors.muted
                }
              />
            </Pressable>

            <View
              style={
                styles.divider
              }
            />

            <Pressable
              accessibilityRole="link"
              onPress={() =>
                void openPublicPage(
                  "/termos",
                )
              }
              style={
                styles.linkRow
              }
            >
              <View
                style={
                  styles.cardIcon
                }
              >
                <Icon
                  name="file-text"
                  size={18}
                  color={
                    colors.plum
                  }
                />
              </View>
              <View
                style={
                  styles.cardBody
                }
              >
                <Text
                  style={
                    styles.cardTitle
                  }
                >
                  Termos de Uso
                </Text>
                <Text
                  style={
                    styles.cardText
                  }
                >
                  Regras essenciais da plataforma.
                </Text>
              </View>
              <Icon
                name="external-link"
                size={17}
                color={
                  colors.muted
                }
              />
            </Pressable>
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
            EXCLUSÃO DA CONTA
          </Text>

          <View
            style={[
              styles.card,
              styles.dangerCard,
            ]}
          >
            <Text
              style={
                styles.dangerTitle
              }
            >
              Remover minha conta
            </Text>

            <Text
              style={
                styles.cardText
              }
            >
              A exclusão é irreversível. Dados pessoais são removidos ou anonimizados. Registros transacionais podem ser preservados de forma anonimizada quando necessário.
            </Text>

            <Text
              style={
                styles.fieldLabel
              }
            >
              Senha atual
            </Text>

            <View
              style={
                styles.inputWrap
              }
            >
              <Icon
                name="lock"
                size={17}
                color={
                  colors.muted
                }
              />
              <TextInput
                value={
                  password
                }
                onChangeText={
                  setPassword
                }
                secureTextEntry
                autoCapitalize="none"
                autoCorrect={false}
                textContentType="password"
                placeholder="Confirme sua senha"
                placeholderTextColor={
                  colors.muted
                }
                style={
                  styles.input
                }
              />
            </View>

            <Pressable
              accessibilityRole="checkbox"
              accessibilityState={{
                checked:
                  confirmDeletion,
              }}
              onPress={() =>
                setConfirmDeletion(
                  (current) =>
                    !current,
                )
              }
              style={
                styles.confirmRow
              }
            >
              <View
                style={[
                  styles.checkbox,
                  confirmDeletion &&
                    styles.checkboxChecked,
                ]}
              >
                {confirmDeletion ? (
                  <Icon
                    name="check"
                    size={14}
                    color={
                      colors.onBrandPrimary
                    }
                  />
                ) : null}
              </View>

              <Text
                style={
                  styles.confirmText
                }
              >
                Entendo que minha conta será desativada e a exclusão não poderá ser desfeita.
              </Text>
            </Pressable>

            <Button
              title="Excluir minha conta"
              variant="secondary"
              loading={
                deleting
              }
              disabled={
                !canDelete
              }
              onPress={
                requestDeletion
              }
              fullWidth
            />
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
        fontSize: 14,
      },
      headerSpacer: {
        width:
          touch.minimum,
      },
      intro: {
        marginTop:
          spacing.xxl,
      },
      eyebrow: {
        color:
          colors.plum,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        letterSpacing: 1.4,
      },
      title: {
        maxWidth: 350,
        marginTop:
          spacing.sm,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 30,
        lineHeight: 36,
      },
      description: {
        maxWidth: 360,
        marginTop:
          spacing.md,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 19,
      },
      section: {
        marginTop:
          spacing.xxl,
      },
      sectionLabel: {
        marginBottom:
          spacing.sm,
        color:
          colors.muted,
        fontFamily:
          fonts.sansMedium,
        fontSize: 9,
        letterSpacing: 1.2,
      },
      card: {
        padding:
          spacing.lg,
        gap:
          spacing.md,
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },
      cardRow: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.md,
      },
      linkRow: {
        minHeight:
          touch.minimum,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.md,
      },
      cardIcon: {
        width: 38,
        height: 38,
        borderRadius:
          radius.pill,
        alignItems:
          "center",
        justifyContent:
          "center",
        backgroundColor:
          colors.plumSoft,
      },
      cardBody: {
        flex: 1,
      },
      cardTitle: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 13,
      },
      cardText: {
        marginTop: 3,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 11,
        lineHeight: 17,
      },
      divider: {
        height: 1,
        backgroundColor:
          colors.glassBorder,
      },
      infoText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 16,
      },
      dangerCard: {
        borderColor:
          colors.error,
      },
      dangerTitle: {
        color:
          colors.error,
        fontFamily:
          fonts.sansSemiBold,
        fontSize: 15,
      },
      fieldLabel: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 11,
      },
      inputWrap: {
        minHeight: 52,
        paddingHorizontal:
          spacing.md,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.sm,
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surface,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },
      input: {
        flex: 1,
        color:
          colors.onSurface,
        fontFamily:
          fonts.sans,
        fontSize: 14,
      },
      confirmRow: {
        minHeight:
          touch.minimum,
        flexDirection:
          "row",
        alignItems:
          "center",
        gap:
          spacing.sm,
      },
      checkbox: {
        width: 22,
        height: 22,
        borderRadius: 6,
        alignItems:
          "center",
        justifyContent:
          "center",
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },
      checkboxChecked: {
        backgroundColor:
          colors.plum,
        borderColor:
          colors.plum,
      },
      confirmText: {
        flex: 1,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 11,
        lineHeight: 17,
      },
      bottomSpace: {
        height: 110,
      },
    }),
  );
