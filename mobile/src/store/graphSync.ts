import type {
  FollowTargetType,
  GraphState,
  SaveTargetType,
} from "@/api/graph";

import {
  reconcileBeautyGraph,
} from "@/api/graph";

import {
  store,
} from "@/store/local";


function isFollowTargetType(
  value: string,
): value is FollowTargetType {
  return (
    value === "professional" ||
    value === "establishment"
  );
}


function isSaveTargetType(
  value: string,
): value is SaveTargetType {
  return (
    value === "professional" ||
    value === "establishment" ||
    value === "experience" ||
    value === "portfolio_item" ||
    value === "work_post"
  );
}


export function localBeautyGraphState():
  GraphState {
  const current =
    store.graphState();

  return {
    follows:
      current.follows.filter(
        (
          item,
        ): item is {
          targetType:
            FollowTargetType;
          targetId: number;
        } =>
          isFollowTargetType(
            item.targetType,
          ),
      ),
    saves:
      current.saves.filter(
        (
          item,
        ): item is {
          targetType:
            SaveTargetType;
          targetId: number;
        } =>
          isSaveTargetType(
            item.targetType,
          ),
      ),
  };
}


export async function syncBeautyGraph() {
  const user =
    store.getUser();

  if (!user) {
    return null;
  }

  const response =
    await reconcileBeautyGraph(
      localBeautyGraphState(),
    );

  store.replaceGraphState(
    response.state,
  );

  return response;
}
