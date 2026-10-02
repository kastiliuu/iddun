import React, { useMemo, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import * as Haptics from "expo-haptics";

import {
  login as loginWithApi,
  registerClient,
} from "@/api/auth";
import { Button } from "@/components/Button";
import { Icon } from "@/components/Icon";
import { markLoggedIn } from "@/store/local";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  SPARK,
  touch,
  useTheme,
} from "@/theme";

type AuthMode = "login" | "signup";
type AccountType = "client" | "professional";

export default function LoginScreen() {
  const styles = useStyles();
  const { colors } = useTheme();

  const params = useLocalSearchParams<{
    mode?: string | string[];
    accountType?: string | string[];
    returnToBooking?: string | string[];
    returnTo?: string | string[];
  }>();

  const requestedMode = Array.isArray(params.mode)
    ? params.mode[0]
    : params.mode;

  const requestedAccountType = Array.isArray(
    params.accountType,
  )
    ? params.accountType[0]
    : params.accountType;

  const requestedBooking = Array.isArray(
    params.returnToBooking,
  )
    ? params.returnToBooking[0]
    : params.returnToBooking;

  const requestedReturnTo = Array.isArray(
    params.returnTo,
  )
    ? params.returnTo[0]
    : params.returnTo;

  const [mode, setMode] = useState<AuthMode>(
    requestedMode === "signup" ? "signup" : "login",
  );

  const [accountType, setAccountType] =
    useState<AccountType>(
      requestedAccountType === "professional"
        ? "professional"
        : "client",
    );

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSignup = mode === "signup";

  const title = useMemo(
    () =>
      isSignup
        ? "Crie sua presença no IDDUN."
        : "Entre no seu universo.",
    [isSignup],
  );

  const description = useMemo(() => {
    if (isSignup) {
      return accountType === "professional"
        ? "Comece seu perfil profissional e conecte seu trabalho a novas experiências."
        : "Crie sua conta para seguir, salvar e descobrir experiências do seu jeito.";
    }

    return "Continue descobrindo profissionais, serviços e lugares que combinam com você.";
  }, [accountType, isSignup]);

  const validate = () => {
    if (
      isSignup &&
      (name.trim().length < 2 || name.trim().length > 120)
    ) {
      setError("Digite um nome entre 2 e 120 caracteres.");
      return false;
    }

    if (!email.includes("@") || !email.includes(".")) {
      setError("Digite um e-mail válido.");
      return false;
    }

    if (!password) {
      setError("Digite sua senha.");
      return false;
    }

    if (
      isSignup &&
      (password.length < 8 || password.length > 128)
    ) {
      setError("A senha deve ter entre 8 e 128 caracteres.");
      return false;
    }

    setError(null);
    return true;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      return;
    }

    Haptics.impactAsync(
      Haptics.ImpactFeedbackStyle.Light,
    ).catch(() => {});

    setLoading(true);

    try {
      if (isSignup && accountType === "professional") {
        router.push({
          pathname: "/signup-pro",
          params: {
            name: name.trim(),
            email: email.trim(),
          },
        });
        return;
      }

      if (isSignup) {
        await registerClient({
          name: name.trim(),
          email: email.trim(),
          password,
        });
      } else {
        await loginWithApi({
          email: email.trim(),
          password,
        });
      }

      await markLoggedIn();

      if (requestedBooking) {
        router.replace(
          `/booking/${requestedBooking}`,
        );
        return;
      }

      if (
        requestedReturnTo ===
        "bookings"
      ) {
        router.replace(
          "/bookings",
        );
        return;
      }

      router.replace("/(tabs)");
    } catch (cause) {
      setError(
        cause instanceof Error && cause.message
          ? cause.message
          : "Não foi possível concluir o acesso. Tente novamente.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleVisitor = () => {
    if (requestedBooking) {
      router.replace(
        `/booking/${requestedBooking}`,
      );
      return;
    }

    router.replace("/(tabs)");
  };

  const toggleMode = (nextMode: AuthMode) => {
    setMode(nextMode);
    setError(null);
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            hitSlop={8}
            onPress={() => {
              if (router.canGoBack()) {
                router.back();
              } else {
                router.replace("/(tabs)");
              }
            }}
            style={({ pressed }) => [
              styles.backButton,
              pressed && styles.pressed,
            ]}
          >
            <Icon
              name="arrow-left"
              size={20}
              color={colors.onSurface}
            />
          </Pressable>

          <View style={styles.brandRow}>
            <Text style={styles.brand}>IDDUN</Text>
            <Text accessible={false} style={styles.brandSpark}>
              {SPARK}
            </Text>
          </View>

          <View style={styles.headerSpacer} />
        </View>

        <View style={styles.intro}>
          <Text style={styles.eyebrow}>
            {isSignup ? "CRIAR CONTA" : "BEM-VINDO DE VOLTA"}
          </Text>

          <Text style={styles.title}>{title}</Text>
          <Text style={styles.description}>
            {description}
          </Text>
        </View>

        <View style={styles.modeSwitcher}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{
              selected: mode === "login",
            }}
            onPress={() => toggleMode("login")}
            style={[
              styles.modeButton,
              mode === "login" && styles.modeButtonActive,
            ]}
          >
            <Text
              style={[
                styles.modeText,
                mode === "login" && styles.modeTextActive,
              ]}
            >
              Entrar
            </Text>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityState={{
              selected: mode === "signup",
            }}
            onPress={() => toggleMode("signup")}
            style={[
              styles.modeButton,
              mode === "signup" && styles.modeButtonActive,
            ]}
          >
            <Text
              style={[
                styles.modeText,
                mode === "signup" && styles.modeTextActive,
              ]}
            >
              Criar conta
            </Text>
          </Pressable>
        </View>

        {isSignup ? (
          <View style={styles.accountTypeArea}>
            <Text style={styles.fieldLabel}>
              Quero usar o IDDUN como
            </Text>

            <View style={styles.accountTypeRow}>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{
                  selected: accountType === "client",
                }}
                onPress={() => {
                  setAccountType("client");
                  setError(null);
                }}
                style={[
                  styles.accountCard,
                  accountType === "client" &&
                    styles.accountCardActive,
                ]}
              >
                <View
                  style={[
                    styles.accountIcon,
                    accountType === "client" &&
                      styles.accountIconActive,
                  ]}
                >
                  <Icon
                    name="heart"
                    size={18}
                    color={
                      accountType === "client"
                        ? colors.onBrandPrimary
                        : colors.muted
                    }
                  />
                </View>

                <Text
                  style={[
                    styles.accountTitle,
                    accountType === "client" &&
                      styles.accountTitleActive,
                  ]}
                >
                  Cliente
                </Text>

                <Text style={styles.accountDescription}>
                  Descobrir, seguir, salvar e agendar.
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="button"
                accessibilityState={{
                  selected: accountType === "professional",
                }}
                onPress={() => {
                  setAccountType("professional");
                  setError(null);
                }}
                style={[
                  styles.accountCard,
                  accountType === "professional" &&
                    styles.accountCardActive,
                ]}
              >
                <View
                  style={[
                    styles.accountIcon,
                    accountType === "professional" &&
                      styles.accountIconActive,
                  ]}
                >
                  <Icon
                    name="briefcase"
                    size={18}
                    color={
                      accountType === "professional"
                        ? colors.onBrandPrimary
                        : colors.muted
                    }
                  />
                </View>

                <Text
                  style={[
                    styles.accountTitle,
                    accountType === "professional" &&
                      styles.accountTitleActive,
                  ]}
                >
                  Profissional
                </Text>

                <Text style={styles.accountDescription}>
                  Mostrar seu trabalho e receber clientes.
                </Text>
              </Pressable>
            </View>

            {accountType === "professional" ? (
              <Text style={styles.accountHint}>
                Você poderá escolher depois entre profissional
                individual ou estabelecimento.
              </Text>
            ) : null}
          </View>
        ) : null}

        <View style={styles.form}>
          {isSignup ? (
            <View>
              <Text style={styles.fieldLabel}>Nome</Text>

              <View style={styles.inputWrap}>
                <Icon
                  name="user"
                  size={17}
                  color={colors.muted}
                />

                <TextInput
                  value={name}
                  onChangeText={setName}
                  placeholder="Seu nome"
                  placeholderTextColor={colors.muted}
                  autoCapitalize="words"
                  autoCorrect={false}
                  style={styles.input}
                  accessibilityLabel="Nome"
                />
              </View>
            </View>
          ) : null}

          <View>
            <Text style={styles.fieldLabel}>E-mail</Text>

            <View style={styles.inputWrap}>
              <Icon
                name="mail"
                size={17}
                color={colors.muted}
              />

              <TextInput
                value={email}
                onChangeText={setEmail}
                placeholder="voce@exemplo.com"
                placeholderTextColor={colors.muted}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                textContentType="emailAddress"
                style={styles.input}
                accessibilityLabel="E-mail"
              />
            </View>
          </View>

          <View>
            <Text style={styles.fieldLabel}>Senha</Text>

            <View style={styles.inputWrap}>
              <Icon
                name="lock"
                size={17}
                color={colors.muted}
              />

              <TextInput
                value={password}
                onChangeText={setPassword}
                placeholder="Sua senha"
                placeholderTextColor={colors.muted}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                textContentType="password"
                style={styles.input}
                accessibilityLabel="Senha"
              />

              <Pressable
                accessibilityRole="button"
                accessibilityLabel={
                  showPassword
                    ? "Ocultar senha"
                    : "Mostrar senha"
                }
                hitSlop={8}
                onPress={() =>
                  setShowPassword((current) => !current)
                }
                style={styles.passwordButton}
              >
                <Icon
                  name={showPassword ? "eye-off" : "eye"}
                  size={17}
                  color={colors.muted}
                />
              </Pressable>
            </View>
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <Icon
                name="alert-circle"
                size={15}
                color={colors.error}
              />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <Button
            title={
              isSignup
                ? accountType === "professional"
                  ? "Continuar"
                  : "Criar minha conta"
                : "Entrar"
            }
            onPress={handleSubmit}
            loading={loading}
            fullWidth
          />
        </View>

        <View style={styles.dividerRow}>
          <View style={styles.divider} />
          <Text style={styles.dividerText}>ou</Text>
          <View style={styles.divider} />
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Continuar como visitante"
          onPress={handleVisitor}
          style={({ pressed }) => [
            styles.visitorButton,
            pressed && styles.pressed,
          ]}
        >
          <Text style={styles.visitorText}>
            Continuar como visitante
          </Text>
          <Icon
            name="arrow-right"
            size={15}
            color={colors.onSurfaceSecondary}
          />
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: 54,
    paddingBottom: spacing.xxxl,
  },
  header: {
    minHeight: touch.minimum,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  backButton: {
    width: touch.minimum,
    height: touch.minimum,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    backgroundColor: colors.glassSoft,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
  },
  brand: {
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 18,
    lineHeight: 22,
    letterSpacing: 2.2,
  },
  brandSpark: {
    color: colors.plum,
    fontFamily: fonts.display,
    fontSize: 11,
  },
  headerSpacer: {
    width: touch.minimum,
  },
  intro: {
    marginTop: spacing.xxxl,
  },
  eyebrow: {
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 1.5,
  },
  title: {
    maxWidth: 330,
    marginTop: spacing.sm,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: 34,
    lineHeight: 40,
    letterSpacing: -0.5,
  },
  description: {
    maxWidth: 340,
    marginTop: spacing.md,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 13,
    lineHeight: 20,
  },
  modeSwitcher: {
    height: 48,
    marginTop: spacing.xxl,
    padding: 4,
    borderRadius: radius.pill,
    flexDirection: "row",
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  modeButton: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
  },
  modeButtonActive: {
    backgroundColor: colors.surfaceTertiary,
  },
  modeText: {
    color: colors.muted,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
  },
  modeTextActive: {
    color: colors.onSurface,
  },
  accountTypeArea: {
    marginTop: spacing.xl,
  },
  accountTypeRow: {
    marginTop: spacing.sm,
    flexDirection: "row",
    gap: spacing.sm,
  },
  accountCard: {
    flex: 1,
    minHeight: 130,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  accountCardActive: {
    borderColor: colors.plum,
    backgroundColor: colors.plumSoft,
  },
  accountIcon: {
    width: 34,
    height: 34,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surfaceTertiary,
  },
  accountIconActive: {
    backgroundColor: colors.plum,
  },
  accountTitle: {
    marginTop: spacing.md,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansSemiBold,
    fontSize: 13,
  },
  accountTitleActive: {
    color: colors.onSurface,
  },
  accountDescription: {
    marginTop: spacing.xs,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 10,
    lineHeight: 15,
  },
  accountHint: {
    marginTop: spacing.sm,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 10,
    lineHeight: 15,
  },
  form: {
    marginTop: spacing.xl,
    gap: spacing.lg,
  },
  fieldLabel: {
    marginBottom: spacing.sm,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: 11,
    lineHeight: 15,
  },
  inputWrap: {
    minHeight: 52,
    paddingHorizontal: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
  input: {
    flex: 1,
    paddingVertical: spacing.md,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 13,
    lineHeight: 18,
  },
  passwordButton: {
    width: touch.minimum,
    height: touch.minimum,
    alignItems: "center",
    justifyContent: "center",
  },
  errorBox: {
    minHeight: 42,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    backgroundColor: "rgba(239,68,68,0.10)",
    borderWidth: 1,
    borderColor: "rgba(239,68,68,0.25)",
  },
  errorText: {
    flex: 1,
    color: colors.error,
    fontFamily: fonts.sans,
    fontSize: 11,
    lineHeight: 16,
  },
  dividerRow: {
    marginVertical: spacing.xl,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: colors.divider,
  },
  dividerText: {
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 11,
  },
  visitorButton: {
    minHeight: touch.minimum,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  visitorText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
  },
  pressed: {
    opacity: 0.72,
  },
}));