import React, {
  forwardRef,
} from "react";
import {
  Text,
  View,
} from "react-native";
import {
  BottomSheetBackdrop,
  BottomSheetModal,
} from "@gorhom/bottom-sheet";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  useTheme,
} from "@/theme";

type CommentsSheetProps = {
  postId: string;

  postAuthor?: {
    id: string;
    name: string;
    kind:
      | "professional"
      | "establishment";
  };

  onRequireLogin?: () => void;
};

export type CommentsSheetRef =
  BottomSheetModal;

export const CommentsSheet =
  forwardRef<
    CommentsSheetRef,
    CommentsSheetProps
  >(function CommentsSheet(
    {
      postId,
    },
    ref,
  ) {
    const styles =
      useStyles();

    const { colors } =
      useTheme();

    return (
      <BottomSheetModal
        ref={ref}
        index={0}
        snapPoints={[
          "42%",
        ]}
        enablePanDownToClose
        backdropComponent={(
          props,
        ) => (
          <BottomSheetBackdrop
            {...props}
            appearsOnIndex={0}
            disappearsOnIndex={-1}
            opacity={0.6}
          />
        )}
        backgroundStyle={
          styles.sheetBackground
        }
        handleIndicatorStyle={
          styles.handle
        }
      >
        <View
          accessibilityLabel={
            `Comentários da publicação ${postId}`
          }
          style={
            styles.content
          }
        >
          <Text
            accessible={false}
            style={
              styles.spark
            }
          >
            ✦
          </Text>

          <Text
            style={
              styles.title
            }
          >
            Comentários em preparação
          </Text>

          <Text
            style={
              styles.description
            }
          >
            A conversa entre clientes, profissionais e estabelecimentos será liberada quando estiver sincronizada com a API do IDDUN.
          </Text>

          <View
            style={
              styles.status
            }
          >
            <View
              style={
                styles.statusDot
              }
            />

            <Text
              style={
                styles.statusText
              }
            >
              Nenhum comentário local ou fictício será publicado nesta versão.
            </Text>
          </View>

          <Text
            style={[
              styles.caption,
              {
                color:
                  colors.muted,
              },
            ]}
          >
            Você ainda pode seguir, salvar e acessar os serviços reais disponíveis no perfil.
          </Text>
        </View>
      </BottomSheetModal>
    );
  });

const useStyles =
  makeStyles(
    (colors) => ({
      sheetBackground: {
        backgroundColor:
          colors.surfaceSecondary,
      },

      handle: {
        width: 38,
        backgroundColor:
          colors.surfaceTertiary,
      },

      content: {
        flex: 1,
        alignItems:
          "center",
        justifyContent:
          "center",
        paddingHorizontal:
          spacing.xl,
        paddingBottom:
          spacing.xxl,
      },

      spark: {
        color:
          colors.plum,
        fontFamily:
          fonts.display,
        fontSize: 30,
        lineHeight: 34,
      },

      title: {
        marginTop:
          spacing.md,
        color:
          colors.onSurface,
        fontFamily:
          fonts.display,
        fontSize: 22,
        lineHeight: 28,
        textAlign:
          "center",
      },

      description: {
        maxWidth: 310,
        marginTop:
          spacing.sm,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sans,
        fontSize: 12,
        lineHeight: 18,
        textAlign:
          "center",
      },

      status: {
        maxWidth: 320,
        marginTop:
          spacing.lg,
        padding:
          spacing.md,
        borderRadius:
          radius.md,
        flexDirection:
          "row",
        alignItems:
          "flex-start",
        gap:
          spacing.sm,
        backgroundColor:
          colors.plumSoft,
        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      statusDot: {
        width: 7,
        height: 7,
        marginTop: 5,
        borderRadius:
          radius.pill,
        backgroundColor:
          colors.plum,
      },

      statusText: {
        flex: 1,
        color:
          colors.onSurfaceSecondary,
        fontFamily:
          fonts.sansMedium,
        fontSize: 10,
        lineHeight: 15,
      },

      caption: {
        maxWidth: 300,
        marginTop:
          spacing.md,
        fontFamily:
          fonts.sans,
        fontSize: 10,
        lineHeight: 15,
        textAlign:
          "center",
      },
    }),
  );
