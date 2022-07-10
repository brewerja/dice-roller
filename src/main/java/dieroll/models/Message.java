package dieroll.models;

import lombok.Builder;

@Builder
public record Message(String roomId, String name, long timestamp, String message) {
}
