import { useEffect, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

/**
 * Estado local usado enquanto o backend Flask ainda não está integrado.
 *
 * IMPORTANTE:
 * Favoritos, follows, comentários, notificações e sessão serão
 * posteriormente substituídos/sincronizados com a API.
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

export type NotificationKind =
  | "iddun_now"
  | "follow_back"
  | "system";

export type Notification = {
  id: string;
  kind: NotificationKind;

  title: string;
  body: string;

  timeLabel?: string;
  serviceId?: string;
  authorId?: string;

  read: boolean;
  createdAt: number;
};

type PersistedStore = {
  posts?: string[];
  professionals?: string[];
  services?: string[];

  follows?: string[];

  user?: CurrentUser;

  comments?: Record<string, Comment[]>;
  notifications?: Notification[];
};

const STORE_KEY = "iddun_store";

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

  private user: CurrentUser = null;

  private comments: Record<string, Comment[]> =
    {};

  private notifications: Notification[] = [];

  private listeners = new Set<() => void>();

  private loaded = false;

  /**
   * Um timer por perfil seguido.
   *
   * Isso evita acumular timers sem controle e permite
   * cancelar o alerta simulado caso o usuário deixe de seguir
   * antes dele acontecer.
   */
  private followAlertTimers =
    new Map<string, ReturnType<typeof setTimeout>>();

  async load() {
    if (this.loaded) return;

    try {
      const raw =
        await AsyncStorage.getItem(STORE_KEY);

      if (raw) {
        const parsed: PersistedStore =
          JSON.parse(raw);

        this.data.posts = new Set(
          parsed.posts ?? [],
        );

        this.data.professionals = new Set(
          parsed.professionals ?? [],
        );

        this.data.services = new Set(
          parsed.services ?? [],
        );

        this.follows = new Set(
          parsed.follows ?? [],
        );

        this.user = parsed.user ?? null;

        this.comments =
          parsed.comments ?? {};

        this.notifications =
          parsed.notifications ?? [];
      }
    } catch (error) {
      logStoreError(
        "Falha ao carregar estado local.",
        error,
      );
    }

    if (
      Object.keys(this.comments).length === 0
    ) {
      this.seedComments();
    }

    if (this.notifications.length === 0) {
      this.seedNotifications();
    }

    this.loaded = true;

    await this.persist();

    this.emit();
  }

  private async persist() {
    try {
      const payload: PersistedStore = {
        posts: [...this.data.posts],

        professionals: [
          ...this.data.professionals,
        ],

        services: [
          ...this.data.services,
        ],

        follows: [...this.follows],

        user: this.user,

        comments: this.comments,

        notifications:
          this.notifications,
      };

      await AsyncStorage.setItem(
        STORE_KEY,
        JSON.stringify(payload),
      );
    } catch (error) {
      logStoreError(
        "Falha ao persistir estado local.",
        error,
      );
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
    options?: {
      authorName?: string;

      onAlert?: (
        notification: Notification,
      ) => void;
    },
  ) {
    if (this.follows.has(id)) {
      this.follows.delete(id);

      this.cancelFollowAlert(id);
    } else {
      this.follows.add(id);

      this.scheduleMockFollowAlert(
        id,
        options,
      );
    }

    this.persistAndEmit();
  }

  isFollowing(id: string) {
    return this.follows.has(id);
  }

  following() {
    return [...this.follows];
  }

  private scheduleMockFollowAlert(
    authorId: string,
    options?: {
      authorName?: string;

      onAlert?: (
        notification: Notification,
      ) => void;
    },
  ) {
    this.cancelFollowAlert(authorId);

    /**
     * Apenas para demonstrar IDDUN Now antes da API real.
     */
    const delay =
      4000 + Math.random() * 5000;

    const timer = setTimeout(() => {
      this.followAlertTimers.delete(
        authorId,
      );

      /**
       * Se a pessoa deixou de seguir nesse meio tempo,
       * não geramos o alerta.
       */
      if (!this.follows.has(authorId)) {
        return;
      }

      const notification: Notification = {
        id: createId("notification"),

        kind: "iddun_now",

        title: options?.authorName
          ? `Horário disponível · ${options.authorName}`
          : "Novo horário disponível",

        body:
          "Um novo horário acabou de abrir com alguém que você segue.",

        timeLabel:
          this.randomSoonSlot(),

        authorId,

        read: false,

        createdAt: Date.now(),
      };

      this.notifications = [
        notification,
        ...this.notifications,
      ];

      this.persistAndEmit();

      options?.onAlert?.(
        notification,
      );
    }, delay);

    this.followAlertTimers.set(
      authorId,
      timer,
    );
  }

  private cancelFollowAlert(
    authorId: string,
  ) {
    const timer =
      this.followAlertTimers.get(
        authorId,
      );

    if (!timer) return;

    clearTimeout(timer);

    this.followAlertTimers.delete(
      authorId,
    );
  }

  private randomSoonSlot() {
    const hours = [
      14,
      15,
      16,
      17,
      18,
      19,
    ];

    const minutes = [
      "00",
      "15",
      "30",
      "45",
    ];

    const hour =
      hours[
        Math.floor(
          Math.random() *
            hours.length,
        )
      ];

    const minute =
      minutes[
        Math.floor(
          Math.random() *
            minutes.length,
        )
      ];

    return `Hoje ${hour}:${minute}`;
  }

  /*
   * USUÁRIO / SESSÃO MOCK
   */

  setUser(user: CurrentUser) {
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
    return (
      this.comments[postId] ?? []
    );
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
   * NOTIFICAÇÕES
   */

  getNotifications() {
    return [...this.notifications];
  }

  unreadCount() {
    return this.notifications.filter(
      (notification) =>
        !notification.read,
    ).length;
  }

  markRead(id: string) {
    this.notifications =
      this.notifications.map(
        (notification) =>
          notification.id === id
            ? {
                ...notification,
                read: true,
              }
            : notification,
      );

    this.persistAndEmit();
  }

  markAllRead() {
    this.notifications =
      this.notifications.map(
        (notification) => ({
          ...notification,
          read: true,
        }),
      );

    this.persistAndEmit();
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

  private seedNotifications() {
    const now = Date.now();

    this.notifications = [
      {
        id: "notification_welcome",

        kind: "system",

        title: "Bem-vindo ao IDDUN ✦",

        body:
          "Descubra profissionais, salve favoritos e encontre sua próxima experiência.",

        read: false,

        createdAt:
          now - 60 * 60 * 1000,
      },
    ];
  }

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