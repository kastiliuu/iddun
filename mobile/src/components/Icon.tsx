import React from "react";
import Feather from "@react-native-vector-icons/feather";
import Animated from "react-native-reanimated";

export type IconName = React.ComponentProps<typeof Feather>["name"];

export type IconProps = React.ComponentProps<typeof Feather>;

export function Icon(props: IconProps) {
  return <Feather {...props} />;
}

export const AnimatedIcon = Animated.createAnimatedComponent(Feather);