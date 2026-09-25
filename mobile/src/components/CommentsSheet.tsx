import React, {
  forwardRef,
  useCallback,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Keyboard,
  Pressable,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  BottomSheetBackdrop,
  BottomSheetFlatList,
  BottomSheetModal,
  BottomSheetTextInput,
} from "@gorhom/bottom-sheet";
import * as Haptics from "expo-haptics";

import { Avatar } from "@/components/Avatar";
import { Icon } from "@/components/Icon";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

import {
  Comment,
  store,
  useStoreVersion,
} from "@/store/local";

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

function formatCommentTime(
  timestamp: number,
) {
  const diff =
    Date.now() - timestamp;

  const minutes = Math.max(
    1,
    Math.floor(
      diff / 60_000,
    ),
  );

  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(
    minutes / 60,
  );

  if (hours < 24) {
    return `${hours}h`;
  }

  const days = Math.floor(
    hours / 24,
  );

  if (days < 7) {
    return `${days}d`;
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day: "2-digit",
      month: "short",
    },
  ).format(
    new Date(timestamp),
  );
}

export const CommentsSheet =
  forwardRef<
    CommentsSheetRef,
    CommentsSheetProps
  >(function CommentsSheet(
    {
      postId,
      postAuthor,
      onRequireLogin,
    },
    ref,
  ) {
    useStoreVersion();

    const styles = useStyles();
    const { colors } =
      useTheme();

    const [text, setText] =
      useState("");

    const inputRef =
      useRef<TextInput | null>(
        null,
      );

    const comments =
      store.getComments(
        postId,
      );

    const user =
      store.getUser();

    const snapPoints =
      useMemo(
        () => ["55%", "88%"],
        [],
      );

    const renderBackdrop =
      useCallback(
        (
          props: React.ComponentProps<
            typeof BottomSheetBackdrop
          >,
        ) => (
          <BottomSheetBackdrop
            {...props}
            appearsOnIndex={0}
            disappearsOnIndex={-1}
            opacity={0.6}
          />
        ),
        [],
      );

    const handleSend = () => {
      const clean =
        text.trim();

      if (!clean) {
        return;
      }

      /**
       * Leitura pode ser pública,
       * mas comentar exige login.
       */
      if (!user) {
        Keyboard.dismiss();

        onRequireLogin?.();

        return;
      }

      const isAuthorReply =
        Boolean(
          postAuthor &&
            user.profileId &&
            user.profileId ===
              postAuthor.id &&
            (
              user.role ===
                "professional" ||
              user.role ===
                "establishment"
            ),
        );

      store.addComment(
        postId,
        clean,
        {
          isAuthorReply,
        },
      );

      setText("");

      Haptics.impactAsync(
        Haptics
          .ImpactFeedbackStyle
          .Light,
      ).catch(() => {});
    };

    const renderComment =
      useCallback(
        ({
          item,
        }: {
          item: Comment;
        }) => {
          const isAuthor =
            item.isAuthorReply ===
            true;

          return (
            <View
              style={
                styles.comment
              }
            >
              <Avatar
                name={item.author}
                size={36}
              />

              <View
                style={
                  styles.commentContent
                }
              >
                <View
                  style={
                    styles.commentHeader
                  }
                >
                  <Text
                    style={
                      styles.commentAuthor
                    }
                    numberOfLines={
                      1
                    }
                  >
                    {item.author}
                  </Text>

                  {isAuthor ? (
                    <View
                      style={
                        styles.authorBadge
                      }
                    >
                      <Text
                        style={
                          styles.authorBadgeText
                        }
                      >
                        Autor
                      </Text>
                    </View>
                  ) : null}

                  <Text
                    style={
                      styles.commentTime
                    }
                  >
                    {formatCommentTime(
                      item.createdAt,
                    )}
                  </Text>
                </View>

                <Text
                  style={
                    styles.commentText
                  }
                >
                  {item.text}
                </Text>
              </View>
            </View>
          );
        },
        [styles],
      );

    const listEmptyComponent =
      useMemo(
        () => (
          <View
            style={
              styles.empty
            }
          >
            <Text
              accessible={
                false
              }
              style={
                styles.emptySpark
              }
            >
              ✦
            </Text>

            <Text
              style={
                styles.emptyTitle
              }
            >
              Seja o primeiro
            </Text>

            <Text
              style={
                styles.emptyText
              }
            >
              Ainda não há
              comentários nesta
              publicação.
            </Text>
          </View>
        ),
        [styles],
      );

    return (
      <BottomSheetModal
        ref={ref}
        index={0}
        snapPoints={
          snapPoints
        }
        enablePanDownToClose
        keyboardBehavior="interactive"
        keyboardBlurBehavior="restore"
        android_keyboardInputMode="adjustResize"
        backdropComponent={
          renderBackdrop
        }
        backgroundStyle={
          styles.sheetBackground
        }
        handleIndicatorStyle={
          styles.handle
        }
      >
        <View
          style={
            styles.header
          }
        >
          <View>
            <Text
              style={
                styles.title
              }
            >
              Comentários
            </Text>

            <Text
              style={
                styles.subtitle
              }
            >
              {comments.length ===
              0
                ? "Nenhum comentário ainda"
                : comments.length ===
                    1
                  ? "1 comentário"
                  : `${comments.length} comentários`}
            </Text>
          </View>
        </View>

        <BottomSheetFlatList
          data={comments}
          keyExtractor={(
            item,
          ) => item.id}
          renderItem={
            renderComment
          }
          ListEmptyComponent={
            listEmptyComponent
          }
          contentContainerStyle={
            comments.length ===
            0
              ? styles
                  .emptyListContent
              : styles
                  .listContent
          }
          showsVerticalScrollIndicator={
            false
          }
        />

        <View
          style={
            styles.composer
          }
        >
          {user ? (
            <Avatar
              name={
                user.name
              }
              uri={
                user.avatar
              }
              size={36}
            />
          ) : (
            <View
              style={
                styles.guestAvatar
              }
            >
              <Icon
                name="user"
                size={17}
                color={
                  colors.muted
                }
              />
            </View>
          )}

          <View
            style={
              styles.inputWrap
            }
          >
            <BottomSheetTextInput
              ref={
                inputRef as any
              }
              value={text}
              onChangeText={
                setText
              }
              placeholder={
                user
                  ? "Escreva um comentário..."
                  : "Entre para comentar"
              }
              placeholderTextColor={
                colors.muted
              }
              editable={
                Boolean(user)
              }
              multiline
              maxLength={
                500
              }
              returnKeyType="default"
              style={
                styles.input
              }
              accessibilityLabel="Campo de comentário"
            />

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={
                user
                  ? "Enviar comentário"
                  : "Entrar para comentar"
              }
              disabled={
                Boolean(user) &&
                !text.trim()
              }
              onPress={() => {
                if (!user) {
                  onRequireLogin?.();

                  return;
                }

                handleSend();
              }}
              style={({
                pressed,
              }) => [
                styles.sendButton,

                user &&
                  !text.trim() &&
                  styles.sendDisabled,

                pressed &&
                  styles.pressed,
              ]}
            >
              <Icon
                name="arrow-up"
                size={17}
                color={
                  colors
                    .onBrandPrimary
                }
              />
            </Pressable>
          </View>
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

      header: {
        paddingHorizontal:
          spacing.lg,

        paddingTop:
          spacing.sm,

        paddingBottom:
          spacing.md,

        borderBottomWidth: 1,
        borderBottomColor:
          colors.divider,
      },

      title: {
        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 22,
        lineHeight: 28,
      },

      subtitle: {
        marginTop: 2,

        color:
          colors.muted,

        fontFamily:
          fonts.sans,

        fontSize: 11,
        lineHeight: 15,
      },

      listContent: {
        paddingHorizontal:
          spacing.lg,

        paddingTop:
          spacing.md,

        paddingBottom:
          spacing.xl,
      },

      emptyListContent: {
        flexGrow: 1,
      },

      comment: {
        flexDirection:
          "row",

        alignItems:
          "flex-start",

        paddingVertical:
          spacing.md,

        borderBottomWidth: 1,
        borderBottomColor:
          colors.divider,
      },

      commentContent: {
        flex: 1,
        minWidth: 0,

        marginLeft:
          spacing.md,
      },

      commentHeader: {
        flexDirection:
          "row",

        alignItems:
          "center",

        gap: spacing.sm,
      },

      commentAuthor: {
        flexShrink: 1,

        color:
          colors.onSurface,

        fontFamily:
          fonts.sansSemiBold,

        fontSize: 12,
        lineHeight: 16,
      },

      authorBadge: {
        paddingHorizontal: 7,
        paddingVertical: 2,

        borderRadius:
          radius.pill,

        backgroundColor:
          colors.plumSoft,

        borderWidth: 1,
        borderColor:
          colors.glassBorder,
      },

      authorBadgeText: {
        color:
          colors.plum,

        fontFamily:
          fonts.sansMedium,

        fontSize: 9,
        lineHeight: 12,

        letterSpacing: 0.4,
      },

      commentTime: {
        marginLeft: "auto",

        color:
          colors.muted,

        fontFamily:
          fonts.sans,

        fontSize: 10,
        lineHeight: 13,
      },

      commentText: {
        marginTop:
          spacing.xs,

        color:
          colors.onSurfaceSecondary,

        fontFamily:
          fonts.sans,

        fontSize: 13,
        lineHeight: 19,
      },

      empty: {
        flex: 1,

        minHeight: 260,

        alignItems:
          "center",

        justifyContent:
          "center",

        paddingHorizontal:
          spacing.xl,
      },

      emptySpark: {
        color:
          colors.plum,

        fontFamily:
          fonts.display,

        fontSize: 28,
        lineHeight: 32,
      },

      emptyTitle: {
        marginTop:
          spacing.md,

        color:
          colors.onSurface,

        fontFamily:
          fonts.display,

        fontSize: 20,
        lineHeight: 26,
      },

      emptyText: {
        maxWidth: 260,

        marginTop:
          spacing.sm,

        color:
          colors.muted,

        fontFamily:
          fonts.sans,

        fontSize: 12,
        lineHeight: 18,

        textAlign:
          "center",
      },

      composer: {
        paddingHorizontal:
          spacing.lg,

        paddingTop:
          spacing.md,

        paddingBottom:
          spacing.lg,

        borderTopWidth: 1,
        borderTopColor:
          colors.divider,

        flexDirection:
          "row",

        alignItems:
          "flex-end",

        gap: spacing.sm,

        backgroundColor:
          colors.surfaceSecondary,
      },

      guestAvatar: {
        width: 36,
        height: 36,

        borderRadius:
          radius.pill,

        alignItems:
          "center",

        justifyContent:
          "center",

        backgroundColor:
          colors.surfaceTertiary,

        borderWidth: 1,
        borderColor:
          colors.border,
      },

      inputWrap: {
        flex: 1,

        minHeight: 44,

        flexDirection:
          "row",

        alignItems:
          "flex-end",

        backgroundColor:
          colors.surfaceTertiary,

        borderWidth: 1,
        borderColor:
          colors.glassBorder,

        borderRadius:
          radius.lg,

        paddingLeft:
          spacing.md,

        paddingRight: 4,

        paddingVertical: 4,
      },

      input: {
        flex: 1,

        maxHeight: 110,

        paddingVertical: 8,
        paddingRight:
          spacing.sm,

        color:
          colors.onSurface,

        fontFamily:
          fonts.sans,

        fontSize: 13,
        lineHeight: 18,
      },

      sendButton: {
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
          colors.plum,
      },

      sendDisabled: {
        opacity: 0.35,
      },

      pressed: {
        opacity: 0.78,
      },
    }),
  );