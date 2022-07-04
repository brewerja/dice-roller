package dieroll.models;

import lombok.Builder;

@Builder
public record Roll(String roomId, String name, long timestamp, String request, String result) {

    public byte[] getBytes() {
        return String.join("|", String.valueOf(timestamp), name, request, result).getBytes();
    }

    public static Roll getRollFromRedisValue(String roomId, String redisValue) {
        String[] parts = redisValue.split("\\|");
        return new RollBuilder()
                .roomId(roomId)
                .timestamp(Long.parseLong(parts[0]))
                .name(parts[1])
                .request(parts[2])
                .result(parts[3])
                .build();
    }
}
