import React, {
  forwardRef,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  ActivityIndicator,
  Pressable,
  Text,
  View,
} from "react-native";
import {
  BottomSheetBackdrop,
  BottomSheetModal,
  BottomSheetScrollView,
  BottomSheetTextInput,
} from "@gorhom/bottom-sheet";

import {
  addPostComment,
  deletePostComment,
  getPostComments,
  hidePostComment,
  type PostComment,
} from "@/api/feed";
import { Avatar } from "@/components/Avatar";
import {
  ReportModal,
  type ReportTarget,
} from "@/components/ReportModal";
import { useToast } from "@/components/Toast";
import { store } from "@/store/local";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  useTheme,
} from "@/theme";

/**
 * Comentários reais (PR 3; DEC-ID-229, D-SOC-02): respostas em um nível,
 * quem comentou apaga o próprio, a autoria do post oculta, todos podem
 * denunciar. Comentar exige conta.
 */
type CommentsSheetProps = {
  postId: string;

  postAuthor?: {
    id: string;
    name: string;
    kind:
      | "client"
      | "professional"
      | "establishment";
  };

  onRequireLogin?: () => void;

  /** Avisa a tela quando o total muda (novo, apagado ou ocultado). */
  onCountChange?: (total: number) => void;
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
      onRequireLogin,
      onCountChange,
    },
    ref,
  ) {
    const styles = useStyles();
    const { colors } = useTheme();
    const toast = useToast();
    const [items, setItems] = useState<PostComment[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [body, setBody] = useState("");
    const [replyTo, setReplyTo] = useState<PostComment | null>(null);
    const [sending, setSending] = useState(false);
    const [report, setReport] = useState<ReportTarget | null>(null);
    const signedIn = Boolean(store.getUser());

    const load = useCallback(async () => {
      if (!postId) {
        return;
      }

      setLoading(true);
      try {
        const response = await getPostComments(postId);
        setItems(response.items);
        setTotal(response.total);
        onCountChange?.(response.total);
      } catch (error) {
        toast.show({
          title: "Não foi possível carregar os comentários",
          body: error instanceof Error ? error.message : "Tente novamente.",
          icon: "alert-circle",
        });
      } finally {
        setLoading(false);
      }
    }, [postId, onCountChange, toast]);

    useEffect(() => {
      setItems([]);
      setTotal(0);
      setReplyTo(null);
      setBody("");
      void load();
    }, [postId, load]);

    const send = async () => {
      if (!signedIn) {
        onRequireLogin?.();
        return;
      }

      if (!body.trim() || sending) {
        return;
      }

      setSending(true);
      try {
        await addPostComment(postId, body.trim(), replyTo?.id ?? null);
        setBody("");
        setReplyTo(null);
        await load();
      } catch (error) {
        toast.show({
          title: "Não foi possível comentar",
          body: error instanceof Error ? error.message : "Tente novamente.",
          icon: "alert-circle",
        });
      } finally {
        setSending(false);
      }
    };

    const act = async (action: () => Promise<unknown>) => {
      try {
        await action();
        await load();
      } catch (error) {
        toast.show({
          title: "Não foi possível atualizar",
          body: error instanceof Error ? error.message : "Tente novamente.",
          icon: "alert-circle",
        });
      }
    };

    const renderComment = (item: PostComment, isReply = false) => (
      <View
        key={item.id}
        style={[styles.comment, isReply && styles.reply]}
      >
        <Avatar name={item.author.name} uri={item.author.avatar} size={isReply ? 28 : 34} />
        <View style={styles.commentBody}>
          <Text style={styles.commentText}>
            <Text style={styles.commentAuthor}>{item.author.name} </Text>
            {item.body}
          </Text>
          <View style={styles.commentActions}>
            {!isReply && signedIn ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Responder a ${item.author.name}`}
                onPress={() => setReplyTo(item)}
                style={styles.linkButton}
              >
                <Text style={styles.linkText}>Responder</Text>
              </Pressable>
            ) : null}
            {item.canDelete ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void act(() => deletePostComment(item.id))}
                style={styles.linkButton}
              >
                <Text style={styles.linkText}>Apagar</Text>
              </Pressable>
            ) : item.canHide ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void act(() => hidePostComment(item.id))}
                style={styles.linkButton}
              >
                <Text style={styles.linkText}>Ocultar</Text>
              </Pressable>
            ) : null}
            {signedIn && !item.mine ? (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Denunciar comentário de ${item.author.name}`}
                onPress={() => setReport({ type: "comment", id: item.id })}
                style={styles.linkButton}
              >
                <Text style={styles.linkText}>Denunciar</Text>
              </Pressable>
            ) : null}
          </View>
          {item.replies?.map((reply) => renderComment(reply, true))}
        </View>
      </View>
    );

    return (
      <BottomSheetModal
        ref={ref}
        index={0}
        snapPoints={["70%"]}
        enablePanDownToClose
        keyboardBehavior="interactive"
        backdropComponent={(props) => (
          <BottomSheetBackdrop
            {...props}
            appearsOnIndex={0}
            disappearsOnIndex={-1}
            opacity={0.6}
          />
        )}
        backgroundStyle={styles.sheetBackground}
        handleIndicatorStyle={styles.handle}
      >
        <View style={styles.header}>
          <Text style={styles.title} accessibilityRole="header">
            {`Comentários (${total})`}
          </Text>
        </View>

        <BottomSheetScrollView contentContainerStyle={styles.list}>
          {loading && !items.length ? (
            <ActivityIndicator color={colors.plum} />
          ) : items.length ? (
            items.map((item) => renderComment(item))
          ) : (
            <Text style={styles.empty}>Ainda não há comentários.</Text>
          )}
        </BottomSheetScrollView>

        <View style={styles.composer}>
          {replyTo ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Cancelar resposta"
              onPress={() => setReplyTo(null)}
              style={styles.replyBanner}
            >
              <Text style={styles.replyBannerText} numberOfLines={1}>
                {`Respondendo a ${replyTo.author.name} · cancelar`}
              </Text>
            </Pressable>
          ) : null}
          {signedIn ? (
            <View style={styles.inputRow}>
              <BottomSheetTextInput
                value={body}
                onChangeText={setBody}
                placeholder="Escreva um comentário…"
                placeholderTextColor={colors.muted}
                maxLength={1000}
                multiline
                style={styles.input}
                accessibilityLabel="Escreva um comentário"
              />
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: !body.trim() || sending }}
                disabled={!body.trim() || sending}
                onPress={() => void send()}
                style={[styles.send, (!body.trim() || sending) && styles.disabled]}
              >
                {sending ? (
                  <ActivityIndicator color={colors.onBrandPrimary} />
                ) : (
                  <Text style={styles.sendText}>Enviar</Text>
                )}
              </Pressable>
            </View>
          ) : (
            <Pressable
              accessibilityRole="button"
              onPress={onRequireLogin}
              style={styles.send}
            >
              <Text style={styles.sendText}>Entrar para comentar</Text>
            </Pressable>
          )}
        </View>

        <ReportModal target={report} onClose={() => setReport(null)} />
      </BottomSheetModal>
    );
  });

const useStyles = makeStyles((colors) => ({
  sheetBackground: {
    backgroundColor: colors.surfaceSecondary,
  },

  handle: {
    backgroundColor: colors.glassBorderStrong,
  },

  header: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },

  title: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 17,
  },

  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
    gap: spacing.lg,
  },

  empty: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 14,
  },

  comment: {
    flexDirection: "row",
    gap: spacing.md,
  },

  reply: {
    marginTop: spacing.md,
  },

  commentBody: {
    flex: 1,
    minWidth: 0,
  },

  commentText: {
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 14,
    lineHeight: 20,
  },

  commentAuthor: {
    fontFamily: fonts.sansSemiBold,
  },

  commentActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.md,
  },

  linkButton: {
    minHeight: touch.minimum,
    justifyContent: "center",
  },

  linkText: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: 12,
  },

  composer: {
    padding: spacing.lg,
    gap: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.glassBorder,
  },

  replyBanner: {
    minHeight: touch.minimum,
    justifyContent: "center",
  },

  replyBannerText: {
    color: colors.plum,
    fontFamily: fonts.sansMedium,
    fontSize: 13,
  },

  inputRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
  },

  input: {
    flex: 1,
    minHeight: touch.minimum,
    maxHeight: 120,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.glassBorderStrong,
    color: colors.onSurface,
    fontFamily: fonts.sans,
    fontSize: 15,
  },

  send: {
    minHeight: touch.minimum,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radius.pill,
    backgroundColor: colors.brandPrimary,
  },

  sendText: {
    color: colors.onBrandPrimary,
    fontFamily: fonts.sansSemiBold,
    fontSize: 14,
  },

  disabled: {
    opacity: 0.5,
  },
}));
