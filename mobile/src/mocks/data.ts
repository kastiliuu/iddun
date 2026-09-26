export type ProfileKind =
  | "professional"
  | "establishment";

export type Professional = {
  id: string;
  kind: ProfileKind;

  name: string;
  avatar: string;
  cover?: string;

  specialty: string;
  location: string;

  rating: number;
  reviewsCount: number;

  bio?: string;

  categories: string[];
};

export type Service = {
  id: string;

  authorId: string;
  authorKind: ProfileKind;

  name: string;
  category: string;

  description: string;

  image: string;

  durationMinutes: number;
  price: number;

  location: string;

  availabilityLabel?: string;

  availableSlots?: string[];
};

export type Post = {
  id: string;

  authorId: string;

  image: string;

  caption: string;

  rating?: number;

  commentsCount: number;

  serviceId?: string;

  createdAt: string;
};

export type Story = {
  id: string;

  profileId: string;

  seen: boolean;
};

export type IDDUNNowItem = {
  id: string;

  serviceId: string;

  professionalId: string;

  timeLabel: string;

  urgent?: boolean;
};

export type DiscoverItem = {
  id: string;

  sourceId: string;

  type:
    | "post"
    | "professional"
    | "establishment"
    | "service";

  title: string;

  subtitle?: string;

  image: string;

  rating?: number;

  location?: string;

  height: number;

  category?: string;
};

/*
 * PERFIS
 */

export const professionals: Professional[] = [
  {
    id: "pro_1",

    kind: "professional",

    name: "Renata Mocelin",

    avatar:
      "https://images.unsplash.com/photo-1596462502278-27bfdc403348?auto=format&fit=crop&w=500&q=80",

    cover:
      "https://images.unsplash.com/photo-1604654894610-df63bc536371?auto=format&fit=crop&w=1200&q=85",

    specialty:
      "Nail Designer",

    location:
      "Batel · Curitiba",

    rating: 4.9,

    reviewsCount: 128,

    bio:
      "Especialista em unhas com acabamento sofisticado, técnicas modernas e experiência personalizada.",

    categories: [
      "Unhas",
      "Alongamento",
      "Gel",
    ],
  },

  {
    id: "pro_2",

    kind: "professional",

    name: "Marina Alves",

    avatar:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=500&q=80",

    cover:
      "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=85",

    specialty:
      "Hair Stylist",

    location:
      "Água Verde · Curitiba",

    rating: 4.8,

    reviewsCount: 94,

    bio:
      "Cortes, coloração e transformação de imagem com foco em naturalidade.",

    categories: [
      "Cabelo",
      "Coloração",
      "Corte",
    ],
  },

  {
    id: "pro_3",

    kind: "professional",

    name: "João Martins",

    avatar:
      "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=500&q=80",

    cover:
      "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=1200&q=85",

    specialty:
      "Barber",

    location:
      "Centro · Curitiba",

    rating: 4.7,

    reviewsCount: 76,

    bio:
      "Barbearia contemporânea, cortes clássicos e modernos com atendimento individual.",

    categories: [
      "Barbearia",
      "Cabelo",
      "Barba",
    ],
  },

  {
    id: "pro_4",

    kind: "professional",

    name: "Camila Duarte",

    avatar:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=500&q=80",

    cover:
      "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=1200&q=85",

    specialty:
      "Lash Designer",

    location:
      "Bigorrilho · Curitiba",

    rating: 4.9,

    reviewsCount: 112,

    bio:
      "Extensão de cílios com mapeamentos personalizados e acabamento elegante.",

    categories: [
      "Cílios",
      "Sobrancelhas",
    ],
  },

  {
    id: "est_1",

    kind: "establishment",

    name: "Atelier Lumi",

    avatar:
      "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=500&q=80",

    cover:
      "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1200&q=85",

    specialty:
      "Beauty Studio",

    location:
      "Batel · Curitiba",

    rating: 4.8,

    reviewsCount: 203,

    bio:
      "Um espaço contemporâneo para cabelo, unhas e experiências de beleza.",

    categories: [
      "Cabelo",
      "Unhas",
      "Estética",
    ],
  },

  {
    id: "est_2",

    kind: "establishment",

    name: "Noma Beauty House",

    avatar:
      "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=500&q=80",

    cover:
      "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?auto=format&fit=crop&w=1200&q=85",

    specialty:
      "Beauty House",

    location:
      "Cabral · Curitiba",

    rating: 4.7,

    reviewsCount: 146,

    bio:
      "Beleza, bem-estar e atendimento personalizado em um só espaço.",

    categories: [
      "Cabelo",
      "Maquiagem",
      "Estética",
    ],
  },
];

/*
 * SERVIÇOS
 */

export const services: Service[] = [
  {
    id: "srv_1",

    authorId: "pro_1",

    authorKind: "professional",

    name:
      "Alongamento em Fibra",

    category: "Unhas",

    description:
      "Alongamento em fibra com preparação, estrutura, acabamento e esmaltação.",

    image:
      "https://images.unsplash.com/photo-1604654894610-df63bc536371?auto=format&fit=crop&w=900&q=85",

    durationMinutes: 120,

    price: 250,

    location:
      "Batel · Curitiba",

    availabilityLabel:
      "Hoje 14:30",

    availableSlots: [
      "14:30",
      "15:00",
      "15:30",
    ],
  },

  {
    id: "srv_2",

    authorId: "pro_1",

    authorKind: "professional",

    name:
      "Banho de Gel",

    category: "Unhas",

    description:
      "Estruturação da unha natural com gel para maior resistência e acabamento uniforme.",

    image:
      "https://images.unsplash.com/photo-1610992015732-2449b76344bc?auto=format&fit=crop&w=900&q=85",

    durationMinutes: 90,

    price: 160,

    location:
      "Batel · Curitiba",

    availabilityLabel:
      "Amanhã 10:30",

    availableSlots: [
      "10:30",
      "13:00",
      "14:40",
    ],
  },

  {
    id: "srv_3",

    authorId: "pro_2",

    authorKind: "professional",

    name:
      "Corte + Finalização",

    category: "Cabelo",

    description:
      "Corte personalizado com lavagem, tratamento leve e finalização.",

    image:
      "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&w=900&q=85",

    durationMinutes: 75,

    price: 180,

    location:
      "Água Verde · Curitiba",

    availabilityLabel:
      "Hoje 16:00",

    availableSlots: [
      "16:00",
      "17:30",
    ],
  },

  {
    id: "srv_4",

    authorId: "pro_3",

    authorKind: "professional",

    name:
      "Corte Masculino",

    category: "Barbearia",

    description:
      "Corte masculino com acabamento, lavagem e styling.",

    image:
      "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=900&q=85",

    durationMinutes: 45,

    price: 80,

    location:
      "Centro · Curitiba",

    availabilityLabel:
      "Hoje 18:15",

    availableSlots: [
      "18:15",
      "19:00",
    ],
  },

  {
    id: "srv_5",

    authorId: "pro_4",

    authorKind: "professional",

    name:
      "Extensão de Cílios",

    category: "Cílios",

    description:
      "Extensão personalizada de acordo com o formato dos olhos e o resultado desejado.",

    image:
      "https://images.unsplash.com/photo-1583001931096-959e9a1a6223?auto=format&fit=crop&w=900&q=85",

    durationMinutes: 120,

    price: 220,

    location:
      "Bigorrilho · Curitiba",

    availabilityLabel:
      "Amanhã 13:30",

    availableSlots: [
      "13:30",
      "15:40",
    ],
  },

  {
    id: "srv_6",

    authorId: "est_1",

    authorKind: "establishment",

    name:
      "Coloração Premium",

    category: "Cabelo",

    description:
      "Coloração personalizada com diagnóstico, proteção dos fios e finalização.",

    image:
      "https://images.unsplash.com/photo-1522337660859-02fbefca4702?auto=format&fit=crop&w=900&q=85",

    durationMinutes: 180,

    price: 390,

    location:
      "Batel · Curitiba",

    availabilityLabel:
      "Quinta 11:00",

    availableSlots: [
      "11:00",
      "13:30",
    ],
  },
];

/*
 * POSTS
 */

export const posts: Post[] = [
  {
    id: "p1",

    authorId: "pro_1",

    image:
      "https://images.unsplash.com/photo-1604654894610-df63bc536371?auto=format&fit=crop&w=1000&q=90",

    caption:
      "Uma composição delicada, limpa e com acabamento natural. Menos excesso, mais detalhe.",

    rating: 4.9,

    commentsCount: 3,

    serviceId: "srv_1",

    createdAt:
      "2026-09-23T12:00:00-03:00",
  },

  {
    id: "p2",

    authorId: "pro_2",

    image:
      "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=1000&q=90",

    caption:
      "Camadas, movimento e uma finalização pensada para funcionar também no dia a dia.",

    rating: 4.8,

    commentsCount: 12,

    serviceId: "srv_3",

    createdAt:
      "2026-09-23T10:20:00-03:00",
  },

  {
    id: "p3",

    authorId: "pro_3",

    image:
      "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=1000&q=90",

    caption:
      "Um clássico atualizado: laterais limpas, textura e acabamento natural.",

    rating: 4.7,

    commentsCount: 2,

    serviceId: "srv_4",

    createdAt:
      "2026-09-22T18:10:00-03:00",
  },

  {
    id: "p4",

    authorId: "est_1",

    image:
      "https://images.unsplash.com/photo-1560066984-138dadb4c035?auto=format&fit=crop&w=1000&q=90",

    caption:
      "Um espaço pensado para transformar atendimento em experiência.",

    rating: 4.8,

    commentsCount: 21,

    serviceId: "srv_6",

    createdAt:
      "2026-09-22T14:30:00-03:00",
  },

  {
    id: "p5",

    authorId: "pro_4",

    image:
      "https://images.unsplash.com/photo-1583001931096-959e9a1a6223?auto=format&fit=crop&w=1000&q=90",

    caption:
      "Mapeamento leve para valorizar o olhar sem perder naturalidade.",

    rating: 4.9,

    commentsCount: 1,

    serviceId: "srv_5",

    createdAt:
      "2026-09-21T16:50:00-03:00",
  },
];

/*
 * STORIES / DESTAQUES
 */

export const stories: Story[] = [
  {
    id: "story_1",
    profileId: "pro_1",
    seen: false,
  },

  {
    id: "story_2",
    profileId: "pro_2",
    seen: false,
  },

  {
    id: "story_3",
    profileId: "est_1",
    seen: true,
  },

  {
    id: "story_4",
    profileId: "pro_3",
    seen: false,
  },

  {
    id: "story_5",
    profileId: "pro_4",
    seen: true,
  },

  {
    id: "story_6",
    profileId: "est_2",
    seen: false,
  },
];

/*
 * IDDUN NOW
 */

export const iddunNowItems: IDDUNNowItem[] = [
  {
    id: "now_1",

    serviceId: "srv_1",

    professionalId: "pro_1",

    timeLabel:
      "Hoje 14:30",

    urgent: true,
  },

  {
    id: "now_2",

    serviceId: "srv_3",

    professionalId: "pro_2",

    timeLabel:
      "Hoje 16:00",

    urgent: false,
  },

  {
    id: "now_3",

    serviceId: "srv_4",

    professionalId: "pro_3",

    timeLabel:
      "Hoje 18:15",

    urgent: true,
  },
];

/*
 * DESCOBRIR
 */

export const discoverItems: DiscoverItem[] = [
  {
    id: "discover_1",

    sourceId: "p1",

    type: "post",

    title:
      "Minimalismo em gel",

    subtitle:
      "Detalhes que fazem diferença.",

    image:
      posts[0].image,

    height: 310,

    category: "Unhas",
  },

  {
    id: "discover_2",

    sourceId: "pro_2",

    type: "professional",

    title:
      "Marina Alves",

    subtitle:
      "Hair Stylist",

    image:
      professionals[1].cover ??
      professionals[1].avatar,

    rating:
      professionals[1].rating,

    location:
      professionals[1].location,

    height: 220,

    category: "Cabelo",
  },

  {
    id: "discover_3",

    sourceId: "srv_4",

    type: "service",

    title:
      "Corte Masculino",

    subtitle:
      "Visual contemporâneo",

    image:
      services[3].image,

    location:
      services[3].location,

    height: 260,

    category: "Barbearia",
  },

  {
    id: "discover_4",

    sourceId: "est_1",

    type: "establishment",

    title:
      "Atelier Lumi",

    subtitle:
      "Beauty Studio",

    image:
      professionals[4].cover ??
      professionals[4].avatar,

    rating:
      professionals[4].rating,

    location:
      professionals[4].location,

    height: 330,

    category: "Estética",
  },

  {
    id: "discover_5",

    sourceId: "p5",

    type: "post",

    title:
      "Natural Lash",

    subtitle:
      "Elegância sem excesso.",

    image:
      posts[4].image,

    height: 240,

    category: "Cílios",
  },

  {
    id: "discover_6",

    sourceId: "srv_6",

    type: "service",

    title:
      "Coloração Premium",

    subtitle:
      "Cor sob medida",

    image:
      services[5].image,

    location:
      services[5].location,

    height: 290,

    category: "Cabelo",
  },

  {
    id: "discover_7",

    sourceId: "pro_1",

    type: "professional",

    title:
      "Renata Mocelin",

    subtitle:
      "Nail Designer",

    image:
      professionals[0].cover ??
      professionals[0].avatar,

    rating:
      professionals[0].rating,

    location:
      professionals[0].location,

    height: 350,

    category: "Unhas",
  },

  {
    id: "discover_8",

    sourceId: "pro_4",

    type: "professional",

    title:
      "Camila Duarte",

    subtitle:
      "Lash Designer",

    image:
      professionals[3].cover ??
      professionals[3].avatar,

    rating:
      professionals[3].rating,

    location:
      professionals[3].location,

    height: 230,

    category: "Cílios",
  },
];

/*
 * CATEGORIAS
 */

export const categories = [
  "Todos",
  "Unhas",
  "Cabelo",
  "Barbearia",
  "Tatuagem",
  "Sobrancelhas",
  "Estética",
];

/*
 * HELPERS
 */

export function getProfessionalById(
  id: string,
) {
  return professionals.find(
    (professional) =>
      professional.id === id,
  );
}

export function getServiceById(
  id: string,
) {
  return services.find(
    (service) =>
      service.id === id,
  );
}

export function getPostById(
  id: string,
) {
  return posts.find(
    (post) =>
      post.id === id,
  );
}

export function getServicesByAuthorId(
  authorId: string,
) {
  return services.filter(
    (service) =>
      service.authorId ===
      authorId,
  );
}

export function getPostsByAuthorId(
  authorId: string,
) {
  return posts.filter(
    (post) =>
      post.authorId ===
      authorId,
  );
}

export function getPostAuthor(
  post: Post,
) {
  return getProfessionalById(
    post.authorId,
  );
}

export function getPostService(
  post: Post,
) {
  if (!post.serviceId) {
    return undefined;
  }

  return getServiceById(
    post.serviceId,
  );
}

export function getStoryProfile(
  story: Story,
) {
  return getProfessionalById(
    story.profileId,
  );
}

export function getIDDUNNowData(
  item: IDDUNNowItem,
) {
  const service =
    getServiceById(
      item.serviceId,
    );

  const professional =
    getProfessionalById(
      item.professionalId,
    );

  if (
    !service ||
    !professional
  ) {
    return null;
  }

  return {
    item,
    service,
    professional,
  };
}
