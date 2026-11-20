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
import {
  followGraphTarget,
  unfollowGraphTarget,
} from "@/api/graph";
import { ApiError } from "@/api/client";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/Button";
import { CommentsSheet } from "@/components/CommentsSheet";
import { EmptyState } from "@/components/EmptyState";
import { Icon } from "@/components/Icon";
import { PostCard } from "@/components/PostCard";
import { openWebEditor, OwnerBanner } from "@/components/ProfileSections";
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
 * Página pessoal pública (ID-SOC-R1-04, substitui a D-SOC-13): foto, nome,
 * @username, seguidores e publicações. Nada de salvos, agendamentos ou
 * cidade. Existe para toda conta ativa; fora disso, "não encontrado".
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
  const [followBusy, setFollowBusy] = useState(false);
  const [followError, setFollowError] = useState<string | null>(null);

  // ID-SOC-R1-03: segue-se a pessoa (a conta), pelo alvo "person".
  const toggleFollow = async () => {
    if (!profile?.userId || followBusy) {
      return;
    }
    const next = !profile.following;
    setFollowBusy(true);
    setFollowError(null);
    try {
      if (next) {
        await followGraphTarget("person", profile.userId);
      } else {
        await unfollowGraphTarget("person", profile.userId);
      }
      setProfile((current) =>
        current
          ? {
              ...current,
              following: next,
              followerCount: Math.max(
                0,
                (current.followerCount ?? 0) + (next ? 1 : -1),
              ),
            }
          : current,
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.push("/login");
      } else {
        setFollowError("Não foi possível atualizar agora. Tente de novo.");
      }
    } finally {
      setFollowBusy(false);
    }
  };

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
          <Text style={styles.meta}>
            {[
              profile.username ? `@${profile.username}` : null,
              countLabel,
              typeof profile.followerCount === "number"
                ? profile.followerCount === 1
                  ? "1 seguidor"
                  : `${profile.followerCount} seguidores`
                : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </Text>
          {!profile.mine && profile.userId ? (
            <Button
              title={profile.following ? "Seguindo" : "Seguir"}
              variant={profile.following ? "secondary" : "primary"}
              onPress={toggleFollow}
              loading={followBusy}
              accessibilityLabel={`${profile.following ? "Deixar de seguir" : "Seguir"} ${profile.name}`}
            />
          ) : null}
          {profile.professional?.slug ? (
            <Button
              title="Ver serviços e portfólio"
              variant="outline"
              onPress={() =>
                router.push(`/professional/${profile.professional!.slug}`)
              }
            />
          ) : null}
          {followError ? (
            <Text style={styles.meta} accessibilityRole="alert">
              {followError}
            </Text>
          ) : null}
        </View>

        {profile.mine ? (
          // D-SOC-17: nome e foto da Cliente se editam no site por enquanto.
          <OwnerBanner
            message="Você está vendo seu perfil como o público vê."
            actionLabel="Editar no site"
            onPress={() => openWebEditor("/minha-conta/editar")}
          />
        ) : null}

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
