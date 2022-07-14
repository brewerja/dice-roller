package dieroll.models;

import lombok.Builder;

import java.util.List;

@Builder
public record Roll(String roomId, String name, long timestamp, String request, List<Integer> results) {
}
