import React, { useCallback, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, View } from "react-native";
import { useFocusEffect, useLocalSearchParams, useRouter } from "expo-router";
import {
  getBooking, getBookingActions, getBookingTimeline,
  requestBookingReschedule, type Booking, type BookingActionsResponse,
  type BookingTimeline,
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
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [detail, available, history] = await Promise.all([
        getBooking(id), getBookingActions(id), getBookingTimeline(id),
      ]);
      setBooking(detail.booking);
      setActions(available);
      setTimeline(history.items);
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
}));
