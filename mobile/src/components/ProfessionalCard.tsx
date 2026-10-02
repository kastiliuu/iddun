import React from "react";
import {
  Pressable,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";

import { Avatar } from "@/components/Avatar";
import { FollowButton } from "@/components/FollowButton";
import { Rating } from "@/components/Rating";

import {
  fonts,
  makeStyles,
  radius,
  spacing,
} from "@/theme";

type ProfessionalCardProps = {
  id: string;
  name: string;
  avatar?: string | null;
  specialty?: string;
  location?: string;
  rating?: number;
  reviewsCount?: number;
  routeType?: "professional" | "establishment";
  showFollow?: boolean;
  testID?: string;
};

export function ProfessionalCard({
  id,
  name,
  avatar,
  specialty,
  location,
  rating,
  reviewsCount,
  routeType = "professional",
  showFollow = true,
  testID,
}: ProfessionalCardProps) {
  const styles = useStyles();
  const router = useRouter();

  const handlePress = () => {
    router.push(
      routeType === "establishment"
        ? `/establishment/${id}`
        : `/professional/${id}`,
    );
  };

  return (
    <View
      testID={testID}
      style={styles.card}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Abrir perfil de ${name}`}
        onPress={handlePress}
        style={({ pressed }) => [
          styles.profileArea,
          pressed && styles.pressed,
        ]}
      >
        <Avatar
          name={name}
          uri={avatar}
          size={56}
        />

        <View style={styles.info}>
          <Text
            style={styles.name}
            numberOfLines={1}
          >
            {name}
          </Text>

          {specialty ? (
            <Text
              style={styles.specialty}
              numberOfLines={1}
            >
              {specialty}
            </Text>
          ) : null}

          <View style={styles.metaRow}>
            {typeof rating === "number" ? (
              <Rating
                value={rating}
                small
              />
            ) : null}

            {typeof reviewsCount === "number" ? (
              <Text style={styles.reviews}>
                {reviewsCount}{" "}
                {reviewsCount === 1
                  ? "avaliação"
                  : "avaliações"}
              </Text>
            ) : null}

            {location ? (
              <>
                <View
                  style={styles.separator}
                />

                <Text
                  style={styles.location}
                  numberOfLines={1}
                >
                  {location}
                </Text>
              </>
            ) : null}
          </View>
        </View>
      </Pressable>

      {showFollow ? (
        <View style={styles.followWrap}>
          <FollowButton
            id={id}
            authorName={name}
          />
        </View>
      ) : null}
    </View>
  );
}

const useStyles = makeStyles((colors) => ({
  card: {
    width: "100%",
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceSecondary,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },

  profileArea: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
  },

  pressed: {
    opacity: 0.82,
  },

  info: {
    flex: 1,
    minWidth: 0,
    marginLeft: spacing.md,
  },

  name: {
    color: colors.onSurface,
    fontFamily: fonts.sansSemiBold,
    fontSize: 15,
    lineHeight: 20,
  },

  specialty: {
    marginTop: 2,
    color: colors.onSurfaceSecondary,
    fontFamily: fonts.sans,
    fontSize: 12,
    lineHeight: 16,
  },

  metaRow: {
    minWidth: 0,
    marginTop: spacing.xs,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },

  reviews: {
    flexShrink: 0,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 11,
    lineHeight: 14,
  },

  separator: {
    width: 3,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.muted,
    opacity: 0.6,
  },

  location: {
    flex: 1,
    color: colors.muted,
    fontFamily: fonts.sans,
    fontSize: 11,
    lineHeight: 14,
  },

  followWrap: {
    marginLeft: spacing.md,
  },
}));