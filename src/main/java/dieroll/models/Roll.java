package dieroll.models;

import lombok.Builder;

import java.util.Arrays;

@Builder
public record Roll(String roomId, String name, long timestamp, String request, String result) {

    public byte[] getBytes() {
        return String.join("|", String.valueOf(timestamp), name, request, result).getBytes();
    }

    public static Roll getRollFromByteArray(String roomId, byte[] redisValue) {
        String[] parts = Arrays.toString(redisValue).split("\\|");
        return new RollBuilder()
                .roomId(roomId)
                .timestamp(Long.parseLong(parts[0]))
                .name(parts[1])
                .request(parts[2])
                .result(parts[3])
                .build();
    }
}
