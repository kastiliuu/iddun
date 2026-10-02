import React, {
  useState,
} from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  router,
} from "expo-router";

import {
  requestPasswordReset,
} from "@/api/auth";
import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  touch,
  useTheme,
} from "@/theme";

export default function ForgotPasswordScreen() {
  const styles = useStyles();
  const { colors } = useTheme();

  const [
    email,
    setEmail,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    message,
    setMessage,
  ] =
    useState<string | null>(
      null,
    );

  const [
    error,
    setError,
  ] =
    useState<string | null>(
      null,
    );

  const handleSubmit =
    async () => {
      if (
        !email.includes("@") ||
        !email.includes(".")
      ) {
        setError(
          "Digite um e-mail válido.",
        );
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response =
          await requestPasswordReset(
            email,
          );

        setMessage(
          response.message,
        );
      } catch (
        cause
      ) {
        setError(
          cause instanceof Error
            ? cause.message
            : "Não foi possível enviar a recuperação agora.",
        );
      } finally {
        setLoading(false);
      }
    };

  return (
    <KeyboardAvoidingView
      style={
        styles.container
      }
      behavior={
        Platform.OS === "ios"
          ? "padding"
          : undefined
      }
    >
      <ScrollView
        contentContainerStyle={
          styles.content
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
            onPress={() =>
              router.back()
            }
            style={
              styles.backButton
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

          <View
            style={
              styles.brandRow
            }
          >
            <Text
              style={
                styles.brand
              }
            >
              IDDUN
            </Text>
            <Text
              style={
                styles.brandSpark
              }
            >
              {SPARK}
            </Text>
          </View>

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
            RECUPERAR ACESSO
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Vamos recuperar sua conta.
          </Text>

          <Text
            style={
              styles.description
            }
          >
            Informe o e-mail usado no IDDUN. Se existir uma conta com esse endereço, enviaremos um link seguro de recuperação.
          </Text>
        </View>

        {message ? (
          <View
            style={
              styles.successBox
            }
          >
            <Icon
              name="mail"
              size={18}
              color={
                colors.plum
              }
            />

            <Text
              style={
                styles.successText
              }
            >
              {message}
            </Text>

            <Button
              title="Voltar para o login"
              onPress={() =>
                router.replace(
                  "/login",
                )
              }
              fullWidth
            />
          </View>
        ) : (
          <View
            style={
              styles.form
            }
          >
            <Text
              style={
                styles.fieldLabel
              }
            >
              E-mail
            </Text>

            <View
              style={
                styles.inputWrap
              }
            >
              <Icon
                name="mail"
                size={17}
                color={
                  colors.muted
                }
              />

              <TextInput
                value={email}
                onChangeText={
                  setEmail
                }
                placeholder="voce@exemplo.com"
                placeholderTextColor={
                  colors.muted
                }
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                textContentType="emailAddress"
                style={
                  styles.input
                }
                accessibilityLabel="E-mail"
              />
            </View>

            {error ? (
              <View
                style={
                  styles.errorBox
                }
              >
                <Icon
                  name="alert-circle"
                  size={15}
                  color={
                    colors.error
                  }
                />
                <Text
                  style={
                    styles.errorText
                  }
                >
                  {error}
                </Text>
              </View>
            ) : null}

            <Button
              title="Enviar link de recuperação"
              onPress={
                handleSubmit
              }
              loading={
                loading
              }
              fullWidth
            />
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
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
        flexGrow: 1,
        paddingHorizontal:
          spacing.xl,
        paddingTop: 54,
        paddingBottom:
          spacing.xxxl,
      },

      header: {
        minHeight:
          touch.minimum,
        flexDirection:
          "row",
        alignItems:
          "center",
        justifyContent:
          "space-between",
      },

      backButton: {
        width:
          touch.minimum,
        height:
          touch.minimum,
        alignItems:
          "center",
        justifyContent:
          "center",
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.glassSoft,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      brandRow: {
        flexDirection:
          "row",
        alignItems:
          "center",
        gap: spacing.xs,
      },

      brand: {
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 18,
        lineHeight: 22,
        letterSpacing: 2.2,
      },

      brandSpark: {
        color:
          colors.plum,
        fontFamily:
          fonts.display,
        fontSize: 14,
      },

      headerSpacer: {
        width:
          touch.minimum,
      },

      intro: {
        marginTop:
          spacing.xxxl,
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
        maxWidth: 340,
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

      form: {
        marginTop:
          spacing.xxl,
        gap: spacing.md,
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
        gap: spacing.sm,
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
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

      errorBox: {
        padding:
          spacing.md,
        flexDirection:
          "row",
        gap: spacing.sm,
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.error,
      },

      errorText: {
        flex: 1,
        color:
          colors.error,
        fontFamily:
          fonts.sans,
        fontSize: 11,
        lineHeight: 17,
      },

      successBox: {
        marginTop:
          spacing.xxl,
        padding:
          spacing.xl,
        gap: spacing.lg,
        alignItems:
          "center",
        borderRadius:
          radius.md,
        backgroundColor:
          colors.surfaceSecondary,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      successText: {
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 19,
        textAlign:
          "center",
      },
    }),
  );
