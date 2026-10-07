import { useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * Estado local para interações ainda não sincronizadas com a API.
 *
 * IMPORTANTE:
 * Favoritos e comentários ainda possuem estado local em alguns fluxos.
 * Follows server-backed e notificações usam a API real.
 */

export type FavoriteKind =
  | "posts"
  | "professionals"
  | "services";

export type Role =
  | "client"
  | "professional"
  | "establishment";

export type CurrentUser =
  | {
      role: Role;
      id?: number | string;
      name: string;
      email: string;
      avatar?: string;

      /**
       * ID do perfil profissional/estabelecimento correspondente
       * quando existir no backend.
       */
      profileId?: string;

      businessName?: string;
      specialty?: string;
      city?: string;
      neighborhood?: string;
      emailVerified?: boolean;
    }
  | null;

export type Comment = {
  id: string;
  postId: string;

  /**
   * Futuramente será o ID real do usuário.
   */
  authorId?: string;

  author: string;
  role: Role | "guest";
  text: string;
  createdAt: number;

  /**
   * Indica que o comentário foi feito pelo autor da publicação.
   * Temporário para a fase mock.
   */
  isAuthorReply?: boolean;
};

type PersistedScope = {
  posts?: string[];
  professionals?: string[];
  services?: string[];
  follows?: string[];
  graphFollows?: string[];
  graphSaves?: string[];
  comments?: Record<string, Comment[]>;
};

type PersistedStore = PersistedScope & {
  user?: CurrentUser;
  scopes?: Record<string, PersistedScope>;
};

const STORE_KEY = "iddun_store";
const GUEST_SCOPE = "guest";

function scopeKeyFor(user: CurrentUser) {
  if (!user) return GUEST_SCOPE;

  if (user.id !== undefined && user.id !== null) {
    return `account-id:${String(user.id)}`;
  }

  return emailScopeKeyFor(user);
}

function emailScopeKeyFor(user: NonNullable<CurrentUser>) {
  return `account-email:${user.email.trim().toLowerCase()}`;
}

const KEYS = {
  onboarded: "iddun_onboarded",
  loggedIn: "iddun_logged_in",
};

function logStoreError(
  message: string,
  error: unknown,
) {
  if (__DEV__) {
    console.warn(`[IDDUN Store] ${message}`, error);
  }
}

function createId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

class LocalStore {
  private data: Record<
    FavoriteKind,
    Set<string>
  > = {
    posts: new Set(),
    professionals: new Set(),
    services: new Set(),
  };

  private follows = new Set<string>();

  private graphFollows =
    new Set<string>();

  private graphSaves =
    new Set<string>();

  private user: CurrentUser = null;

  private scopes: Record<string, PersistedScope> = {};

  private activeScopeKey = GUEST_SCOPE;

  private persistence: Promise<void> = Promise.resolve();

  private comments: Record<string, Comment[]> =
    {};

  private listeners = new Set<() => void>();

  private loaded = false;

  async load() {
    if (this.loaded) return;

    try {
      const raw =
        await AsyncStorage.getItem(STORE_KEY);

      if (raw) {
        const parsed: PersistedStore =
          JSON.parse(raw);

        this.user = parsed.user ?? null;

        if (parsed.scopes) {
          this.scopes = parsed.scopes;
        } else {
          this.scopes[scopeKeyFor(this.user)] = {
            posts: parsed.posts ?? [],
            professionals: parsed.professionals ?? [],
            services: parsed.services ?? [],
            follows: parsed.follows ?? [],
            comments: parsed.comments ?? {},
          };
        }

        this.activeScopeKey = scopeKeyFor(this.user);
        this.applyScope(this.scopes[this.activeScopeKey]);
      }
    } catch (error) {
      logStoreError(
        "Falha ao carregar estado local.",
        error,
      );
    }

    this.seedEmptyScope();

    this.loaded = true;

    await this.persist();

    this.emit();
  }

  private async persist() {
    this.saveActiveScope();

    const payload: PersistedStore = {
      user: this.user,
      scopes: this.scopes,
    };

    const serialized = JSON.stringify(payload);

    this.persistence = this.persistence
      .catch(() => {})
      .then(async () => {
        try {
          await AsyncStorage.setItem(
            STORE_KEY,
            serialized,
          );
        } catch (error) {
          logStoreError(
            "Falha ao persistir estado local.",
            error,
          );
        }
      });

    await this.persistence;
  }

  private saveActiveScope() {
    this.scopes[this.activeScopeKey] = {
      posts: [...this.data.posts],
      professionals: [...this.data.professionals],
      services: [...this.data.services],
      follows: [...this.follows],
      graphFollows: [
        ...this.graphFollows,
      ],
      graphSaves: [
        ...this.graphSaves,
      ],
      comments: this.comments,
    };
  }

  private applyScope(scope?: PersistedScope) {
    this.data.posts = new Set(scope?.posts ?? []);
    this.data.professionals = new Set(
      scope?.professionals ?? [],
    );
    this.data.services = new Set(
      scope?.services ?? [],
    );
    this.follows = new Set(scope?.follows ?? []);
    this.graphFollows =
      new Set(
        scope?.graphFollows ?? [],
      );
    this.graphSaves =
      new Set(
        scope?.graphSaves ?? [],
      );
    this.comments = scope?.comments ?? {};
  }

  private seedEmptyScope() {
    if (Object.keys(this.comments).length === 0) {
      this.seedComments();
    }

  }

  private persistAndEmit() {
    void this.persist();
    this.emit();
  }

  /*
   * FAVORITOS
   */

  toggleFavorite(
    kind: FavoriteKind,
    id: string,
  ) {
    const set = this.data[kind];

    if (set.has(id)) {
      set.delete(id);
    } else {
      set.add(id);
    }

    this.persistAndEmit();
  }

  isFavorite(
    kind: FavoriteKind,
    id: string,
  ) {
    return this.data[kind].has(id);
  }

  favorites(kind: FavoriteKind) {
    return [...this.data[kind]];
  }

  /*
   * FOLLOWS
   */

  toggleFollow(
    id: string,
  ) {
    if (this.follows.has(id)) {
      this.follows.delete(id);
    } else {
      this.follows.add(id);
    }

    this.persistAndEmit();
  }

  isFollowing(id: string) {
    return this.follows.has(id);
  }

  following() {
    return [...this.follows];
  }

  private graphKey(
    targetType: string,
    targetId: number,
  ) {
    return (
      targetType
      + ":"
      + targetId
    );
  }

  private parseGraphKey(
    key: string,
  ) {
    const separator =
      key.lastIndexOf(":");

    if (
      separator <= 0 ||
      separator ===
        key.length - 1
    ) {
      return null;
    }

    const targetType =
      key.slice(
        0,
        separator,
      );

    const targetId =
      Number(
        key.slice(
          separator + 1,
        ),
      );

    if (
      !Number.isInteger(
        targetId,
      ) ||
      targetId <= 0
    ) {
      return null;
    }

    return {
      targetType,
      targetId,
    };
  }

  isGraphFollowing(
    targetType: string,
    targetId: number,
  ) {
    return this.graphFollows.has(
      this.graphKey(
        targetType,
        targetId,
      ),
    );
  }

  isGraphSaved(
    targetType: string,
    targetId: number,
  ) {
    return this.graphSaves.has(
      this.graphKey(
        targetType,
        targetId,
      ),
    );
  }

  setGraphFollowing(
    targetType: string,
    targetId: number,
    value: boolean,
  ) {
    const key =
      this.graphKey(
        targetType,
        targetId,
      );

    if (value) {
      this.graphFollows.add(
        key,
      );
    } else {
      this.graphFollows.delete(
        key,
      );
    }

    this.persistAndEmit();
  }

  setGraphSaved(
    targetType: string,
    targetId: number,
    value: boolean,
  ) {
    const key =
      this.graphKey(
        targetType,
        targetId,
      );

    if (value) {
      this.graphSaves.add(
        key,
      );
    } else {
      this.graphSaves.delete(
        key,
      );
    }

    this.persistAndEmit();
  }

  graphState() {
    const follows =
      [...this.graphFollows]
        .map((key) =>
          this.parseGraphKey(
            key,
          ),
        )
        .filter(
          (
            item,
          ): item is {
            targetType: string;
            targetId: number;
          } =>
            item !== null,
        );

    const saves =
      [...this.graphSaves]
        .map((key) =>
          this.parseGraphKey(
            key,
          ),
        )
        .filter(
          (
            item,
          ): item is {
            targetType: string;
            targetId: number;
          } =>
            item !== null,
        );

    return {
      follows,
      saves,
    };
  }

  replaceGraphState(
    state: {
      follows: {
        targetType: string;
        targetId: number;
      }[];
      saves: {
        targetType: string;
        targetId: number;
      }[];
    },
  ) {
    this.graphFollows =
      new Set(
        state.follows.map(
          (item) =>
            this.graphKey(
              item.targetType,
              item.targetId,
            ),
        ),
      );

    this.graphSaves =
      new Set(
        state.saves.map(
          (item) =>
            this.graphKey(
              item.targetType,
              item.targetId,
            ),
        ),
      );

    this.persistAndEmit();
  }

  /*
   * USUÁRIO E DADOS LOCAIS DA CONTA ATIVA
   */

  setUser(user: CurrentUser) {
    const nextScopeKey =
      scopeKeyFor(user);

    if (
      nextScopeKey !==
      this.activeScopeKey
    ) {
      const previousScopeKey =
        this.activeScopeKey;

      this.saveActiveScope();

      if (
        user &&
        user.id !== undefined &&
        user.id !== null
      ) {
        const emailScopeKey =
          emailScopeKeyFor(user);

        if (
          !this.scopes[
            nextScopeKey
          ] &&
          this.scopes[
            emailScopeKey
          ]
        ) {
          this.scopes[
            nextScopeKey
          ] =
            this.scopes[
              emailScopeKey
            ];

          delete this.scopes[
            emailScopeKey
          ];
        }

        if (
          previousScopeKey ===
          GUEST_SCOPE
        ) {
          const guest =
            this.scopes[
              GUEST_SCOPE
            ] ?? {};

          const account =
            this.scopes[
              nextScopeKey
            ] ?? {};

          const mergeStrings = (
            current:
              string[] | undefined,
            incoming:
              string[] | undefined,
          ) => [
            ...new Set([
              ...(current ?? []),
              ...(incoming ?? []),
            ]),
          ];

          this.scopes[
            nextScopeKey
          ] = {
            ...account,
            posts:
              mergeStrings(
                account.posts,
                guest.posts,
              ),
            professionals:
              mergeStrings(
                account.professionals,
                guest.professionals,
              ),
            services:
              mergeStrings(
                account.services,
                guest.services,
              ),
            follows:
              mergeStrings(
                account.follows,
                guest.follows,
              ),
            graphFollows:
              mergeStrings(
                account.graphFollows,
                guest.graphFollows,
              ),
            graphSaves:
              mergeStrings(
                account.graphSaves,
                guest.graphSaves,
              ),
          };
        }
      }

      this.activeScopeKey =
        nextScopeKey;

      this.applyScope(
        this.scopes[
          nextScopeKey
        ],
      );

      this.seedEmptyScope();
    }

    this.user = user;
    this.persistAndEmit();
  }

  getUser() {
    return this.user;
  }

  /*
   * COMENTÁRIOS
   */

  getComments(postId: string) {
    return this.comments[postId] ?? [];
  }

  addComment(
    postId: string,
    text: string,
    options?: {
      isAuthorReply?: boolean;
    },
  ) {
    const cleanText = text.trim();

    if (!cleanText) {
      return null;
    }

    const comment: Comment = {
      id: createId("comment"),
      postId,

      authorId:
        this.user?.profileId,

      author:
        this.user?.name ??
        "Visitante",

      role:
        this.user?.role ??
        "guest",

      text: cleanText,
      createdAt: Date.now(),

      isAuthorReply:
        options?.isAuthorReply,
    };

    const current =
      this.comments[postId] ?? [];

    this.comments[postId] = [
      ...current,
      comment,
    ];

    this.persistAndEmit();

    return comment;
  }

  /*
   * SUBSCRIPTIONS
   */

  subscribe(
    listener: () => void,
  ) {
    this.listeners.add(listener);

    return () => {
      this.listeners.delete(
        listener,
      );
    };
  }

  private emit() {
    this.listeners.forEach(
      (listener) => listener(),
    );
  }

  /*
   * MOCK SEEDS
   */

  private seedComments() {
    const now = Date.now();

    const createSeedComment = ({
      id,
      postId,
      author,
      text,
      minutesAgo,
      isAuthorReply = false,
    }: {
      id: string;
      postId: string;
      author: string;
      text: string;
      minutesAgo: number;
      isAuthorReply?: boolean;
    }): Comment => ({
      id,
      postId,
      author,

      role: isAuthorReply
        ? "professional"
        : "client",

      text,

      createdAt:
        now -
        minutesAgo * 60_000,

      isAuthorReply,
    });

    this.comments = {
      p1: [
        createSeedComment({
          id: "comment_p1_1",
          postId: "p1",
          author: "Ana Paula",
          text:
            "Ficou perfeito! ✦",
          minutesAgo: 45,
        }),

        createSeedComment({
          id: "comment_p1_2",
          postId: "p1",
          author: "Renata Mocelin",
          text:
            "Obrigada! Foi uma delícia criar esse resultado.",
          minutesAgo: 36,
          isAuthorReply: true,
        }),

        createSeedComment({
          id: "comment_p1_3",
          postId: "p1",
          author: "Julia M.",
          text:
            "Que acabamento lindo.",
          minutesAgo: 18,
        }),
      ],

      p3: [
        createSeedComment({
          id: "comment_p3_1",
          postId: "p3",
          author: "Marina S.",
          text:
            "Já salvei como inspiração.",
          minutesAgo: 92,
        }),

        createSeedComment({
          id: "comment_p3_2",
          postId: "p3",
          author: "João Martins",
          text:
            "Valeu! Esse estilo ficou muito bom mesmo.",
          minutesAgo: 63,
          isAuthorReply: true,
        }),
      ],

      p5: [
        createSeedComment({
          id: "comment_p5_1",
          postId: "p5",
          author: "Camila R.",
          text:
            "A combinação ficou incrível.",
          minutesAgo: 28,
        }),
      ],
    };
  }
}

export const store =
  new LocalStore();

/**
 * Hook temporário usado para fazer os componentes
 * reagirem às mudanças do LocalStore.
 *
 * Quando conectarmos React Query + API Flask,
 * vários desses usos serão substituídos por hooks
 * de dados reais.
 */
export function useStoreVersion() {
  const [
    version,
    setVersion,
  ] = useState(0);

  useEffect(() => {
    void store.load();

    return store.subscribe(() => {
      setVersion(
        (current) =>
          current + 1,
      );
    });
  }, []);

  return version;
}

/*
 * ONBOARDING
 */

export async function markOnboarded() {
  try {
    await AsyncStorage.setItem(
      KEYS.onboarded,
      "1",
    );
  } catch (error) {
    logStoreError(
      "Falha ao salvar onboarding.",
      error,
    );
  }
}

export async function getOnboarded() {
  try {
    return (
      (await AsyncStorage.getItem(
        KEYS.onboarded,
      )) === "1"
    );
  } catch (error) {
    logStoreError(
      "Falha ao consultar onboarding.",
      error,
    );

    return false;
  }
}

/*
 * AUTENTICAÇÃO MOCK
 */

export async function markLoggedIn() {
  try {
    await AsyncStorage.setItem(
      KEYS.loggedIn,
      "1",
    );
  } catch (error) {
    logStoreError(
      "Falha ao salvar sessão.",
      error,
    );
  }
}

export async function markLoggedOut() {
  try {
    await AsyncStorage.removeItem(
      KEYS.loggedIn,
    );
  } catch (error) {
    logStoreError(
      "Falha ao remover sessão.",
      error,
    );
  }

  store.setUser(null);
}

export async function isLoggedIn() {
  try {
    return (
      (await AsyncStorage.getItem(
        KEYS.loggedIn,
      )) === "1"
    );
  } catch (error) {
    logStoreError(
      "Falha ao consultar sessão.",
      error,
    );

    return false;
  }
}