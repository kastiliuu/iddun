import React, {
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import {
  useLocalSearchParams,
  useRouter,
} from "expo-router";
import { BottomSheetModal } from "@gorhom/bottom-sheet";

import {
  getClientProfile,
  type ClientPublicProfile,
  type WorkPost,
} from "@/api/feed";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { CommentsSheet } from "@/components/CommentsSheet";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { PostCard } from "@/components/PostCard";
import {
  fonts,
  makeStyles,
  radius,
  spacing,
  touch,
  typography,
  useTheme,
} from "@/theme";

/**
 * Página da Cliente (PR 4a; D-SOC-03, 12, 13): foto, nome e publicações
 * públicas. Nada de salvos, agendamentos ou cidade. Só existe com conta
 * ativa e ao menos uma publicação pública; fora disso, "não encontrado".
 */
export default function ClientProfileScreen() {
  const styles = useStyles();
  const { colors } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ id: string }>();
  const commentsRef = useRef<BottomSheetModal>(null);

  const [profile, setProfile] = useState<ClientPublicProfile | null>(null);
  const [posts, setPosts] = useState<WorkPost[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    getClientProfile(params.id)
      .then((response) => {
        if (!mounted) {
          return;
        }
        setProfile(response);
        setPosts(response.posts);
        setNextCursor(response.nextCursor);
      })
      .catch(() => {
        if (mounted) {
          setProfile(null);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [params.id]);

  const goBack = () => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace("/(tabs)");
    }
  };

  const loadMore = async () => {
    if (!nextCursor || loadingMore) {
      return;
    }

    setLoadingMore(true);
    try {
      const response = await getClientProfile(params.id, nextCursor);
      setPosts((current) => [...current, ...response.posts]);
      setNextCursor(response.nextCursor);
    } catch {
      setNextCursor(null);
    } finally {
      setLoadingMore(false);
    }
  };

  const openComments = (postId: string) => {
    setSelectedPostId(postId);
    commentsRef.current?.present();
  };

  const backButton = (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Voltar"
      onPress={goBack}
      style={styles.headerButton}
    >
      <Icon name="arrow-left" size={20} color={colors.onSurface} />
    </Pressable>
  );

  if (loading) {
    return (
      <View
        style={styles.loading}
        accessibilityRole="progressbar"
        accessibilityLabel="Carregando perfil"
      >
        <ActivityIndicator color={colors.plum} />
      </View>
    );
  }

  if (!profile) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>{backButton}</View>
        <EmptyState
          title="Perfil não encontrado"
          description="Esse perfil não está disponível."
          actionLabel="Voltar ao início"
          onActionPress={() => router.replace("/(tabs)")}
        />
      </View>
    );
  }

  const countLabel =
    profile.postsCount === 1
      ? "1 publicação"
      : `${profile.postsCount} publicações`;

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>{backButton}</View>

        <View style={styles.hero}>
          <Avatar name={profile.name} uri={profile.avatar} size={88} />
          <Text style={styles.name} accessibilityRole="header">
            {profile.name}
          </Text>
          <Text style={styles.meta}>{`Cliente IDDUN · ${countLabel}`}</Text>
        </View>

        <View style={styles.posts}>
          {posts.map((post) => (
            <PostCard
              key={post.id}
              id={post.id}
              author={{
                id: post.author.id,
                routeId: post.author.routeId,
                name: post.author.name,
                avatar: post.author.avatar,
                kind: post.author.kind,
              }}
              image={post.image}
              media={post.media}
              likesCount={post.likesCount}
              likedByMe={post.likedByMe}
              mine={post.mine}
              caption={post.caption}
              commentsCount={post.commentsCount}
              showFollow={false}
              onRemoved={() =>
                setPosts((current) =>
                  current.filter((item) => item.id !== post.id),
                )
              }
              onCommentsPress={() => openComments(post.id)}
            />
          ))}
        </View>

        {nextCursor ? (
          <View style={styles.more}>
            <Button
              title="Ver mais"
              variant="outline"
              loading={loadingMore}
              onPress={() => void loadMore()}
            />
          </View>
        ) : null}
      </ScrollView>

      <CommentsSheet
        ref={commentsRef}
        postId={selectedPostId ?? ""}
        postAuthor={{
          id: profile.id,
          name: profile.name,
          kind: "client",
        }}
        onRequireLogin={() => {
          commentsRef.current?.dismiss();
          router.push("/login");
        }}
      />
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },

  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.surface,
  },

  content: {
    paddingTop: spacing.xxxl,
    paddingBottom: spacing.xxxl * 2,
  },

  header: {
    paddingTop: spacing.sm,
    paddingHorizontal: spacing.lg,
  },

  headerButton: {
    width: touch.minimum,
    height: touch.minimum,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },

  hero: {
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.xl,
  },

  name: {
    marginTop: spacing.sm,
    color: colors.onSurface,
    fontFamily: fonts.display,
    fontSize: typography.title,
    textAlign: "center",
  },

  meta: {
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sansMedium,
    fontSize: typography.bodySmall,
  },

  posts: {
    gap: spacing.xl,
  },

  more: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xl,
  },
}));
