import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Calendar from "expo-calendar/legacy";
import { Platform } from "react-native";
import { getBookingCalendar, type CalendarBookingPayload } from "@/api/bookings";

type StoredEvent = { id: string; calendarId: string; startsAt: string; endsAt: string };
const key = (bookingId: string) => `iddun:calendar:event:${bookingId}`;

export async function syncNativeBookingCalendar(bookingId: string): Promise<"created" | "updated" | "unchanged"> {
  if (Platform.OS !== "ios" && Platform.OS !== "android") {
    throw new Error("Calendário nativo disponível apenas no iOS e Android.");
  }
  // Revalidar no servidor antes de solicitar acesso ao calendário.
  const booking = await getBookingCalendar(bookingId);
  const permission = await Calendar.requestCalendarPermissionsAsync();
  if (!permission.granted) throw new Error("Permissão de calendário não concedida.");
  const saved = await AsyncStorage.getItem(key(bookingId));
  const tracked: StoredEvent | null = saved ? JSON.parse(saved) as StoredEvent : null;
  const data = {
    title: booking.title,
    startDate: new Date(booking.startsAt),
    endDate: new Date(booking.endsAt),
    notes: "Reserva IDDUN. Consulte o aplicativo para informações e alterações.",
  };
  if (tracked) {
    // Nunca interpretar falha de acesso/atualização como evento ausente:
    // isso poderia criar uma segunda reserva no calendário.
    const existing = await Calendar.getEventAsync(tracked.id);
    if (existing) {
      if (tracked.startsAt === booking.startsAt && tracked.endsAt === booking.endsAt
        && new Date(existing.startDate).getTime() === data.startDate.getTime()
        && new Date(existing.endDate).getTime() === data.endDate.getTime()) return "unchanged";
      await Calendar.updateEventAsync(tracked.id, data);
      await persist(bookingId, tracked.id, tracked.calendarId, booking);
      return "updated";
    }
    await AsyncStorage.removeItem(key(bookingId));
  }
  const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  const writable = calendars.find((calendar) => calendar.allowsModifications)
    ?? (Platform.OS === "ios" ? await Calendar.getDefaultCalendarAsync() : null);
  if (!writable) throw new Error("Nenhum calendário gravável disponível no dispositivo.");
  const id = await Calendar.createEventAsync(writable.id, data);
  await persist(bookingId, id, writable.id, booking);
  return "created";
}

async function persist(bookingId: string, id: string, calendarId: string, booking: CalendarBookingPayload) {
  await AsyncStorage.setItem(key(bookingId), JSON.stringify({
    id, calendarId, startsAt: booking.startsAt, endsAt: booking.endsAt,
  } satisfies StoredEvent));
}

export async function removeNativeBookingCalendar(bookingId: string): Promise<boolean> {
  const saved = await AsyncStorage.getItem(key(bookingId));
  if (!saved) return false;
  const tracked = JSON.parse(saved) as StoredEvent;
  const permission = await Calendar.requestCalendarPermissionsAsync();
  if (!permission.granted) throw new Error("Permissão de calendário não concedida.");
  // Falhas de acesso ou exclusão não podem apagar o rastreamento local.
  // Assim o usuário poderá tentar novamente sem perder a referência ao evento.
  const event = await Calendar.getEventAsync(tracked.id);
  if (event) await Calendar.deleteEventAsync(tracked.id);
  await AsyncStorage.removeItem(key(bookingId));
  return true;
}
