import React, { useCallback, useState } from "react";
import { ActivityIndicator, Alert, Linking, Share, ScrollView, Text, TextInput, View } from "react-native";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import {
  getBooking, getBookingActions, getBookingTimeline, getNoShowDisputes, createNoShowDispute,
  getBookingReview, saveBookingReview, getBookingCalendar, getBookingSafeShare,
  type BookingReviewResponse,
  requestBookingReschedule, type Booking, type BookingActionsResponse,
  type BookingTimeline, type NoShowDisputesResponse,
} from "@/api/bookings";
import { Button } from "@/components/Button";
import { fonts, makeStyles, spacing, radius, useTheme } from "@/theme";

export default function BookingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const styles = useStyles();
  const { colors } = useTheme();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [actions, setActions] = useState<BookingActionsResponse | null>(null);
  const [timeline, setTimeline] = useState<BookingTimeline["items"]>([]);
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<BookingReviewResponse | null>(null);
  const [rating, setRating] = useState(5);
  const [recommended, setRecommended] = useState(true);
  const [reviewComment, setReviewComment] = useState("");
  const [disputes, setDisputes] = useState<NoShowDisputesResponse | null>(null);
  const [justification, setJustification] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [detail, available, history, disputeHistory, reviewResponse] = await Promise.all([
        getBooking(id), getBookingActions(id), getBookingTimeline(id), getNoShowDisputes(id), getBookingReview(id),
      ]);
      setBooking(detail.booking);
      setActions(available);
      setTimeline(history.items);
      setDisputes(disputeHistory);
      setReview(reviewResponse);
      if (reviewResponse.review) {
        setRating(reviewResponse.review.rating);
        setRecommended(reviewResponse.review.recommended);
        setReviewComment(reviewResponse.review.comment || "");
      }
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível carregar a reserva.");
    }
  }, [id]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));
  const askForSlot = (slotId: number, when: string) => {
    Alert.alert("Solicitar reagendamento?", `Novo horário: ${when}. O horário atual permanece até a aprovação do executor.`, [
      { text: "Voltar", style: "cancel" },
      { text: "Solicitar", onPress: () => {
        if (!id || busy) return;
        setBusy(true);
        void requestBookingReschedule(id, slotId).then(() => {
          Alert.alert("Solicitação enviada", "Aguarde a resposta do executor.");
          return load();
        }).catch((caught: unknown) => {
          Alert.alert("Não foi possível solicitar", caught instanceof Error ? caught.message : "Tente novamente.");
        }).finally(() => setBusy(false));
      } },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Button title="Voltar às reservas" compact variant="ghost" onPress={() => router.back()} />
      <Text style={styles.heading}>Detalhes da reserva</Text>
      {error ? <Text accessibilityRole="alert" style={styles.text}>{error}</Text> : null}
      {!booking && !error ? <ActivityIndicator color={colors.plum} /> : null}
      {booking ? (
        <>
          <View style={styles.card}>
            <Text style={styles.subtitle}>{booking.experience.title}</Text>
            <Text style={styles.text}>Status: {booking.status}</Text>
            <Text style={styles.text}>Profissional: {booking.professional.name}</Text>
            {booking.establishment ? <Text style={styles.text}>Estabelecimento: {booking.establishment.name}</Text> : null}
            <Text style={styles.text}>Data: {booking.slot.localDate} às {booking.slot.localTime}</Text>
            <Text style={styles.text}>Fuso: {booking.slot.timezone}</Text>
            <Text style={styles.text}>Duração: {booking.experience.durationMinutes} minutos</Text>
            <Text style={styles.text}>Valor registrado: R$ {booking.price.toFixed(2).replace(".", ",")}</Text>
            <Text style={styles.text}>Esta é uma confirmação de agendamento, não um comprovante de pagamento.</Text>
          </View>
          <Text style={styles.subtitle}>Linha do tempo</Text>
          {timeline.map((event, index) => (
            <View key={`${event.at}-${index}`} style={styles.event}>
              <Text style={styles.text}>{new Date(event.at).toLocaleString("pt-BR")}</Text>
              <Text style={styles.text}>{event.label}</Text>
            </View>
          ))}
          {(booking.status === "confirmed" || booking.status === "completed") ? (
            <View style={styles.card}>
              <Text style={styles.subtitle}>Calendário e compartilhamento</Text>
              <Text style={styles.text}>Adicione um evento ao Google Calendar ou compartilhe apenas os detalhes mínimos. Dados de contato, links autenticados e endereços privados não são enviados.</Text>
              <Button title="Adicionar ao Google Calendar" compact variant="secondary" onPress={() => {
                if (!id || busy) return;
                setBusy(true);
                void getBookingCalendar(id).then(async (event) => {
                  const utc = (date: string) => new Date(date).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
                  const url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
                    + "&text=" + encodeURIComponent(event.title)
                    + "&dates=" + encodeURIComponent(utc(event.startsAt) + "/" + utc(event.endsAt))
                    + "&details=" + encodeURIComponent("Reserva IDDUN. Consulte a plataforma para alterações.");
                  await Linking.openURL(url);
                }).catch((caught: unknown) => Alert.alert("Calendário indisponível",
                  caught instanceof Error ? caught.message : "Tente novamente."))
                  .finally(() => setBusy(false));
              }} />
              <Button title="Compartilhar resumo seguro" compact variant="ghost" onPress={() => {
                if (!id || busy) return;
                setBusy(true);
                void getBookingSafeShare(id).then(({ message }) => Share.share({ message }))
                  .catch((caught: unknown) => Alert.alert("Compartilhamento indisponível",
                    caught instanceof Error ? caught.message : "Tente novamente."))
                  .finally(() => setBusy(false));
              }} />
              <Text style={styles.text}>Se a reserva mudar, abra novamente esta tela e gere um novo evento. Eventos adicionados anteriormente não são alterados automaticamente.</Text>
            </View>
          ) : null}
          {booking.status === "completed" ? (
            <View style={styles.card}>
              <Text style={styles.subtitle}>Pós-atendimento</Text>
              <Text style={styles.text}>Atendimento concluído com {booking.professional.name}.</Text>
              <Text style={styles.text}>Preço registrado: R$ {booking.price.toFixed(2).replace(".", ",")}</Text>
              {actions?.canRebook && actions.rebookExperienceSlug ? (
                <Button title="Reservar novamente" compact variant="secondary"
                  onPress={() => router.push({
                    pathname: "/booking/[serviceId]",
                    params: { serviceId: actions.rebookExperienceSlug || "" },
                  })} />
              ) : <Text style={styles.text}>Esta oferta não possui novos horários válidos no momento.</Text>}
              {review?.eligible ? (
                <>
                  <Text style={styles.subtitle}>Avaliar profissional</Text>
                  <Text style={styles.text}>Nota: {rating} de 5</Text>
                  <View style={styles.ratingRow}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <View key={star} style={styles.slot}>
                        <Button title={String(star)} compact
                          variant={rating === star ? "secondary" : "ghost"}
                          onPress={() => setRating(star)} />
                      </View>
                    ))}
                  </View>
                  <Button compact title={recommended ? "Recomendo este profissional" : "Não recomendo"}
                    variant="ghost" onPress={() => setRecommended(!recommended)} />
                  <TextInput style={styles.input} multiline maxLength={2000}
                    placeholder="Conte como foi sua experiência (opcional)"
                    placeholderTextColor={colors.muted} accessibilityLabel="Comentário da avaliação"
                    value={reviewComment} onChangeText={setReviewComment} />
                  <Button title={review.review ? "Atualizar avaliação" : "Publicar avaliação"}
                    compact loading={busy} onPress={() => {
                      if (!id || busy) return;
                      setBusy(true);
                      void saveBookingReview(id, rating, recommended, reviewComment)
                        .then(() => load())
                        .catch((caught: unknown) => Alert.alert("Avaliação não salva",
                          caught instanceof Error ? caught.message : "Tente novamente."))
                        .finally(() => setBusy(false));
                    }} />
                </>
              ) : null}
            </View>
          ) : null}
          {booking.status === "no_show" ? (
            <View style={styles.card}>
              <Text style={styles.subtitle}>Contestação de ausência</Text>
              <Text style={styles.text}>O registro da ausência permanece no histórico durante a análise.</Text>
              {disputes?.items.map((item) => (
                <View key={item.id} style={styles.event}>
                  <Text style={styles.text}>Status: {item.status === "pending" ? "Em análise" : item.status === "accepted" ? "Acolhida" : "Não acolhida"}</Text>
                  <Text style={styles.text}>Solicitada em {new Date(item.createdAt).toLocaleString("pt-BR")}</Text>
                  <Text style={styles.text}>Justificativa: {item.justification}</Text>
                  {item.resolvedAt ? <Text style={styles.text}>Analisada em {new Date(item.resolvedAt).toLocaleString("pt-BR")}</Text> : null}
                  {item.resolutionNote ? <Text style={styles.text}>Decisão: {item.resolutionNote}</Text> : null}
                </View>
              ))}
              {disputes?.canDispute ? (
                <>
                  <Text style={styles.text}>Justificativa (10 a 2000 caracteres)</Text>
                  <TextInput style={styles.input} multiline maxLength={2000} value={justification}
                    onChangeText={setJustification} placeholder="Explique por que contesta a ausência"
                    placeholderTextColor={colors.muted} accessibilityLabel="Justificativa da contestação" />
                  <Text style={styles.text}>Referência de evidência (opcional, apenas texto privado)</Text>
                  <TextInput style={styles.input} maxLength={500} value={evidenceReference}
                    onChangeText={setEvidenceReference} placeholder="Ex.: número de protocolo"
                    placeholderTextColor={colors.muted} accessibilityLabel="Referência privada de evidência" />
                  <Button title="Enviar contestação" compact loading={busy}
                    onPress={() => {
                      if (!id || busy) return;
                      if (justification.trim().length < 10) {
                        Alert.alert("Justificativa incompleta", "Informe pelo menos 10 caracteres.");
                        return;
                      }
                      setBusy(true);
                      void createNoShowDispute(id, justification, evidenceReference).then(() => {
                        setJustification("");
                        setEvidenceReference("");
                        return load();
                      }).catch((caught: unknown) => {
                        Alert.alert("Não foi possível contestar", caught instanceof Error ? caught.message : "Tente novamente.");
                      }).finally(() => setBusy(false));
                    }} />
                </>
              ) : null}
            </View>
          ) : null}
          <Text style={styles.subtitle}>Solicitar outro horário</Text>
          {actions?.rescheduleRequestStatus === "pending" ? (
            <Text style={styles.text}>Solicitação em análise. O horário original continua reservado.</Text>
          ) : booking.status === "confirmed" && actions?.rescheduleSlots.length ? (
            actions.rescheduleSlots.map((slot) => (
              <View key={slot.id} style={styles.slot}>
                <Button title={`${slot.localDate} às ${slot.localTime}`} compact variant="secondary"
                  loading={busy} onPress={() => askForSlot(slot.id, `${slot.localDate} às ${slot.localTime}`)} />
              </View>
            ))
          ) : <Text style={styles.text}>Nenhuma alternativa disponível para esta reserva.</Text>}
        </>
      ) : null}
    </ScrollView>
  );
}
const useStyles = makeStyles((colors) => ({
  container: { flex: 1, backgroundColor: colors.surface },
  content: { paddingHorizontal: spacing.lg, paddingTop: spacing.xxl, paddingBottom: 100, gap: spacing.md },
  heading: { fontFamily: fonts.display, fontSize: 28, color: colors.onSurface },
  subtitle: { fontFamily: fonts.sansSemiBold, fontSize: 17, color: colors.onSurface },
  text: { fontFamily: fonts.sans, fontSize: 13, color: colors.onSurfaceSecondary },
  card: { backgroundColor: colors.surfaceSecondary, padding: spacing.lg, borderRadius: radius.md, gap: spacing.sm },
  event: { borderLeftWidth: 2, borderLeftColor: colors.plum, paddingLeft: spacing.md, gap: spacing.xs },
  slot: { marginTop: spacing.xs },
  ratingRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.xs },
  input: { borderWidth: 1, borderColor: colors.glassBorder, color: colors.onSurface, backgroundColor: colors.surface, borderRadius: radius.md, padding: spacing.md, minHeight: 48 },
}));
