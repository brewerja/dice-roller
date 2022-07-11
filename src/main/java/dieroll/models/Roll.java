package dieroll.models;

import lombok.Builder;

@Builder
public record Roll(String roomId, String name, long timestamp, String request, String result) {
}
